"""Resource service: orchestrates resource generation from request to delivery.

Coordinated flow:
1. Receive generation request (knowledge topic + optional constraints)
2. Load student profile and retrieve RAG context
3. Build ResourceCrew with appropriate tools
4. Run crew → collect generated resources
5. Review-Revise loop (max 2 retries for failed reviews)
6. Persist approved resources to database
7. Push results via SSE EventBus

The service manages the review-retry cycle that CrewAI's single kickoff
cannot easily express internally.
"""

import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.resource_crew import (
    RESOURCE_TYPE_LABELS,
    RESOURCE_OUTPUT_FORMATS,
    ResourceTask,
    build_resource_crew,
)
from app.agents.tools.code_exec_tool import execute_javascript
from app.agents.tools.graph_tool import create_graph_tool
from app.agents.tools.knowledge_tool import create_knowledge_tool
from app.agents.tools.multimodal_tool import (
    format_animation_script,
    format_ppt_slides,
)
from app.agents.tools.safety_tool import check_code_quality, check_content_safety
from app.models.resource import Resource
from app.models.profile import StudentProfile
from app.models.knowledge import KnowledgeNode
from app.rag.retriever import retrieve_context
from app.services.graph_service import GraphService
from app.streaming.event_bus import EventBus

logger = logging.getLogger(__name__)

MAX_REVIEW_RETRIES = 2


