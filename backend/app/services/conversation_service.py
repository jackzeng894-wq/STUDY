"""Conversation and message CRUD service."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation, Message


async def create_conversation(
    db: AsyncSession,
    student_id: str,
    conversation_type: str,
    title: str | None = None,
) -> Conversation:
    conversation = Conversation(
        student_id=student_id,
        conversation_type=conversation_type,
        title=title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


async def get_conversation(
    db: AsyncSession, conversation_id: str
) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .options(selectinload(Conversation.messages))
    )
    return result.scalar_one_or_none()


async def list_conversations(
    db: AsyncSession, student_id: str
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.student_id == student_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def add_message(
    db: AsyncSession,
    conversation_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
) -> Message:
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        message_metadata=metadata or {},
    )
    db.add(message)
    # Touch conversation updated_at
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        from datetime import datetime
        conv.updated_at = datetime.utcnow()

    await db.flush()
    await db.refresh(message)
    return message


async def get_messages(
    db: AsyncSession, conversation_id: str
) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


async def delete_conversation(
    db: AsyncSession, conversation_id: str
) -> bool:
    conversation = await get_conversation(db, conversation_id)
    if not conversation:
        return False
    await db.delete(conversation)
    await db.flush()
    return True


def build_messages_context(messages: list[Message]) -> str:
    """Format message history for LLM context injection."""
    lines = []
    for m in messages:
        role_label = {"user": "学生", "assistant": "系统", "system": "系统提示"}.get(
            m.role, m.role
        )
        lines.append(f"[{role_label}]: {m.content}")
    return "\n".join(lines)
