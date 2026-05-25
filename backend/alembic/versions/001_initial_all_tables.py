"""Initial migration: create all tables (SQLite / PostgreSQL compatible).

Revision ID: 001
Revises: None
Create Date: 2025-05-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---- students ----
    op.create_table(
        "students",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(50), unique=True, nullable=False),
        sa.Column("email", sa.String(100), unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # ---- student_profiles ----
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"),
                  unique=True, nullable=False),
        sa.Column("knowledge_foundation", sa.JSON()),
        sa.Column("cognitive_style", sa.String(20), default="unknown"),
        sa.Column("common_errors", sa.JSON()),
        sa.Column("learning_preferences", sa.JSON()),
        sa.Column("learning_goals", sa.JSON()),
        sa.Column("time_commitment", sa.String(20), default="moderate"),
        sa.Column("profile_confidence", sa.Float(), default=0.0),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("updated_at", sa.DateTime()),
    )

    # ---- conversations ----
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("conversation_type", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # ---- messages ----
    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("message_metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
    )

    # ---- knowledge_nodes ----
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("topic_code", sa.String(50), unique=True, nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("knowledge_nodes.id")),
        sa.Column("depth", sa.Integer(), default=0),
        sa.Column("sort_order", sa.Integer(), default=0),
        sa.Column("difficulty", sa.String(20), default="beginner"),
        sa.Column("prerequisites", sa.JSON()),
        sa.Column("keywords", sa.JSON()),
        sa.Column("content_markdown", sa.Text()),
    )

    # ---- knowledge_relations ----
    op.create_table(
        "knowledge_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_node_id", sa.String(36), sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("target_node_id", sa.String(36), sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("relation_type", sa.String(30), nullable=False),
        sa.Column("weight", sa.Float(), default=1.0),
        sa.Column("description", sa.Text()),
    )

    # ---- resources ----
    op.create_table(
        "resources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("knowledge_node_ids", sa.JSON()),
        sa.Column("difficulty", sa.String(20), default="beginner"),
        sa.Column("target_student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="SET NULL")),
        sa.Column("generation_context", sa.JSON()),
        sa.Column("review_status", sa.String(20), default="pending"),
        sa.Column("review_notes", sa.Text()),
        sa.Column("iflytek_apis_used", sa.JSON()),
        sa.Column("created_at", sa.DateTime()),
    )

    # ---- learning_paths ----
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("title", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("path_nodes", sa.JSON(), nullable=False),
        sa.Column("total_nodes", sa.Integer(), default=0),
        sa.Column("completed_nodes", sa.Integer(), default=0),
        sa.Column("estimated_total_hours", sa.Float()),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("version", sa.Integer(), default=1),
        sa.Column("created_at", sa.DateTime()),
        sa.Column("updated_at", sa.DateTime()),
    )

    # ---- learning_activities ----
    op.create_table(
        "learning_activities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("activity_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.String(36)),
        sa.Column("activity_data", sa.JSON()),
        sa.Column("duration_seconds", sa.Integer()),
        sa.Column("created_at", sa.DateTime()),
    )

    # ---- exercise_submissions ----
    op.create_table(
        "exercise_submissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("student_id", sa.String(36), sa.ForeignKey("students.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("resource_id", sa.String(36), sa.ForeignKey("resources.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("total_score", sa.Float()),
        sa.Column("max_score", sa.Float()),
        sa.Column("submitted_at", sa.DateTime()),
    )


def downgrade() -> None:
    op.drop_table("exercise_submissions")
    op.drop_table("learning_activities")
    op.drop_table("learning_paths")
    op.drop_table("resources")
    op.drop_table("knowledge_relations")
    op.drop_table("knowledge_nodes")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("student_profiles")
    op.drop_table("students")
