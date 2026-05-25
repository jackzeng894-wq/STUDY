"""Student profile request/response schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel


class KnowledgeFoundationItem(BaseModel):
    topic_code: str
    mastery: str  # beginner | intermediate | advanced | expert


class CommonErrorItem(BaseModel):
    pattern: str
    topic: str
    frequency: int = 1


class LearningPreference(BaseModel):
    resource_types: list[str] = []
    pace: str = "moderate"  # slow | moderate | fast


class LearningGoalItem(BaseModel):
    goal: str
    priority: str = "medium"  # high | medium | low
    target_date: str | None = None


class StudentProfileResponse(BaseModel):
    id: str
    student_id: str
    knowledge_foundation: dict = {}
    cognitive_style: str = "unknown"
    common_errors: list = []
    learning_preferences: dict = {}
    learning_goals: list = []
    time_commitment: str = "moderate"
    profile_confidence: float = 0.0
    version: int = 1
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProfileDimensionResponse(BaseModel):
    dimension: str
    value: dict


class ProfileUpdateRequest(BaseModel):
    dimension: str
    value: dict
