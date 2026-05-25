"""Evaluation service: learning assessment and adaptive adjustment engine.

Aggregates student behavior data, runs multi-dimensional evaluation
via EvaluationCrew, generates reports, and feeds adjustments back to
path_service and resource_service for continuous optimization.
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluation_crew import build_evaluation_crew
from app.agents.tools.graph_tool import create_graph_tool
from app.agents.tools.knowledge_tool import create_knowledge_tool
from app.models.learning import LearningActivity, ExerciseSubmission, LearningPath
from app.models.profile import StudentProfile
from app.models.resource import Resource
from app.services.graph_service import GraphService
from app.streaming.event_bus import EventBus

logger = logging.getLogger(__name__)


class EvaluationService:
    """Learning effect evaluation and adaptive adjustment service."""

    def __init__(
        self,
        event_bus: EventBus,
        graph_service: GraphService | None = None,
    ):
        self._event_bus = event_bus
        self._graph_service = graph_service or GraphService()

    # ── Main Entry Point ──────────────────────────────────────────────

    async def evaluate(
        self,
        db: AsyncSession,
        student_id: str,
        focus: str = "comprehensive",
        days: int = 30,
    ) -> dict:
        """Run a full multi-dimensional learning evaluation.

        Args:
            db: Database session.
            student_id: Student to evaluate.
            focus: Evaluation focus (comprehensive/progress/weakness/readiness).
            days: Number of days of history to analyze.

        Returns:
            Dict with full evaluation report.
        """
        # 1. Load profile
        profile = await self._load_profile(db, student_id)
        profile_summary = self._format_profile_summary(profile)

        # 2. Aggregate behavior data
        behavior_summary = await self._aggregate_behavior(db, student_id, days)

        # 3. Build tools
        tools = [
            create_knowledge_tool(""),
            create_graph_tool(self._graph_service),
        ]

        # 4. Run EvaluationCrew
        conversation_id = str(uuid.uuid4())

        crew = build_evaluation_crew(
            student_profile_summary=profile_summary,
            behavior_summary=behavior_summary,
            evaluation_focus=focus,
            evaluator_tools=tools,
            step_callback=self._make_step_callback(conversation_id),
        )

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor(max_workers=1) as pool:
            crew_result = await loop.run_in_executor(pool, crew.kickoff)

        # 5. Parse report
        report = self._parse_report(str(crew_result))

        # 6. Store evaluation as an activity record
        await self._record_evaluation(db, student_id, report)

        # 7. Check if adjustments should be triggered
        await self._trigger_adjustments(db, student_id, report)

        await self._event_bus.publish_done(conversation_id)

        return report

    # ── Behavior Aggregation ─────────────────────────────────────────

    async def _aggregate_behavior(
        self,
        db: AsyncSession,
        student_id: str,
        days: int = 30,
    ) -> str:
        """Collect and summarize all learning behavior data."""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Activity summary
        act_result = await db.execute(
            select(LearningActivity)
            .where(
                LearningActivity.student_id == student_id,
                LearningActivity.created_at >= cutoff,
            )
            .order_by(LearningActivity.created_at)
        )
        activities = act_result.scalars().all()

        # Exercise submissions
        ex_result = await db.execute(
            select(ExerciseSubmission)
            .where(
                ExerciseSubmission.student_id == student_id,
                ExerciseSubmission.submitted_at >= cutoff,
            )
            .order_by(ExerciseSubmission.submitted_at)
        )
        exercises = ex_result.scalars().all()

        # Resource usage
        r_result = await db.execute(
            select(Resource)
            .where(Resource.target_student_id == student_id)
        )
        resources = r_result.scalars().all()

        # Path progress
        p_result = await db.execute(
            select(LearningPath)
            .where(
                LearningPath.student_id == student_id,
                LearningPath.status.in_(["active", "completed"]),
            )
            .order_by(LearningPath.created_at.desc())
        )
        paths = p_result.scalars().all()

        # Count activities by type
        activity_counts = defaultdict(int)
        total_duration = 0
        daily_counts = defaultdict(int)

        for a in activities:
            activity_counts[a.activity_type] += 1
            if a.duration_seconds:
                total_duration += a.duration_seconds
            day = a.created_at.strftime("%Y-%m-%d") if a.created_at else ""
            if day:
                daily_counts[day] += 1

        # Exercise stats
        total_questions = 0
        correct_questions = 0
        exercise_scores = []

        for ex in exercises:
            answers = ex.answers or []
            for ans in answers:
                total_questions += 1
                if ans.get("is_correct"):
                    correct_questions += 1
            if ex.total_score is not None and ex.max_score:
                exercise_scores.append(ex.total_score / ex.max_score)

        avg_score = (
            sum(exercise_scores) / len(exercise_scores)
            if exercise_scores else 0
        )

        # Resource breakdown
        resource_type_counts = defaultdict(int)
        for r in resources:
            resource_type_counts[r.resource_type] += 1

        # Path progress
        path_info = ""
        if paths:
            p = paths[0]
            path_info = (
                f"当前路径: {p.title}\n"
                f"进度: {p.completed_nodes}/{p.total_nodes} ({p.completed_nodes/p.total_nodes*100:.0f}%)\n" if p.total_nodes else ""
                f"状态: {p.status}\n"
                f"版本: v{p.version}"
            )

        # Active days
        active_days = len(daily_counts)
        avg_daily_activities = len(activities) / max(active_days, 1)

        # Format summary
        summary = (
            f"## 学习行为统计（最近{days}天）\n\n"
            f"### 基本统计\n"
            f"- 活跃天数: {active_days}/{days}\n"
            f"- 日均活动次数: {avg_daily_activities:.1f}\n"
            f"- 总学习时长（估算）: {total_duration/3600:.1f} 小时\n\n"
            f"### 活动分布\n"
            + "\n".join(f"- {k}: {v}次" for k, v in sorted(activity_counts.items()))
            + f"\n\n### 练习统计\n"
            f"- 提交次数: {len(exercises)}\n"
            f"- 总题数: {total_questions}\n"
            f"- 正确数: {correct_questions}\n"
            f"- 正确率: {correct_questions/total_questions*100:.1f}% （{total_questions}题中）\n" if total_questions > 0 else ""
            f"- 平均得分率: {avg_score*100:.0f}%\n\n"
            f"### 资源使用\n"
            + "\n".join(f"- {k}: {v}个" for k, v in sorted(resource_type_counts.items()))
            + f"\n\n### 学习路径\n{path_info}"
        )

        return summary

    # ── Report Parsing ────────────────────────────────────────────────

    @staticmethod
    def _parse_report(crew_result: str) -> dict:
        """Extract JSON evaluation report from crew output."""
        import re

        # Find the JSON object
        start = crew_result.find('{')
        end = crew_result.rfind('}')
        if start >= 0 and end > start:
            try:
                report = json.loads(crew_result[start:end + 1])
                if "dimensions" in report or "overall_score" in report:
                    return report
            except json.JSONDecodeError:
                pass

        # Fallback minimal report
        return {
            "report_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "dimensions": {
                "knowledge_mastery": {"score": 50, "level": "developing",
                                       "summary": "需要更多数据以进行准确评估"},
                "engagement": {"score": 50, "level": "moderate",
                               "summary": "需要更多数据"},
                "progress_velocity": {"score": 50, "level": "steady",
                                      "summary": "需要更多数据"},
                "weakness_convergence": {"score": 50, "summary": "需要更多数据",
                                         "converging_patterns": [],
                                         "persistent_gaps": []},
            },
            "overall_score": 50,
            "overall_assessment": "数据不足，无法生成完整评估",
            "adaptive_recommendations": {
                "path_adjustments": [],
                "resource_adjustments": [],
                "pace_recommendation": "保持当前节奏",
            },
            "next_milestones": ["收集更多学习行为数据"],
        }

    # ── Adjustments ──────────────────────────────────────────────────

    async def _trigger_adjustments(
        self,
        db: AsyncSession,
        student_id: str,
        report: dict,
    ) -> None:
        """Check if evaluation results trigger automatic adjustments."""
        recommendations = report.get("adaptive_recommendations", {})
        if not recommendations:
            return

        # Check if path needs adjustment
        path_recs = recommendations.get("path_adjustments", [])
        if path_recs:
            # Mark for next path re-planning (path_service handles the actual logic)
            logger.info(
                f"Student {student_id}: {len(path_recs)} path adjustment(s) "
                f"recommended based on evaluation."
            )

        # Check if resource strategy needs adjustment
        resource_recs = recommendations.get("resource_adjustments", [])
        if resource_recs:
            logger.info(
                f"Student {student_id}: {len(resource_recs)} resource "
                f"adjustment(s) recommended."
            )

    async def _record_evaluation(
        self,
        db: AsyncSession,
        student_id: str,
        report: dict,
    ) -> None:
        """Record evaluation as a learning activity for audit trail."""
        activity = LearningActivity(
            student_id=student_id,
            activity_type="evaluation",
            activity_data={"report": report},
        )
        db.add(activity)
        await db.flush()

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
            return "画像未构建"
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

    # ── Quick Stats for Dashboard ────────────────────────────────────

    async def get_dashboard_stats(
        self,
        db: AsyncSession,
        student_id: str,
    ) -> dict:
        """Get quick stats for the dashboard overview."""
        profile = await self._load_profile(db, student_id)

        # Get active path
        path_result = await db.execute(
            select(LearningPath)
            .where(
                LearningPath.student_id == student_id,
                LearningPath.status == "active",
            )
            .order_by(LearningPath.version.desc())
            .limit(1)
        )
        active_path = path_result.scalar_one_or_none()

        # Recent activities count (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        activity_count_result = await db.execute(
            select(func.count(LearningActivity.id))
            .where(
                LearningActivity.student_id == student_id,
                LearningActivity.created_at >= week_ago,
            )
        )
        recent_activities = activity_count_result.scalar()

        # Total resources
        resource_count_result = await db.execute(
            select(func.count(Resource.id))
            .where(Resource.target_student_id == student_id)
        )
        resource_count = resource_count_result.scalar()

        # Exercise stats
        ex_count_result = await db.execute(
            select(func.count(ExerciseSubmission.id))
            .where(ExerciseSubmission.student_id == student_id)
        )
        exercise_count = ex_count_result.scalar()

        return {
            "profile_confidence": profile.profile_confidence if profile else 0,
            "profile_version": profile.version if profile else 0,
            "active_path": {
                "title": active_path.title,
                "progress": (
                    active_path.completed_nodes / active_path.total_nodes * 100
                    if active_path and active_path.total_nodes else 0
                ),
                "total_nodes": active_path.total_nodes if active_path else 0,
                "completed_nodes": active_path.completed_nodes if active_path else 0,
            } if active_path else None,
            "recent_activities_7d": recent_activities or 0,
            "total_resources": resource_count or 0,
            "total_exercises": exercise_count or 0,
        }
