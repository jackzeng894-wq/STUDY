"""Tutoring service: orchestrates real-time Q&A and tutoring.

Flow:
1. Student asks a question in a tutoring conversation
2. RAG retrieval for relevant knowledge base content
3. TutorAgent answers (grounded in knowledge base)
4. ExplanationGenerator enhances with multi-modal content
5. Response + enhancements streamed to frontend via SSE
6. Student profile updated based on question patterns
"""

import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.tutoring_crew import build_tutoring_crew
from app.agents.tools.code_exec_tool import execute_javascript
from app.agents.tools.knowledge_tool import create_knowledge_tool
from app.agents.tools.multimodal_tool import format_animation_script
from app.agents.tools.safety_tool import check_code_quality, check_content_safety
from app.models.conversation import Conversation, Message
from app.models.profile import StudentProfile
from app.rag.retriever import retrieve_context
from app.services.conversation_service import add_message
from app.streaming.event_bus import EventBus

logger = logging.getLogger(__name__)


class TutoringService:
    """Orchestrates the tutoring Q&A lifecycle."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    async def process_question(
        self,
        db: AsyncSession,
        conversation_id: str,
        student_id: str,
        question: str,
        conversation_history: str = "",
    ) -> dict:
        """Process a student's tutoring question.

        Args:
            db: Database session.
            conversation_id: Current tutoring conversation.
            student_id: The asking student.
            question: The student's question.
            conversation_history: Previous messages in this conversation.

        Returns:
            Dict with keys: answer (str), enhancements (dict or None),
            profile_updates (list).
        """
        # 1. Load student profile for personalization
        profile = await self._load_profile(db, student_id)
        profile_summary = self._format_profile_brief(profile)

        # 2. RAG retrieval
        rag_context = await retrieve_context(question, top_k=3, max_tokens=2000)

        # 3. Build tools
        tools = [
            create_knowledge_tool(rag_context),
            execute_javascript,
            check_content_safety,
            check_code_quality,
        ]

        # 4. Publish agent step
        await self._event_bus.publish(conversation_id, {
            "event": "agent_step",
            "data": {
                "name": "TutorAgent",
                "role": "JavaScript辅导教师",
                "status": "thinking",
                "progress": 0.0,
            },
        })

        # 5. Run TutoringCrew
        crew = build_tutoring_crew(
            student_question=question,
            conversation_history=conversation_history,
            student_profile_summary=profile_summary,
            rag_context=rag_context,
            tutor_tools=tools,
            explainer_tools=tools + [format_animation_script],
            step_callback=self._make_step_callback(conversation_id),
        )

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            crew_result = await loop.run_in_executor(pool, crew.kickoff)

        result_text = str(crew_result)

        # 6. Parse result: the sequential output contains both answer and enhancements
        answer, enhancements = self._parse_tutoring_result(result_text)

        # 7. Save assistant response
        assistant_content = answer
        metadata = {}
        if enhancements:
            metadata["enhancements"] = enhancements

        await add_message(
            db, conversation_id, "assistant", assistant_content,
            metadata=metadata,
        )

        # 8. Update profile based on question topic
        profile_updates = await self._update_profile_from_question(
            db, student_id, question, profile,
        )

        # 9. Publish done
        await self._event_bus.publish(conversation_id, {
            "event": "profile_update",
            "data": {"updates": profile_updates},
        })
        await self._event_bus.publish_done(conversation_id)

        return {
            "answer": answer,
            "enhancements": enhancements,
            "profile_updates": profile_updates,
        }

    async def process_question_background(
        self,
        conversation_id: str,
        student_id: str,
        question: str,
        conversation_history: str = "",
    ) -> None:
        """Background-friendly wrapper with its own DB session."""
        from app.database import async_session
        async with async_session() as db:
            await self.process_question(
                db=db,
                conversation_id=conversation_id,
                student_id=student_id,
                question=question,
                conversation_history=conversation_history,
            )
            await db.commit()

    # ── Helpers ──────────────────────────────────────────────────────

    async def _load_profile(
        self, db: AsyncSession, student_id: str,
    ) -> StudentProfile | None:
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _format_profile_brief(profile: StudentProfile | None) -> str:
        if not profile:
            return ""
        foundation = profile.knowledge_foundation or {}
        if foundation:
            levels = list(foundation.values())
            if levels:
                most_common = max(set(levels), key=levels.count)
                return (
                    f"学生总体JS水平: {most_common}。"
                    f"认知风格: {profile.cognitive_style}。"
                    f"学习偏好: {profile.learning_preferences}。"
                )
        return f"认知风格: {profile.cognitive_style}。"

    def _make_step_callback(self, conversation_id: str):
        def on_step(step_output):
            agent_name = getattr(step_output, 'agent_role', 'Unknown Agent')
            self._event_bus.publish_sync(conversation_id, {
                "event": "agent_step",
                "data": {
                    "name": agent_name,
                    "role": agent_name,
                    "status": "generating",
                    "progress": 0.5,
                },
            })
        return on_step

    @staticmethod
    def _parse_tutoring_result(result_text: str) -> tuple[str, dict | None]:
        """Parse sequential crew output into answer text and enhancement JSON.

        The TutorAgent output comes first (Markdown answer), followed by
        the ExplanationGenerator output (JSON enhancements).
        """
        import re

        answer = result_text
        enhancements = None

        # Try to find JSON at the end (ExplanationGenerator output)
        json_match = re.search(r'\{[^{}]*"steps"[^{}]*\}', result_text)
        if not json_match:
            json_match = re.search(r'\{[^{}]*"mnemonic"[^{}]*\}', result_text)
        if not json_match:
            json_match = re.search(r'\{[^{}]*"comparison_table"[^{}]*\}', result_text)
        if not json_match:
            # Try to find any JSON block at the end
            brace_start = result_text.rfind('{')
            brace_end = result_text.rfind('}')
            if brace_start >= 0 and brace_end > brace_start:
                try:
                    json.loads(result_text[brace_start:brace_end + 1])
                    json_match = re.search(
                        r'\{.*\}', result_text[brace_start:brace_end + 1],
                        re.DOTALL,
                    )
                except json.JSONDecodeError:
                    pass

        if json_match:
            try:
                enhancements = json.loads(json_match.group(0))
                # Remove JSON from answer text
                answer = result_text[:json_match.start()].strip()
                if not answer:
                    answer = result_text[json_match.end():].strip()
            except json.JSONDecodeError:
                pass

        # If answer is still the full result, it's fine — just means no
        # separate enhancements were generated
        if not answer:
            answer = result_text

        return answer, enhancements

    async def _update_profile_from_question(
        self,
        db: AsyncSession,
        student_id: str,
        question: str,
        profile: StudentProfile | None,
    ) -> list[dict]:
        """Track tutoring topics for profile enrichment."""
        updates = []

        if not profile:
            return updates

        # Simple keyword-based topic detection
        topic_keywords = {
            "js_var_let_const": ["var", "let", "const", "变量", "声明", "作用域"],
            "js_functions": ["函数", "箭头函数", "参数", "返回值", "调用"],
            "js_closure": ["闭包", "作用域链", "词法"],
            "js_this": ["this", "绑定", "call", "apply", "bind", "上下文"],
            "js_async_promise": ["异步", "Promise", "回调", "then", "catch"],
            "js_async_await": ["async", "await", "同步", "等待"],
            "js_event_loop": ["事件循环", "event loop", "宏任务", "微任务"],
            "js_prototype": ["原型", "prototype", "proto", "继承"],
            "js_dom": ["DOM", "document", "元素", "选择器", "事件"],
            "js_array": ["数组", "Array", "遍历", "map", "filter", "reduce"],
            "js_object": ["对象", "Object", "属性", "方法"],
            "js_es6": ["ES6", "解构", "模板字符串", "展开", "模块"],
        }

        matched_topics = []
        for topic_code, keywords in topic_keywords.items():
            if any(kw in question for kw in keywords):
                matched_topics.append(topic_code)

        if matched_topics:
            # Record as "asked about" — weaker signal than exercise performance
            current = profile.knowledge_foundation or {}
            for tc in matched_topics:
                if tc not in current:
                    current[tc] = "exploring"
            profile.knowledge_foundation = current
            updates.append({
                "type": "question_topics",
                "topics": matched_topics,
            })

        return updates
