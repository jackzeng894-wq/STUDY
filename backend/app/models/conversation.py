"""Conversation and message models for chat history."""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Conversation(Base):
    """A conversation session between a student and the multi-agent system."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )
    conversation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # profile_building | resource_request | path_planning | tutoring
    title: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan",
        order_by="Message.created_at"
    )


class Message(Base):
    """A single message within a conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    # user | assistant | system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    # Structured data: profile_updates, resource_cards, agent_status, etc.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
