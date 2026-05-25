"""Pydantic schemas for learning paths and activities."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PathGenerateRequest(BaseModel):
    """Request to generate a personalized learning path."""

    learning_goal: str = Field(
        default="",
        description="Student's learning goal description.",
    )
    target_topic: str = Field(
        default="",
        description="Specific target knowledge point topic_code.",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "learning_goal": "想在一个月内掌握JavaScript异步编程",
                "target_topic": "js_async_promise",
            }
        }


class PathNodeResponse(BaseModel):
    """A single node in a learning path."""

    order: int
    knowledge_node_id: str
    topic_code: str = ""
    title: str = ""
    status: str = "ready"
    recommended_resources: list[str] = Field(default_factory=list)
    estimated_minutes: int = 45
    rationale: str = ""


class LearningPathResponse(BaseModel):
    """Public learning path representation."""

    id: str
    student_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    path_nodes: list[dict] = Field(default_factory=list)
    total_nodes: int = 0
    completed_nodes: int = 0
    estimated_total_hours: Optional[float] = None
    status: str = "active"
    version: int = 1
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PathNodeUpdateRequest(BaseModel):
    """Request to update a single node's status in a learning path."""

    status: str = Field(
        ...,
        description="New status: ready, in_progress, completed, skipped",
    )

    class Config:
        json_schema_extra = {
            "example": {"status": "completed"}
        }


class LearningPathListResponse(BaseModel):
    """List of learning paths."""

    items: list[LearningPathResponse]
    total: int


class PathGenerateResponse(BaseModel):
    """Response after triggering path generation."""

    message: str
    path_id: str
    total_nodes: int
    estimated_hours: float

    class Config:
        json_schema_extra = {
            "example": {
                "message": "学习路径生成成功",
                "path_id": "550e8400-e29b-41d4-a716-446655440000",
                "total_nodes": 15,
                "estimated_hours": 12.5,
            }
        }
