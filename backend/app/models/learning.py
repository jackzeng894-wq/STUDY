"""Learning models: paths, activities, and exercise submissions."""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LearningPath(Base):
    """Personalized learning path: an ordered sequence of knowledge nodes
    with recommended resources for each step.
    """

    __tablename__ = "learning_paths"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )

    title: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)

    # Ordered path nodes
    # [{"knowledge_node_id": "...", "order": 1, "status": "active",
    #   "recommended_resources": [...], "estimated_minutes": 45}, ...]
    path_nodes: Mapped[list] = mapped_column(JSON, nullable=False)

    total_nodes: Mapped[int] = mapped_column(Integer, default=0)
    completed_nodes: Mapped[int] = mapped_column(Integer, default=0)
    estimated_total_hours: Mapped[float | None] = mapped_column(Float)

    status: Mapped[str] = mapped_column(String(20), default="active")
    # active | completed | paused | superseded
    version: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="learning_paths")


class LearningActivity(Base):
    """Tracks every learning behavior for evaluation and path adjustment."""

    __tablename__ = "learning_activities"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )

    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # page_view | resource_open | exercise_submit | code_run
    # chat_message | path_progress | profile_update

    target_id: Mapped[str | None] = mapped_column(String(36))
    # References resource_id or path_node_id

    activity_data: Mapped[dict] = mapped_column(JSON, default=dict)
    # Type-specific data: answer results, dwell time, code output, etc.

    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="activities")


class ExerciseSubmission(Base):
    """Student's answer to a generated exercise resource."""

    __tablename__ = "exercise_submissions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False
    )
    resource_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resources.id", ondelete="CASCADE"),
        nullable=False
    )

    answers: Mapped[list] = mapped_column(JSON, nullable=False)
    # [{"question_id": "...", "answer": "...", "is_correct": true,
    #   "time_spent_seconds": 30}, ...]

    total_score: Mapped[float | None] = mapped_column(Float)
    max_score: Mapped[float | None] = mapped_column(Float)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        back_populates="exercise_submissions"
    )
    resource: Mapped["Resource"] = relationship(back_populates="submissions")
