"""Pydantic schemas for knowledge graph and knowledge base queries."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeNodeResponse(BaseModel):
    """Public knowledge node representation."""

    id: str
    topic_code: str
    title: str
    description: Optional[str] = None
    difficulty: str
    depth: int
    keywords: list[str] = Field(default_factory=list)
    parent_id: Optional[str] = None
    prerequisites: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class KnowledgeNodeDetail(KnowledgeNodeResponse):
    """Knowledge node with full Markdown content."""

    content_markdown: Optional[str] = None


class KnowledgeRelationResponse(BaseModel):
    """Public knowledge relation (edge) representation."""

    id: str
    source_node_id: str
    target_node_id: str
    relation_type: str
    weight: float
    description: Optional[str] = None

    class Config:
        from_attributes = True


class KnowledgeTreeNode(BaseModel):
    """A node in the knowledge tree (hierarchical view)."""

    id: str
    topic_code: str
    title: str
    difficulty: str
    children: list["KnowledgeTreeNode"] = Field(default_factory=list)


class KnowledgeTreeResponse(BaseModel):
    """Full knowledge tree with chapter-level grouping."""

    chapters: list[dict] = Field(default_factory=list)
    total_nodes: int = 0


class KnowledgeGraphResponse(BaseModel):
    """Knowledge graph data for 3D visualization."""

    nodes: list[dict] = Field(default_factory=list)
    edges: list[dict] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)


class KnowledgeSearchRequest(BaseModel):
    """Search request for knowledge base."""

    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)

    class Config:
        json_schema_extra = {
            "example": {"query": "JavaScript闭包和作用域", "top_k": 5}
        }


class KnowledgeSearchResult(BaseModel):
    """Single search result."""

    id: str
    topic_code: str
    title: str
    content_snippet: str
    similarity: float


class KnowledgeSearchResponse(BaseModel):
    """Semantic search results."""

    query: str
    results: list[KnowledgeSearchResult]
    total: int
