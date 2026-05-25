"""Student and authentication models."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Student(Base):
    """Student account and authentication."""

    __tablename__ = "students"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(100), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    profile: Mapped["StudentProfile"] = relationship(
        back_populates="student", uselist=False, cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    learning_paths: Mapped[list["LearningPath"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    resources: Mapped[list["Resource"]] = relationship(
        back_populates="target_student", cascade="all, delete-orphan"
    )
    activities: Mapped[list["LearningActivity"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
    exercise_submissions: Mapped[list["ExerciseSubmission"]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
