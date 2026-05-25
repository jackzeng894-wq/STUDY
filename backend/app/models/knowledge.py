"""Knowledge graph models: nodes (topics) and relations (edges).

These form the directed graph used by NetworkX graph algorithms
for learning path planning (topological sort, shortest path, PageRank).

Vector embeddings are stored in ChromaDB, not in SQLite.
"""

import uuid

from sqlalchemy import String, Integer, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class KnowledgeNode(Base):
    """A single JavaScript knowledge point in the learning graph.

    Forms nodes in the directed graph. Each node has:
    - Prerequisite links to other nodes (forming a DAG)
    - Full Markdown content for retrieval-augmented generation
    - Vector embedding stored in ChromaDB (not in this table)
    """

    __tablename__ = "knowledge_nodes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    topic_code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )
    # e.g. "js_basics_variables", "js_async_promise"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # Tree hierarchy
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id")
    )
    depth: Mapped[int] = mapped_column(Integer, default=0)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # Node attributes
    difficulty: Mapped[str] = mapped_column(String(20), default="beginner")
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    # Full content for RAG
    content_markdown: Mapped[str | None] = mapped_column(Text)


class KnowledgeRelation(Base):
    """An edge between two knowledge nodes in the learning graph.

    Represents directed relationships:
    - prerequisite: source must be learned before target
    - related: loosely associated topics
    - extends: target is an advanced extension of source
    - contrasts: topics that are often compared/confused
    """

    __tablename__ = "knowledge_relations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False
    )
    target_node_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # prerequisite | related | extends | contrasts
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[str | None] = mapped_column(Text)
