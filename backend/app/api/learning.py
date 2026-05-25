"""Learning path API endpoints.

POST   /learning-paths/generate        - Generate a personalized learning path
GET    /learning-paths                 - List student's learning paths
GET    /learning-paths/{id}            - Get a single learning path
PATCH  /learning-paths/{id}/nodes/{order} - Update node status
POST   /learning-paths/{id}/replan     - Trigger path re-planning
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_student
from app.database import get_db
from app.models.student import Student
from app.schemas.learning import (
    LearningPathListResponse,
    LearningPathResponse,
    PathGenerateRequest,
    PathGenerateResponse,
    PathNodeUpdateRequest,
)
from app.services.path_service import PathService
from app.streaming.event_bus import EventBus

router = APIRouter(tags=["LearningPaths"])

path_service: PathService | None = None
event_bus: EventBus | None = None


def init_learning_api(ps: PathService, eb: EventBus):
    """Initialize module-level service references."""
    global path_service, event_bus
    path_service = ps
    event_bus = eb


@router.post("/generate", response_model=PathGenerateResponse,
             status_code=status.HTTP_201_CREATED)
async def generate_learning_path(
    data: PathGenerateRequest,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Generate a personalized learning path based on student profile and goals."""
    if not path_service:
        raise HTTPException(status_code=503, detail="Path service not available")

    try:
        learning_path = await path_service.generate_path(
            db=db,
            student_id=current_student.id,
            learning_goal=data.learning_goal,
            target_topic=data.target_topic,
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Path generation failed: {str(e)}",
        )

    return PathGenerateResponse(
        message="学习路径生成成功",
        path_id=learning_path.id,
        total_nodes=learning_path.total_nodes,
        estimated_hours=learning_path.estimated_total_hours or 0,
    )


@router.get("", response_model=LearningPathListResponse)
async def list_learning_paths(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """List all learning paths for the current student."""
    if not path_service:
        raise HTTPException(status_code=503, detail="Path service not available")

    paths = await path_service.list_paths(db, current_student.id)

    return LearningPathListResponse(
        items=[
            LearningPathResponse(
                id=p.id,
                student_id=p.student_id,
                title=p.title,
                description=p.description,
                path_nodes=p.path_nodes,
                total_nodes=p.total_nodes,
                completed_nodes=p.completed_nodes,
                estimated_total_hours=p.estimated_total_hours,
                status=p.status,
                version=p.version,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in paths
        ],
        total=len(paths),
    )


@router.get("/active", response_model=LearningPathResponse)
async def get_active_path(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Get the current active learning path."""
    if not path_service:
        raise HTTPException(status_code=503, detail="Path service not available")

    path = await path_service.get_path(db, current_student.id)
    if not path:
        raise HTTPException(status_code=404, detail="No active learning path found")

    return LearningPathResponse(
        id=path.id,
        student_id=path.student_id,
        title=path.title,
        description=path.description,
        path_nodes=path.path_nodes,
        total_nodes=path.total_nodes,
        completed_nodes=path.completed_nodes,
        estimated_total_hours=path.estimated_total_hours,
        status=path.status,
        version=path.version,
        created_at=path.created_at,
        updated_at=path.updated_at,
    )


@router.get("/{path_id}", response_model=LearningPathResponse)
async def get_learning_path(
    path_id: str,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific learning path by ID."""
    if not path_service:
        raise HTTPException(status_code=503, detail="Path service not available")

    path = await path_service.get_path_by_id(db, path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    if path.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return LearningPathResponse(
        id=path.id,
        student_id=path.student_id,
        title=path.title,
        description=path.description,
        path_nodes=path.path_nodes,
        total_nodes=path.total_nodes,
        completed_nodes=path.completed_nodes,
        estimated_total_hours=path.estimated_total_hours,
        status=path.status,
        version=path.version,
        created_at=path.created_at,
        updated_at=path.updated_at,
    )


@router.patch("/{path_id}/nodes/{node_order}", response_model=LearningPathResponse)
async def update_node_status(
    path_id: str,
    node_order: int,
    data: PathNodeUpdateRequest,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a single node in a learning path."""
    if not path_service:
        raise HTTPException(status_code=503, detail="Path service not available")

    # Verify ownership
    path = await path_service.get_path_by_id(db, path_id)
    if not path:
        raise HTTPException(status_code=404, detail="Learning path not found")
    if path.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")

    valid_statuses = {"ready", "in_progress", "completed", "skipped"}
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}",
        )

    updated_path = await path_service.update_node_status(
        db, path_id, node_order, data.status,
    )
    await db.commit()

    if not updated_path:
        raise HTTPException(status_code=404, detail="Node not found in path")

    return LearningPathResponse(
        id=updated_path.id,
        student_id=updated_path.student_id,
        title=updated_path.title,
        description=updated_path.description,
        path_nodes=updated_path.path_nodes,
        total_nodes=updated_path.total_nodes,
        completed_nodes=updated_path.completed_nodes,
        estimated_total_hours=updated_path.estimated_total_hours,
        status=updated_path.status,
        version=updated_path.version,
        created_at=updated_path.created_at,
        updated_at=updated_path.updated_at,
    )


@router.post("/replan", response_model=PathGenerateResponse,
             status_code=status.HTTP_201_CREATED)
async def replan_path(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Trigger re-planning of the learning path based on current profile."""
    if not path_service:
        raise HTTPException(status_code=503, detail="Path service not available")

    try:
        new_path = await path_service.adjust_path(
            db, current_student.id, "手动触发重规划",
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Path re-planning failed: {str(e)}",
        )

    if not new_path:
        raise HTTPException(status_code=500, detail="Path re-planning returned no result")

    return PathGenerateResponse(
        message="学习路径重规划完成",
        path_id=new_path.id,
        total_nodes=new_path.total_nodes,
        estimated_hours=new_path.estimated_total_hours or 0,
    )
