"""Learning evaluation and dashboard API endpoints.

POST /evaluation/assess    - Run a multi-dimensional learning assessment
GET  /evaluation/dashboard  - Get dashboard quick stats
GET  /evaluation/report     - Get latest evaluation report
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_student
from app.database import get_db
from app.models.student import Student
from app.services.evaluation_service import EvaluationService
from app.streaming.event_bus import EventBus

router = APIRouter(tags=["Evaluation"])

evaluation_service: EvaluationService | None = None
event_bus: EventBus | None = None


def init_evaluation_api(es: EvaluationService, eb: EventBus):
    """Initialize module-level service references."""
    global evaluation_service, event_bus
    evaluation_service = es
    event_bus = eb


@router.post("/assess", status_code=status.HTTP_202_ACCEPTED)
async def assess_learning(
    focus: str = Query(
        "comprehensive",
        description="Evaluation focus: comprehensive, progress, weakness, readiness",
    ),
    days: int = Query(30, ge=7, le=90, description="Days of history to analyze"),
    background_tasks: BackgroundTasks = None,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Run a multi-dimensional learning evaluation.

    Evaluation dimensions: knowledge mastery, engagement, progress velocity,
    weakness convergence. Returns a structured assessment report with
    adaptive recommendations.
    """
    if not evaluation_service:
        raise HTTPException(status_code=503, detail="Evaluation service not available")

    valid_focus = {"comprehensive", "progress", "weakness", "readiness"}
    if focus not in valid_focus:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid focus. Must be one of: {', '.join(sorted(valid_focus))}",
        )

    report = await evaluation_service.evaluate(
        db=db,
        student_id=current_student.id,
        focus=focus,
        days=days,
    )
    await db.commit()

    return report


@router.get("/dashboard")
async def get_dashboard(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Get quick stats for the student dashboard.

    Returns profile status, active path progress, recent activity count,
    and resource/exercise totals.
    """
    if not evaluation_service:
        raise HTTPException(status_code=503, detail="Evaluation service not available")

    stats = await evaluation_service.get_dashboard_stats(db, current_student.id)
    return stats


@router.get("/report")
async def get_latest_report(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent evaluation report."""
    from sqlalchemy import select

    from app.models.learning import LearningActivity

    result = await db.execute(
        select(LearningActivity)
        .where(
            LearningActivity.student_id == current_student.id,
            LearningActivity.activity_type == "evaluation",
        )
        .order_by(LearningActivity.created_at.desc())
        .limit(1)
    )
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(status_code=404, detail="No evaluation report found")

    return activity.activity_data.get("report", {})