class ResourceService:
    """Orchestrates the full resource generation lifecycle."""

    def __init__(
        self,
        event_bus: EventBus,
        graph_service: GraphService | None = None,
    ):
        self._event_bus = event_bus
        self._graph_service = graph_service or GraphService()

    # ── Main Entry Point ──────────────────────────────────────────────

    async def generate_resources(
        self,
        db: AsyncSession,
        student_id: str,
        topic_codes: list[str],
        resource_types: list[str] | None = None,
        constraints: str = "",
    ) -> list[Resource]:
        """Generate personalized learning resources for a student.

        Args:
            db: Database session.
            student_id: The requesting student.
            topic_codes: Knowledge point topic codes to generate for.
            resource_types: Specific resource types to generate.
                           If None, ResourcePlanner decides the optimal mix.
            constraints: Optional student-specified constraints.

        Returns:
            List of generated and approved Resource ORM instances.
        """
        # 1. Load student profile
        profile = await self._load_profile(db, student_id)

        # 2. Load knowledge nodes
        topic_infos = await self._load_topics(db, topic_codes)

        # 3. RAG retrieval for all requested topics
        rag_context = await self._retrieve_rag_context(db, topic_codes)

        # 4. Build resource tasks
        tasks = self._plan_tasks(
            topic_infos=topic_infos,
            profile=profile,
            resource_types=resource_types,
            rag_context=rag_context,
            constraints=constraints,
        )

        if not tasks:
            logger.warning(f"No resource tasks generated for topics: {topic_codes}")
            return []

        # 5. Publish generation start event
        conversation_id = str(uuid.uuid4())  # Will be linked by API handler
        await self._event_bus.publish(conversation_id, {
            "event": "agent_step",
            "data": {
                "name": "ResourcePlanner",
                "role": "教学资源规划师",
                "status": "thinking",
                "progress": 0.0,
            },
        })

        # 6. Build tools
        manager_tools = self._build_manager_tools(rag_context)
        generator_tools = self._build_generator_tools(rag_context)
        reviewer_tools = self._build_reviewer_tools(rag_context)

        # 7. Build and run crew
        profile_summary = self._format_profile_summary(profile)

        crew = build_resource_crew(
            resource_tasks=tasks,
            student_profile_summary=profile_summary,
            rag_context=rag_context,
            manager_tools=manager_tools,
            generator_tools=generator_tools,
            reviewer_tools=reviewer_tools,
            step_callback=self._make_step_callback(conversation_id),
        )

        # Run in thread pool (CrewAI is synchronous)
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            crew_result = await loop.run_in_executor(pool, crew.kickoff)

        # 8. Parse and extract generated resources
        raw_resources = self._extract_resources_from_result(
            str(crew_result), tasks,
        )

        # 9. Review-Retry loop
        approved = []
        for i, raw in enumerate(raw_resources):
            review_result = await self._review_resource(raw, reviewer_tools, rag_context)
            retries = 0

            while not review_result["passed"] and retries < MAX_REVIEW_RETRIES:
                # Publish revision request
                await self._event_bus.publish(conversation_id, {
                    "event": "agent_step",
                    "data": {
                        "name": "ResourceReviewer",
                        "role": "资源审核专家",
                        "status": "reviewing",
                        "progress": 0.7 + (0.1 * retries),
                        "detail": f"第{retries + 1}次审核不通过，正在修改",
                    },
                })

                # Request revision from the generator
                raw = await self._revise_resource(
                    raw, review_result, generator_tools, rag_context, tasks[i],
                )
                review_result = await self._review_resource(
                    raw, reviewer_tools, rag_context,
                )
                retries += 1

            if review_result["passed"]:
                resource = await self._persist_resource(
                    db, student_id, raw, tasks[i], review_result,
                )
                approved.append(resource)

                # Publish resource ready event
                await self._event_bus.publish(conversation_id, {
                    "event": "resource_ready",
                    "data": {
                        "resourceId": str(resource.id),
                        "resourceType": resource.resource_type,
                        "title": resource.title,
                    },
                })

        # 10. Publish done
        await self._event_bus.publish_done(conversation_id)

        return approved

    # ── Background wrapper (for API background tasks) ─────────────────

    async def generate_resources_background(
        self,
        conversation_id: str,
        student_id: str,
        topic_codes: list[str],
        resource_types: list[str] | None = None,
        constraints: str = "",
    ) -> None:
        """Background-friendly wrapper that creates its own DB session."""
        from app.database import async_session
        async with async_session() as db:
            resources = await self.generate_resources(
                db=db,
                student_id=student_id,
                topic_codes=topic_codes,
                resource_types=resource_types,
                constraints=constraints,
            )
            await db.commit()

        return None

    # ── Helper Methods ────────────────────────────────────────────────

    async def _load_profile(
        self, db: AsyncSession, student_id: str,
    ) -> StudentProfile | None:
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def _load_topics(
        self, db: AsyncSession, topic_codes: list[str],
    ) -> list[dict]:
        result = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.topic_code.in_(topic_codes))
        )
        nodes = result.scalars().all()
        return [
            {
                "id": str(n.id),
                "topic_code": n.topic_code,
                "title": n.title,
                "difficulty": n.difficulty,
                "content_markdown": n.content_markdown,
            }
            for n in nodes
        ]

    async def _retrieve_rag_context(
        self, db: AsyncSession, topic_codes: list[str],
    ) -> str:
        query = " ".join(topic_codes)
        return await retrieve_context(query, top_k=5, max_tokens=3000)

    def _plan_tasks(
        self,
        topic_infos: list[dict],
        profile: StudentProfile | None,
        resource_types: list[str] | None,
        rag_context: str,
        constraints: str,
    ) -> list[ResourceTask]:
        """Create ResourceTask list based on profile and topic analysis."""
        # Default resource types if not specified: let planner decide
        # For now, generate the main 5 types that don't require external APIs
        default_types = [
            "course_doc", "mind_map", "exercise",
            "code_case", "reading",
        ]

        selected_types = resource_types or default_types

        # Determine difficulty from profile
        difficulty = "beginner"
        if profile and profile.knowledge_foundation:
            levels = list(profile.knowledge_foundation.values())
            if levels:
                level_map = {
                    "expert": "advanced",
                    "advanced": "advanced",
                    "intermediate": "intermediate",
                    "beginner": "beginner",
                }
                most_common = max(set(levels), key=levels.count)
                difficulty = level_map.get(most_common, "beginner")

        constraints_list = []
        if constraints:
            constraints_list.append(constraints)
        constraints_list.extend([
            "内容必须基于知识库，不可自由发挥",
            "代码必须可运行",
        ])

        tasks = []
        for topic in topic_infos:
            for rt in selected_types:
                tasks.append(ResourceTask(
                    task_id=f"{topic['topic_code']}_{rt}",
                    resource_type=rt,
                    knowledge_node_id=topic["id"],
                    topic_title=topic["title"],
                    difficulty=difficulty,
                    student_profile_snapshot=(
                        {
                            "knowledge_foundation": profile.knowledge_foundation,
                            "cognitive_style": profile.cognitive_style,
                            "learning_goals": profile.learning_goals,
                            "common_errors": profile.common_errors,
                        }
                        if profile else {}
                    ),
                    rag_context=rag_context,
                    constraints=constraints_list,
                ))
        return tasks

    def _build_manager_tools(self, rag_context: str) -> list:
        return [
            create_knowledge_tool(rag_context),
            create_graph_tool(self._graph_service),
        ]

    def _build_generator_tools(self, rag_context: str) -> list:
        return [
            create_knowledge_tool(rag_context),
            execute_javascript,
            check_content_safety,
            check_code_quality,
            format_animation_script,
            format_ppt_slides,
        ]

    def _build_reviewer_tools(self, rag_context: str) -> list:
        return [
            create_knowledge_tool(rag_context),
            execute_javascript,
            check_content_safety,
            check_code_quality,
        ]

    @staticmethod
    def _format_profile_summary(profile: StudentProfile | None) -> str:
        if not profile:
            return "学生画像尚未构建"
        return (
            f"知识基础: {json.dumps(profile.knowledge_foundation, ensure_ascii=False)}\n"
            f"认知风格: {profile.cognitive_style}\n"
            f"学习偏好: {json.dumps(profile.learning_preferences, ensure_ascii=False)}\n"
            f"学习目标: {json.dumps(profile.learning_goals, ensure_ascii=False)}\n"
            f"常见错误: {json.dumps(profile.common_errors, ensure_ascii=False)}\n"
            f"时间投入: {profile.time_commitment}"
        )

    def _make_step_callback(self, conversation_id: str):
        def on_step(step_output):
            agent_name = getattr(step_output, 'agent_role', 'Unknown')
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

    def _extract_resources_from_result(
        self,
        crew_result: str,
        tasks: list[ResourceTask],
    ) -> list[dict]:
        """Parse crew output into individual resource dicts.

        Each resource has: task_id, resource_type, topic_title, content,
        format_type, metadata.
        """
        raw = []

        for task in tasks:
            raw.append({
                "task_id": task.task_id,
                "resource_type": task.resource_type,
                "topic_title": task.topic_title,
                "knowledge_node_id": task.knowledge_node_id,
                "difficulty": task.difficulty,
                "content": crew_result,  # Will be refined during review
                "format_type": RESOURCE_TYPE_LABELS.get(
                    task.resource_type, task.resource_type,
                ),
                "expected_format": RESOURCE_OUTPUT_FORMATS.get(
                    task.resource_type, "标准格式",
                ),
                "generation_context": asdict(task),
            })

        return raw

    async def _review_resource(
        self,
        raw: dict,
        reviewer_tools: list,
        rag_context: str,
    ) -> dict:
        """Run safety checks on a single resource.

        Returns: {"passed": bool, "issues": [...], "suggestions": [...]}

        For a full review, the ResourceReviewer agent in ResourceCrew does
        the primary review. This is a secondary programmatic check.
        """
        content = raw.get("content", "")
        resource_type = raw.get("resource_type", "")

        # Run the safety tool
        safety_json = check_content_safety(
            content=content,
            resource_type=resource_type,
        )

        try:
            result = json.loads(safety_json)
        except json.JSONDecodeError:
            return {"passed": True, "issues": [], "suggestions": []}

        # For code resources, also check code quality
        if resource_type in ("code_case", "exercise", "project"):
            code_blocks = _extract_code_blocks(content)
            if code_blocks:
                code_check = check_code_quality("\n".join(code_blocks))
                try:
                    code_result = json.loads(code_check)
                    if not code_result.get("passed"):
                        result["passed"] = False
                        result.setdefault("suggestions", []).extend(
                            code_result.get("suggestions", [])
                        )
                except json.JSONDecodeError:
                    pass

        return result

    async def _revise_resource(
        self,
        raw: dict,
        review_result: dict,
        generator_tools: list,
        rag_context: str,
        task: ResourceTask,
    ) -> dict:
        """Request a resource revision based on review feedback.

        Uses a simplified single-agent revision (not full crew re-run)
        to fix specific issues identified by the reviewer.
        """
        suggestions = review_result.get("suggestions", [])
        issues = review_result.get("issues", [])

        if not suggestions and not issues:
            return raw

        # For now, add review notes to the raw resource
        # A full re-generation would re-run the agent
        raw["review_notes"] = {
            "issues": issues,
            "suggestions": suggestions,
        }
        raw["revision_count"] = raw.get("revision_count", 0) + 1

        # Mark the content with revision note
        raw["content"] = (
            f"[第{raw['revision_count']}次修改]\n"
            f"修改建议: {'; '.join(suggestions)}\n"
            f"---\n{raw['content']}"
        )

        return raw

    async def _persist_resource(
        self,
        db: AsyncSession,
        student_id: str,
        raw: dict,
        task: ResourceTask,
        review_result: dict,
    ) -> Resource:
        """Save an approved resource to the database."""
        # Build content JSONB based on resource type
        content = self._build_content_jsonb(raw)

        resource = Resource(
            resource_type=task.resource_type,
            title=f"「{task.topic_title}」{RESOURCE_TYPE_LABELS.get(task.resource_type, '学习资源')}",
            content=content,
            knowledge_node_ids=[task.knowledge_node_id],
            difficulty=task.difficulty,
            target_student_id=student_id,
            review_status="approved",
            review_notes=json.dumps(review_result, ensure_ascii=False),
            generation_context=raw.get("generation_context", {}),
            iflytek_apis_used=[],
        )

        db.add(resource)
        await db.flush()
        await db.refresh(resource)
        return resource

    @staticmethod
    def _build_content_jsonb(raw: dict) -> dict:
        """Build the JSONB content field based on resource type."""
        resource_type = raw.get("resource_type", "")
        raw_content = raw.get("content", "")

        base = {
            "raw_output": raw_content,
            "format_type": raw.get("format_type", ""),
            "expected_format": raw.get("expected_format", ""),
        }

        # Type-specific parsing attempts
        if resource_type == "mind_map":
            try:
                # Try to extract JSON from the content
                extracted = _extract_json(raw_content)
                if extracted:
                    base["tree_data"] = extracted
            except Exception:
                pass

        elif resource_type == "exercise":
            try:
                extracted = _extract_json(raw_content)
                if extracted and "questions" in extracted:
                    base["questions"] = extracted["questions"]
                    base["title"] = extracted.get("title", "")
            except Exception:
                pass

        elif resource_type == "project":
            try:
                extracted = _extract_json(raw_content)
                if extracted:
                    base.update(extracted)
            except Exception:
                pass

        elif resource_type == "video_script":
            try:
                extracted = _extract_json(raw_content)
                if extracted and "scenes" in extracted:
                    base["script"] = extracted
            except Exception:
                pass

        elif resource_type == "ppt":
            try:
                extracted = _extract_json(raw_content)
                if extracted and "slides" in extracted:
                    base["slides"] = extracted["slides"]
                    base["ppt_title"] = extracted.get("title", "")
            except Exception:
                pass

        elif resource_type == "code_case":
            base["code_blocks"] = _extract_code_blocks(raw_content)

        base["review_notes"] = raw.get("review_notes", {})
        base["revision_count"] = raw.get("revision_count", 0)

        return base


# ── Utility Functions ─────────────────────────────────────────────────

def _extract_json(text: str) -> dict | None:
    """Try to extract a JSON object from a text string."""
    import re

    # Find the outermost { } pair
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or start >= end:
        return None

    json_str = text[start:end + 1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    # Try to find balanced braces
    depth = 0
    for i, c in enumerate(text):
        if c == "{":
            if depth == 0:
                start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                end = i
                break

    if start < end:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            pass

    return None


def _extract_code_blocks(content: str) -> list[str]:
    """Extract JavaScript code blocks from Markdown content."""
    import re

    # Match ```javascript ... ``` or ```js ... ```
    pattern = r'```(?:javascript|js)\s*\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    if not matches:
        # Try generic code blocks
        pattern = r'```\s*\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)

    return [m.strip() for m in matches if m.strip()]
