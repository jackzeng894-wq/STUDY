"""Student profile API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_student
from app.database import get_db
from app.models.student import Student
from app.schemas.profile import (
    ProfileDimensionResponse,
    ProfileUpdateRequest,
    StudentProfileResponse,
)
from app.services.conversation_service import create_conversation
from app.services.profile_service import ProfileService

router = APIRouter(tags=["Profiles"])

profile_service: ProfileService | None = None


def init_profile_api(ps: ProfileService):
    global profile_service
    profile_service = ps


@router.get("", response_model=StudentProfileResponse)
async def get_profile(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    if not profile_service:
        raise HTTPException(status_code=503, detail="Profile service not available")

    profile = await profile_service.get_or_create_profile(db, current_student.id)
    return StudentProfileResponse(
        id=profile.id,
        student_id=profile.student_id,
        knowledge_foundation=profile.knowledge_foundation,
        cognitive_style=profile.cognitive_style,
        common_errors=profile.common_errors,
        learning_preferences=profile.learning_preferences,
        learning_goals=profile.learning_goals,
        time_commitment=profile.time_commitment,
        profile_confidence=profile.profile_confidence,
        version=profile.version,
        updated_at=profile.updated_at,
    )


@router.get("/dimensions", response_model=list[ProfileDimensionResponse])
async def get_profile_dimensions(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    if not profile_service:
        raise HTTPException(status_code=503, detail="Profile service not available")

    profile = await profile_service.get_or_create_profile(db, current_student.id)

    dimensions = [
        ("knowledge_foundation", profile.knowledge_foundation),
        ("cognitive_style", profile.cognitive_style),
        ("common_errors", profile.common_errors),
        ("learning_preferences", profile.learning_preferences),
        ("learning_goals", profile.learning_goals),
        ("time_commitment", profile.time_commitment),
    ]

    return [
        ProfileDimensionResponse(dimension=name, value={"data": value})
        for name, value in dimensions
    ]


@router.post("/refresh", status_code=status.HTTP_201_CREATED)
async def refresh_profile(
    current_student: Student = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
):
    """Start a new profile-building conversation to refresh the profile."""
    conversation = await create_conversation(
        db, current_student.id, "profile_building", "画像评估更新"
    )
    return {"conversation_id": str(conversation.id)}
