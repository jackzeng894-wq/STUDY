"""Conversation API endpoints.

Handles conversation CRUD and the critical SSE streaming endpoint
that connects frontend to agent output. Routes messages to the
appropriate service based on conversation_type:
  - profile_building → ProfileService
  - tutoring → TutoringService
  - resource_request → handled by resource API directly
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_student
from app.database import get_db
from app.models.student import Student
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationWithMessages,
    MessageCreate,
    MessageResponse,
)
from app.services.conversation_service import (
    add_message,
    build_messages_context,
    create_conversation,
    delete_conversation,
    get_conversation,
    get_messages,
    list_conversations,
)
from app.services.profile_service import ProfileService
from app.services.tutoring_service import TutoringService
from app.streaming.event_bus import EventBus
from app.streaming.sse_manager import SSEManager

router = APIRouter(tags=["Conversations"])

event_bus: EventBus | None = None
sse_manager: SSEManager | None = None
profile_service: ProfileService | None = None
tutoring_service: TutoringService | None = None


def init_conversation_api(
    eb: EventBus,
    sm: SSEManager,
    ps: ProfileService,
    ts: TutoringService | None = None,
):
    """Initialize module-level service references. Called during app startup."""
    global event_bus, sse_manager, profile_service, tutoring_service
    event_bus = eb
    sse_manager = sm
    profile_service = ps
    tutoring_service = ts


@router.get("", response_model=list[ConversationResponse])
async def list_conversations_route(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await list_conversations(db, current_student.id)


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation_route(
    data: ConversationCreate,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    return await create_conversation(
        db, current_student.id, data.conversation_type, data.title
    )


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation_route(
    conversation_id: str,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")
    return ConversationWithMessages(
        id=conv.id,
        student_id=conv.student_id,
        conversation_type=conv.conversation_type,
        title=conv.title,
        messages=[
            MessageResponse(
                id=m.id,
                conversation_id=m.conversation_id,
                role=m.role,
                content=m.content,
                metadata=m.message_metadata,
                created_at=m.created_at,
            )
            for m in (conv.messages or [])
        ],
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    background_tasks: BackgroundTasks,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Send a message. Returns immediately; agent processing runs in background.

    Routes to ProfileService for profile_building conversations, or
    TutoringService for tutoring conversations.
    """
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Save user message
    message = await add_message(db, conversation_id, "user", data.content)

    # Build conversation history for context
    messages = await get_messages(db, conversation_id)
    history = build_messages_context(messages[:-1])  # Exclude the just-saved message

    # Route to appropriate service based on conversation type
    conv_type = conv.conversation_type

    if conv_type == "profile_building":
        if not profile_service:
            raise HTTPException(status_code=503, detail="Profile service unavailable")
        background_tasks.add_task(
            profile_service.process_message_background,
            conversation_id=conversation_id,
            student_id=current_student.id,
            content=data.content,
        )

    elif conv_type == "tutoring":
        if not tutoring_service:
            raise HTTPException(status_code=503, detail="Tutoring service unavailable")
        background_tasks.add_task(
            tutoring_service.process_question_background,
            conversation_id=conversation_id,
            student_id=current_student.id,
            question=data.content,
            conversation_history=history,
        )

    elif conv_type == "resource_request":
        # Resource requests are handled by POST /resources/generate endpoint
        # If a message is sent in a resource_request conversation, treat as tutoring
        if tutoring_service:
            background_tasks.add_task(
                tutoring_service.process_question_background,
                conversation_id=conversation_id,
                student_id=current_student.id,
                question=data.content,
                conversation_history=history,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Resource request conversations use the resource generation endpoint",
            )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown conversation type: {conv_type}",
        )

    return MessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        role=message.role,
        content=message.content,
        metadata=message.message_metadata,
        created_at=message.created_at,
    )


@router.get("/{conversation_id}/stream")
async def stream_conversation(
    conversation_id: str,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """SSE endpoint for streaming agent output in real-time.

    The client connects here after sending a message to receive
    token, agent_step, profile_update, and done events.
    """
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not sse_manager:
        raise HTTPException(status_code=503, detail="SSE not available")

    return sse_manager.streaming_response(str(conversation_id))


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_route(
    conversation_id: str,
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    conv = await get_conversation(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.student_id != current_student.id:
        raise HTTPException(status_code=403, detail="Access denied")
    await delete_conversation(db, conversation_id)
