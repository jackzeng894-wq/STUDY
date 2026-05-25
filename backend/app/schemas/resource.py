"""Pydantic schemas for resource generation and management."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResourceGenerateRequest(BaseModel):
    """Request to trigger resource generation for specific knowledge topics."""

    topic_codes: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Knowledge point topic codes to generate resources for.",
    )
    resource_types: Optional[list[str]] = Field(
        default=None,
        description=(
            "Specific resource types to generate. If None, the planner "
            "decides the optimal mix. Valid: course_doc, mind_map, exercise, "
            "code_case, ppt, project, reading, video_script."
        ),
    )
    constraints: str = Field(
        default="",
        description="Optional student-specified constraints or requirements.",
    )

    # Allow specifying which field types are permitted
    class Config:
        json_schema_extra = {
            "example": {
                "topic_codes": ["js_async_promise", "js_closure"],
                "resource_types": ["course_doc", "exercise", "code_case"],
                "constraints": "希望多些实际代码例子，练习题难度适中",
            }
        }


class ResourceResponse(BaseModel):
    """Public resource representation."""

    id: str
    resource_type: str
    title: str
    knowledge_node_ids: list[str]
    difficulty: str
    review_status: str
    review_notes: Optional[str] = None
    content: dict = Field(default_factory=dict)
    created_at: datetime

    class Config:
        from_attributes = True


class ResourceListResponse(BaseModel):
    """Paginated resource list."""

    items: list[ResourceResponse]
    total: int
    skip: int
    limit: int


class ResourceGenerateResponse(BaseModel):
    """Response after triggering resource generation."""

    message: str
    conversation_id: str
    topic_codes: list[str]
    task_count: int

    class Config:
        json_schema_extra = {
            "example": {
                "message": "资源生成已启动",
                "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
                "topic_codes": ["js_closure"],
                "task_count": 5,
            }
        }
