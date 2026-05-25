"""Resource generation and management API endpoints.

POST /resources/generate     - Trigger resource generation
GET  /resources/{id}         - Get a single resource
GET  /resources              - List/filter resources
GET  /resources/{id}/stream  - SSE progress stream for a generation task
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_student
from app.database import get_db
from app.models.resource import Resource
from app.models.student import Student
from app.schemas.resource import (
    ResourceGenerateRequest,
    ResourceGenerateResponse,
    ResourceListResponse,
    ResourceResponse,
)
from app.services.resource_service import ResourceService
from app.streaming.event_bus import EventBus
from app.streaming.sse_manager import SSEManager

router = APIRouter(tags=["Resources"])

resource_service: ResourceService | None = None
event_bus: EventBus | None = None
sse_manager: SSEManager | None = None


def init_resource_api(rs: ResourceService, eb: EventBus, sm: SSEManager):
    """Initialize module-level service references. Called during app startup."""
    global resource_service, event_bus, sse_manager
    resource_service = rs
    event_bus = eb
    sse_manager = sm


@router.post("/generate", response_model=ResourceGenerateResponse,
             status_code=status.HTTP_202_ACCEPTED)
async def generate_resources(
    data: ResourceGenerateRequest,
    background_tasks: BackgroundTasks,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Trigger personalized resource generation for one or more knowledge topics.

    Generation runs asynchronously in the background. The client should
    connect to the returned conversation's SSE stream for real-time progress.
    """
    if not resource_service or not event_bus:
        raise HTTPException(status_code=503, detail="Resource service not available")

    # Validate resource types if specified
    valid_types = {
        "course_doc", "mind_map", "exercise", "code_case",
        "ppt", "project", "reading", "video_script",
    }
    if data.resource_types:
        invalid = set(data.resource_types) - valid_types
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"无效的资源类型: {', '.join(invalid)}。有效类型: {', '.join(sorted(valid_types))}",
            )

    # Validate topic codes exist
    from app.models.knowledge import KnowledgeNode
    result = await db.execute(
        select(KnowledgeNode.topic_code).where(
            KnowledgeNode.topic_code.in_(data.topic_codes)
        )
    )
    existing_codes = {row[0] for row in result.fetchall()}
    missing = set(data.topic_codes) - existing_codes
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"无效的知识点代码: {', '.join(missing)}",
        )

    # Create a conversation to tie the generation to
    from app.services.conversation_service import create_conversation
    conversation = await create_conversation(
        db, current_student.id, "resource_request",
        f"资源生成: {', '.join(data.topic_codes)}"
    )

    task_count = len(data.topic_codes) * (len(data.resource_types) if data.resource_types else 5)

    # Trigger background generation
    background_tasks.add_task(
        resource_service.generate_resources_background,
        conversation_id=conversation.id,
        student_id=current_student.id,
        topic_codes=data.topic_codes,
        resource_types=data.resource_types,
        constraints=data.constraints,
    )

    return ResourceGenerateResponse(
        message="资源生成已启动，请通过SSE端点获取实时进度",
        conversation_id=conversation.id,
        topic_codes=data.topic_codes,
        task_count=task_count,
    )


@router.get("", response_model=ResourceListResponse)
async def list_resources(
    resource_type: str | None = Query(None, description="Filter by resource type"),
    difficulty: str | None = Query(None, description="Filter by difficulty"),
    review_status: str | None = Query("approved", description="Filter by review status"),
    knowledge_node_id: str | None = Query(
        None, description="Filter by knowledge node"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """List generated resources with optional filters.

    By default, only returns approved resources. Use review_status=all
    to include all statuses.
    """
    conditions = []

    if resource_type:
        conditions.append(Resource.resource_type == resource_type)
    if difficulty:
        conditions.append(Resource.difficulty == difficulty)
    if review_status and review_status != "all":
        conditions.append(Resource.review_status == review_status)
    if knowledge_node_id:
        conditions.append(Resource.knowledge_node_ids.contains([str(knowledge_node_id)]))

    # Only show the current student's resources (or all if admin)
    conditions.append(Resource.target_student_id == current_student.id)

    # Count total
    count_query = select(func.count(Resource.id))
    for cond in conditions:
        count_query = count_query.where(cond)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch page
    query = (
        select(Resource)
        .order_by(Resource.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    for cond in conditions:
        query = query.where(cond)

    result = await db.execute(query)
    resources = result.scalars().all()

    return ResourceListResponse(
        items=[
            ResourceResponse(
                id=r.id,
                resource_type=r.resource_type,
                title=r.title,
                knowledge_node_ids=r.knowledge_node_ids,
                difficulty=r.difficulty,
                review_status=r.review_status,
                review_notes=r.review_notes,
                content=r.content,
                created_at=r.created_at,
            )
            for r in resources
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{resource_id}", response_model=ResourceResponse)
async def get_resource(
    resource_id: str,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Get a single resource by ID."""
    result = await db.execute(
        select(Resource).where(Resource.id == resource_id)
    )
    resource = result.scalar_one_or_none()

    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    if resource.target_student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return ResourceResponse(
        id=resource.id,
        resource_type=resource.resource_type,
        title=resource.title,
        knowledge_node_ids=resource.knowledge_node_ids,
        difficulty=resource.difficulty,
        review_status=resource.review_status,
        review_notes=resource.review_notes,
        content=resource.content,
        created_at=resource.created_at,
    )


@router.get("/generate/{task_id}/stream")
async def stream_generation_progress(
    task_id: str,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for streaming resource generation progress.

    The task_id is the conversation_id returned by POST /resources/generate.
    """
    if not sse_manager:
        raise HTTPException(status_code=503, detail="SSE not available")

    # Verify the conversation exists and belongs to this student
    from app.models.conversation import Conversation
    result = await db.execute(
        select(Conversation).where(Conversation.id == task_id)
    )
    conv = result.scalar_one_or_none()

    if not conv:
        raise HTTPException(status_code=404, detail="Generation task not found")
    if conv.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return sse_manager.streaming_response(str(task_id))
