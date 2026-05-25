"""Resource model for 8 types of generated learning resources.

Content is stored as JSON with type-specific schemas:
  R0: Resource design plan (planning metadata)
  R1: Course document (Markdown)
  R2: Mind map (JSON tree structure)
  R3: Exercise set (questions with answers)
  R4: Code case (Markdown + runnable code)
  R5: PPT slides (PPTX file path or Markdown)
  R6: Project materials (spec + starter code + tests + guide)
  R7: Extended reading (Markdown + references)
  R8: Video/animation script (scenes + narration + animation instructions)
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Resource(Base):
    """A generated learning resource, personalized for a student."""

    __tablename__ = "resources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # course_doc | mind_map | exercise | code_case | ppt
    # project | reading | video_script | design_plan

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Type-specific content structure

    knowledge_node_ids: Mapped[list] = mapped_column(JSON, default=list)
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")

    # Personalization tracking
    target_student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="SET NULL")
    )
    generation_context: Mapped[dict] = mapped_column(JSON, default=dict)
    # Snapshot of profile + agent version at generation time, for traceability

    # Review workflow
    review_status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | approved | rejected | needs_revision
    review_notes: Mapped[str | None] = mapped_column(Text)

    # Audit trail
    iflytek_apis_used: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    target_student: Mapped["Student | None"] = relationship(
        back_populates="resources"
    )
    submissions: Mapped[list["ExerciseSubmission"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )
