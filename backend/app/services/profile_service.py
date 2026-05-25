"""Profile service: orchestrates the profile building conversation flow.

Coordinates between RAG, ProfileCrew, EventBus, and database.
The main entry point is process_message() which handles one round of
the profile interview conversation.
"""

import asyncio
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.profile_crew import build_profile_crew
from app.models.profile import StudentProfile
from app.rag.retriever import retrieve_context
from app.services.conversation_service import (
    add_message,
    build_messages_context,
    get_messages,
)
from app.streaming.event_bus import EventBus


class ProfileService:
    """Orchestrates profile building conversations."""

    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus

    async def process_message_background(
        self,
        conversation_id: str,
        student_id: str,
        content: str,
    ) -> None:
        """Background-friendly wrapper that creates its own DB session."""
        from app.database import async_session
        async with async_session() as db:
            await self.process_message(db, conversation_id, student_id, content)
            await db.commit()
        return None

    async def process_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        student_id: str,
        content: str,
    ) -> None:
        """Process a user message in a profile-building conversation.

        1. Load conversation history
        2. Retrieve RAG context
        3. Run ProfileCrew (in thread pool)
        4. Save assistant response
        5. Update profile from analyzer output
        6. Publish events via EventBus

        Note: the user message is already saved by the API handler before
        this is called. This method adds the assistant reply and profile updates.
        """
        # 1. Load history
        messages = await get_messages(db, conversation_id)
        history = build_messages_context(messages)

        # 3. RAG retrieval
        rag_context = await retrieve_context(content, top_k=3, max_tokens=1500)

        # 4. Publish agent_step: interviewer starting
        await self._event_bus.publish(conversation_id, {
            "event": "agent_step",
            "data": {
                "name": "ProfileInterviewer",
                "role": "JavaScript学习画像面试官",
                "status": "thinking",
                "progress": 0.0,
            },
        })

        # 5. Run crew in thread pool (CrewAI kickoff() is synchronous)
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            crew_result = await loop.run_in_executor(
                pool,
                self._run_crew,
                conversation_id,
                history,
                content,
                rag_context,
            )

        # 6. Save assistant message (interviewer response)
        interviewer_response = self._extract_interviewer_response(crew_result)
        if interviewer_response:
            await add_message(db, conversation_id, "assistant", interviewer_response)

        # 7. Update profile from analyzer output
        await self._update_profile_from_result(db, student_id, crew_result)

        # 8. Publish done
        await self._event_bus.publish_done(conversation_id)

    def _run_crew(
        self,
        conversation_id: str,
        history: str,
        user_message: str,
        rag_context: str,
    ) -> str:
        """Synchronous crew execution (runs in thread pool)."""
        def on_step(step_output):
            # Determine which agent is active from the step output
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

        crew = build_profile_crew(
            conversation_history=history,
            user_message=user_message,
            rag_context=rag_context,
            step_callback=on_step,
        )
        result = crew.kickoff()
        return str(result)

    @staticmethod
    def _extract_interviewer_response(crew_result: str) -> str | None:
        """Extract the interviewer's reply from the crew result.

        CrewAI sequential process returns the last task's output.
        The last task is the analyzer, so we need the interviewer's output
        which is embedded in the full result. For simplicity, if the result
        looks like a chat reply, return it directly.
        """
        if not crew_result or not crew_result.strip():
            return None
        # If result contains our markers, extract the reply portion
        # Otherwise return the whole thing (it's the interviewer's reply)
        return crew_result.strip()

    async def _update_profile_from_result(
        self,
        db: AsyncSession,
        student_id: str,
        crew_result: str,
    ) -> None:
        """Parse crew output and update StudentProfile dimensions.

        The analyzer task calls update_student_profile tool which returns
        confirmation strings. The profile data is embedded in the task outputs.
        For robustness, try to extract structured profile data from the result.
        """
        if not crew_result:
            return

        # Try to find JSON profile data embedded in the result
        # The analyzer should output structured data; attempt to parse it
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = StudentProfile(student_id=student_id)
            db.add(profile)

        # Attempt to extract dimension updates from crew result
        # The analyzer's tool calls also appear in the result text
        self._parse_and_apply_dimensions(profile, crew_result)

        # Recalculate confidence
        profile.profile_confidence = self._calculate_confidence(profile)
        profile.version += 1
        await db.flush()

    @staticmethod
    def _parse_and_apply_dimensions(profile: StudentProfile, result: str) -> None:
        """Try to extract dimension data from crew result text.

        Looks for JSON objects that might be profile dimensions.
        This is a best-effort parser; handles the structured output format.
        """
        # Check for common dimension patterns in the result
        # The analyzer might embed JSON in its output or tool call results

        # Look for JSON objects (anything between { and })
        import re
        json_objects = re.findall(r'\{[^{}]*\}', result)

        for obj_str in json_objects:
            try:
                data = json.loads(obj_str)
            except json.JSONDecodeError:
                continue

            # Heuristic: classify the JSON based on its keys
            if "topic_code" in data or any(
                k in data for k in ["js_", "beginner", "intermediate", "advanced"]
            ):
                # Likely knowledge_foundation data
                if isinstance(data, dict) and all(
                    isinstance(v, str) for v in data.values()
                ):
                    profile.knowledge_foundation = {
                        **profile.knowledge_foundation, **data
                    }

            if "resource_types" in data and "pace" in data:
                profile.learning_preferences = data

            if "goal" in data and "priority" in data:
                current = profile.learning_goals or []
                if isinstance(data, dict):
                    current.append(data)
                    profile.learning_goals = current

            if "pattern" in data and "topic" in data:
                current = profile.common_errors or []
                if isinstance(data, dict):
                    current.append(data)
                    profile.common_errors = current

        # Check for cognitive_style values in the text
        for style in ["visual", "auditory", "kinesthetic", "reading_writing", "mixed"]:
            if style in result.lower():
                profile.cognitive_style = style
                break

        # Check for time_commitment values
        for tc in ["minimal", "moderate", "substantial", "intensive"]:
            if tc in result.lower():
                profile.time_commitment = tc
                break

    @staticmethod
    def _calculate_confidence(profile: StudentProfile) -> float:
        """Calculate profile confidence based on how many dimensions have data."""
        scores = []
        scores.append(1.0 if profile.knowledge_foundation else 0.0)
        scores.append(1.0 if profile.cognitive_style and profile.cognitive_style != "unknown" else 0.0)
        scores.append(0.5 if profile.common_errors else 0.0)  # partial weight
        scores.append(1.0 if profile.learning_preferences else 0.0)
        scores.append(0.5 if profile.learning_goals else 0.0)  # partial weight
        scores.append(0.5 if profile.time_commitment and profile.time_commitment != "moderate" else 0.0)
        return sum(scores) / len(scores)

    async def update_dimension(
        self,
        db: AsyncSession,
        student_id: str,
        dimension: str,
        value: dict | str | list,
    ) -> StudentProfile:
        """Directly update a single profile dimension."""
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        profile = result.scalar_one_or_none()
        if not profile:
            profile = StudentProfile(student_id=student_id)
            db.add(profile)

        if dimension == "knowledge_foundation" and isinstance(value, dict):
            profile.knowledge_foundation = {**profile.knowledge_foundation, **value}
        elif dimension == "cognitive_style" and isinstance(value, str):
            profile.cognitive_style = value
        elif dimension == "common_errors" and isinstance(value, list):
            profile.common_errors = value
        elif dimension == "learning_preferences" and isinstance(value, dict):
            profile.learning_preferences = value
        elif dimension == "learning_goals" and isinstance(value, list):
            profile.learning_goals = value
        elif dimension == "time_commitment" and isinstance(value, str):
            profile.time_commitment = value

        profile.profile_confidence = self._calculate_confidence(profile)
        profile.version += 1
        await db.flush()
        await db.refresh(profile)
        return profile

    async def get_profile(
        self, db: AsyncSession, student_id: str
    ) -> StudentProfile | None:
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_profile(
        self, db: AsyncSession, student_id: str
    ) -> StudentProfile:
        profile = await self.get_profile(db, student_id)
        if not profile:
            profile = StudentProfile(student_id=student_id)
            db.add(profile)
            await db.flush()
            await db.refresh(profile)
        return profile
