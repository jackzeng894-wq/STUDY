"""Conversation and message request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class ConversationCreate(BaseModel):
    conversation_type: str  # profile_building | resource_request | path_planning | tutoring
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    student_id: str
    conversation_type: str
    title: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    metadata: dict = {}
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationWithMessages(BaseModel):
    id: str
    student_id: str
    conversation_type: str
    title: str | None = None
    messages: list[MessageResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
