"""Student profile model with 6 dynamic dimensions stored as JSON."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StudentProfile(Base):
    """Learning profile with 6 dimensions, stored as JSON for flexibility.

    Dimensions:
      1. knowledge_foundation - per-topic mastery levels
      2. cognitive_style - visual/auditory/kinesthetic/etc.
      3. common_errors - recurring error patterns with frequency
      4. learning_preferences - preferred resource types and pace
      5. learning_goals - short and long term goals with priorities
      6. time_commitment - available study time and schedule
    """

    __tablename__ = "student_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"),
        unique=True, nullable=False
    )

    # 6 profile dimensions as JSON
    knowledge_foundation: Mapped[dict] = mapped_column(JSON, default=dict)
    cognitive_style: Mapped[str] = mapped_column(String(20), default="unknown")
    common_errors: Mapped[list] = mapped_column(JSON, default=list)
    learning_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    learning_goals: Mapped[list] = mapped_column(JSON, default=list)
    time_commitment: Mapped[str] = mapped_column(String(20), default="moderate")

    # Profile metadata
    profile_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="profile")
