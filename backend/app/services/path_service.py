"""Path service: orchestrates learning path generation and adjustment.

Flow:
1. Load student profile + learning goals
2. Run graph algorithms (topo sort, shortest path, PageRank, gap detection)
3. Trigger PathCrew (PathDesigner → PathEvaluator)
4. Parse and save the personalized learning path
5. Publish progress via SSE EventBus

Path adjustment is triggered when profile changes exceed a threshold.
"""

import asyncio
import json
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.path_crew import build_path_crew
from app.agents.tools.graph_tool import create_graph_tool
from app.agents.tools.knowledge_tool import create_knowledge_tool
from app.models.learning import LearningPath
from app.models.profile import StudentProfile
from app.services.graph_service import GraphService
from app.streaming.event_bus import EventBus

logger = logging.getLogger(__name__)

# Threshold for triggering path re-planning
PROFILE_CHANGE_THRESHOLD = 0.3  # 30% confidence change


class PathService:
    """Orchestrates learning path generation and dynamic adjustment."""

    def __init__(
        self,
        event_bus: EventBus,
        graph_service: GraphService | None = None,
    ):
        self._event_bus = event_bus
        self._graph_service = graph_service or GraphService()

    # ── Main Entry Point ──────────────────────────────────────────────

    async def generate_path(
        self,
        db: AsyncSession,
        student_id: str,
        learning_goal: str = "",
        target_topic: str = "",
    ) -> LearningPath:
        """Generate a personalized learning path for a student.

        Args:
            db: Database session.
            student_id: The student to generate a path for.
            learning_goal: Student's stated learning goal.
            target_topic: Specific target knowledge point topic_code.

        Returns:
            The generated LearningPath ORM instance.
        """
        # 1. Load profile
        profile = await self._load_profile(db, student_id)

        # 2. Build/refresh graph
        await self._graph_service.rebuild_graph(db)

        # 3. Run graph algorithms
        graph_analysis = await self._analyze_graph(
            db, profile, target_topic,
        )

        # 4. Format profile summary
        profile_summary = self._format_profile_summary(profile)

        # 5. Build tools
        rag_context = ""  # PathCrew uses graph data, not RAG text
        tools = [
            create_knowledge_tool(rag_context),
            create_graph_tool(self._graph_service),
        ]

        # 6. Build and run PathCrew
        conversation_id = str(uuid.uuid4())

        await self._event_bus.publish(conversation_id, {
            "event": "agent_step",
            "data": {
                "name": "PathDesigner",
                "role": "学习路径规划专家",
                "status": "thinking",
                "progress": 0.0,
            },
        })

        crew = build_path_crew(
            student_profile_summary=profile_summary,
            graph_analysis=graph_analysis,
            learning_goal=learning_goal,
            designer_tools=tools,
            evaluator_tools=tools,
            step_callback=self._make_step_callback(conversation_id),
        )

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            crew_result = await loop.run_in_executor(pool, crew.kickoff)

        # 7. Parse the path from crew output
        path_data = self._parse_path_result(str(crew_result))

        # 8. Persist the learning path
        learning_path = await self._persist_path(
            db, student_id, path_data, learning_goal,
        )

        # 9. Publish done
        await self._event_bus.publish_done(conversation_id)

        return learning_path

    # ── Path Adjustment ──────────────────────────────────────────────

    async def should_replan(
        self,
        db: AsyncSession,
        student_id: str,
    ) -> bool:
        """Check if the current path needs re-planning based on profile changes."""
        profile = await self._load_profile(db, student_id)
        if not profile:
            return False

        # Get current active path
        result = await db.execute(
            select(LearningPath)
            .where(
                LearningPath.student_id == student_id,
                LearningPath.status == "active",
            )
            .order_by(LearningPath.version.desc())
            .limit(1)
        )
        current_path = result.scalar_one_or_none()

        if not current_path:
            return True  # No path exists, need to generate one

        # Check if profile confidence has changed significantly
        if profile.profile_confidence > PROFILE_CHANGE_THRESHOLD:
            # Check if completion ratio is low (student might be stuck)
            if current_path.total_nodes > 0:
                completion_ratio = current_path.completed_nodes / current_path.total_nodes
                if completion_ratio < 0.3 and current_path.version > 1:
                    return True

        return False

    async def adjust_path(
        self,
        db: AsyncSession,
        student_id: str,
        trigger_reason: str = "",
    ) -> LearningPath | None:
        """Re-plan and generate a new version of the learning path."""
        # Mark old paths as superseded
        result = await db.execute(
            select(LearningPath)
            .where(
                LearningPath.student_id == student_id,
                LearningPath.status == "active",
            )
        )
        for old_path in result.scalars().all():
            old_path.status = "superseded"

        await db.flush()

        # Generate new path
        return await self.generate_path(db, student_id)

    # ── Graph Analysis ───────────────────────────────────────────────

    async def _analyze_graph(
        self,
        db: AsyncSession,
        profile: StudentProfile | None,
        target_topic: str,
    ) -> dict:
        """Run all relevant graph algorithms and collect results."""
        analysis = {}

        # Topological sort
        analysis["topological_order"] = await self._graph_service.topological_sort(db)

        # PageRank hub nodes
        analysis["hub_nodes"] = await self._graph_service.pagerank(db, top_k=15)

        # Shortest path and gap detection (if we can determine current/target topics)
        if profile and profile.knowledge_foundation:
            mastered = [
                tc for tc, level in profile.knowledge_foundation.items()
                if level in ("intermediate", "advanced", "expert")
            ]
            weak = [
                tc for tc, level in profile.knowledge_foundation.items()
                if level in ("beginner", "unknown")
            ]

            if target_topic and mastered:
                # Find a mastered topic to start from
                start_topic = mastered[0] if mastered else None
                if start_topic:
                    analysis["shortest_path"] = await self._graph_service.shortest_path(
                        db, from_topic=start_topic, to_topic=target_topic,
                    )

            if weak:
                # Detect gaps for the weakest areas
                worst_topic = weak[0] if weak else target_topic
                if worst_topic:
                    analysis["gaps"] = await self._graph_service.detect_gaps(
                        db, mastered_topics=mastered, target_topic=worst_topic,
                    )

        # Graph stats
        analysis["graph_stats"] = await self._graph_service.get_stats(db)

        return analysis

    # ── Helpers ──────────────────────────────────────────────────────

    async def _load_profile(
        self, db: AsyncSession, student_id: str,
    ) -> StudentProfile | None:
        result = await db.execute(
            select(StudentProfile).where(StudentProfile.student_id == student_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    def _format_profile_summary(profile: StudentProfile | None) -> str:
        if not profile:
            return "学生画像尚未构建，无法进行个性化路径规划。"
        return (
            f"知识基础: {json.dumps(profile.knowledge_foundation, ensure_ascii=False)}\n"
            f"认知风格: {profile.cognitive_style}\n"
            f"学习偏好: {json.dumps(profile.learning_preferences, ensure_ascii=False)}\n"
            f"学习目标: {json.dumps(profile.learning_goals, ensure_ascii=False)}\n"
            f"常见错误: {json.dumps(profile.common_errors, ensure_ascii=False)}\n"
            f"时间投入: {profile.time_commitment}\n"
            f"画像置信度: {profile.profile_confidence:.2f}"
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

    @staticmethod
    def _parse_path_result(crew_result: str) -> dict:
        """Parse the PathCrew output into structured path data.

        Extracts the JSON path from the sequential crew result.
        """
        import re

        # Try to extract JSON from result
        # PathDesigner outputs first, then PathEvaluator
        # We need the designer's JSON output

        # Find all JSON objects in the result
        json_objects = re.findall(r'\{[^{}]*\}', crew_result)

        for obj_str in json_objects:
            try:
                data = json.loads(obj_str)
                if "nodes" in data and isinstance(data.get("nodes"), list):
                    # Also try to extract evaluation
                    eval_data = None
                    for obj_str2 in json_objects:
                        try:
                            d2 = json.loads(obj_str2)
                            if "overall_score" in d2 and "adjustments" in d2:
                                eval_data = d2
                                break
                        except json.JSONDecodeError:
                            continue

                    data["evaluation"] = eval_data
                    return data
            except json.JSONDecodeError:
                continue

        # Fallback: build a minimal path from topological order
        return {
            "path_title": "JavaScript学习路径",
            "description": "基于知识图谱的基本学习路径（未能解析AI生成的完整路径）",
            "estimated_total_hours": 40,
            "nodes": [],
            "evaluation": {"overall_score": 50, "passed": False,
                          "summary": "需要重新生成路径"},
        }

    async def _persist_path(
        self,
        db: AsyncSession,
        student_id: str,
        path_data: dict,
        learning_goal: str,
    ) -> LearningPath:
        """Create and save a LearningPath database record."""
        nodes = path_data.get("nodes", [])

        # Calculate estimated total hours from node estimates
        total_minutes = sum(n.get("estimated_minutes", 45) for n in nodes)
        estimated_hours = total_minutes / 60.0

        learning_path = LearningPath(
            student_id=student_id,
            title=path_data.get("path_title", "个性化学习路径"),
            description=path_data.get("description", learning_goal or ""),
            path_nodes=nodes,
            total_nodes=len(nodes),
            completed_nodes=0,
            estimated_total_hours=estimated_hours,
            status="active",
            version=1,
        )

        db.add(learning_path)
        await db.flush()
        await db.refresh(learning_path)
        return learning_path

    # ── Query Methods ────────────────────────────────────────────────

    async def get_path(
        self, db: AsyncSession, student_id: str,
    ) -> LearningPath | None:
        """Get the student's current active learning path."""
        result = await db.execute(
            select(LearningPath)
            .where(
                LearningPath.student_id == student_id,
                LearningPath.status == "active",
            )
            .order_by(LearningPath.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_path_by_id(
        self, db: AsyncSession, path_id: str,
    ) -> LearningPath | None:
        result = await db.execute(
            select(LearningPath).where(LearningPath.id == path_id)
        )
        return result.scalar_one_or_none()

    async def list_paths(
        self, db: AsyncSession, student_id: str,
    ) -> list[LearningPath]:
        result = await db.execute(
            select(LearningPath)
            .where(LearningPath.student_id == student_id)
            .order_by(LearningPath.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_node_status(
        self,
        db: AsyncSession,
        path_id: str,
        node_order: int,
        new_status: str,
    ) -> LearningPath | None:
        """Update the status of a single node in a learning path."""
        path = await self.get_path_by_id(db, path_id)
        if not path:
            return None

        nodes = path.path_nodes
        for node in nodes:
            if node.get("order") == node_order:
                node["status"] = new_status
                if new_status == "completed":
                    path.completed_nodes += 1
                break

        # Check if path is fully complete
        if path.completed_nodes >= path.total_nodes:
            path.status = "completed"

        path.path_nodes = nodes  # Trigger ORM dirty tracking
        await db.flush()
        await db.refresh(path)
        return path
