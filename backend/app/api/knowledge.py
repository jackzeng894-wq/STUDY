"""Knowledge graph and knowledge base API endpoints.

GET  /knowledge/tree   - Hierarchical knowledge tree (chapter → topic)
GET  /knowledge/graph  - Full graph data for 3D visualization (nodes + edges)
GET  /knowledge/search - Semantic search (RAG)
GET  /knowledge/nodes/{id} - Single knowledge node detail
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_student
from app.database import get_db
from app.models.knowledge import KnowledgeNode, KnowledgeRelation
from app.models.student import Student
from app.rag.embedder import embed_one
from app.rag.vectorstore import search as vector_search
from app.schemas.knowledge import (
    KnowledgeGraphResponse,
    KnowledgeNodeDetail,
    KnowledgeNodeResponse,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    KnowledgeSearchResult,
    KnowledgeTreeResponse,
)
from app.services.graph_service import GraphService

router = APIRouter(tags=["Knowledge"])

graph_service: GraphService | None = None


def init_knowledge_api(gs: GraphService):
    """Initialize module-level service references."""
    global graph_service
    graph_service = gs


@router.get("/tree", response_model=KnowledgeTreeResponse)
async def get_knowledge_tree(
    db: AsyncSession = Depends(get_db),
):
    """Get the knowledge base organized as a hierarchical tree.

    Returns chapters as top-level groups with knowledge nodes as children,
    organized by difficulty within each chapter.
    """
    result = await db.execute(
        select(KnowledgeNode).order_by(
            KnowledgeNode.depth, KnowledgeNode.sort_order,
        )
    )
    nodes = result.scalars().all()

    # Group by depth (chapter level)
    chapters_map: dict[int, dict] = {}
    for node in nodes:
        depth = node.depth
        if depth not in chapters_map:
            chapters_map[depth] = {
                "chapter": depth,
                "title": f"第{depth}章",
                "beginner_nodes": [],
                "intermediate_nodes": [],
                "advanced_nodes": [],
            }

        node_data = {
            "id": str(node.id),
            "topic_code": node.topic_code,
            "title": node.title,
            "difficulty": node.difficulty,
            "keywords": node.keywords or [],
        }

        diff_key = f"{node.difficulty}_nodes"
        if diff_key in chapters_map[depth]:
            chapters_map[depth][diff_key].append(node_data)

    chapters = sorted(chapters_map.values(), key=lambda c: c["chapter"])

    return KnowledgeTreeResponse(
        chapters=chapters,
        total_nodes=len(nodes),
    )


@router.get("/graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    db: AsyncSession = Depends(get_db),
):
    """Get full knowledge graph data for 3D visualization.

    Returns nodes (with PageRank values, difficulty color coding) and
    edges (with relation types and weights) plus graph statistics.
    """
    # Load all nodes
    result = await db.execute(select(KnowledgeNode))
    nodes = result.scalars().all()

    # Load all edges
    result = await db.execute(select(KnowledgeRelation))
    relations = result.scalars().all()

    # Build node list for frontend
    graph_nodes = []
    for node in nodes:
        graph_nodes.append({
            "id": str(node.id),
            "topicCode": node.topic_code,
            "title": node.title,
            "difficulty": node.difficulty,
            "depth": node.depth,
            "keywords": node.keywords or [],
            # Color coding: red=advanced, orange=intermediate, green=beginner
            "color": _difficulty_color(node.difficulty),
            # Size will be determined by PageRank (computed client-side or via graph_service)
        })

    # Build edge list for frontend
    graph_edges = []
    for rel in relations:
        graph_edges.append({
            "id": str(rel.id),
            "source": str(rel.source_node_id),
            "target": str(rel.target_node_id),
            "relationType": rel.relation_type,
            "weight": rel.weight,
            "label": rel.relation_type,
        })

    # Get graph stats if service is available
    stats = {}
    if graph_service:
        try:
            await graph_service.rebuild_graph(db)
            stats = await graph_service.get_stats(db)
        except Exception:
            stats = {
                "node_count": len(graph_nodes),
                "edge_count": len(graph_edges),
                "is_dag": True,
            }
    else:
        stats = {
            "node_count": len(graph_nodes),
            "edge_count": len(graph_edges),
        }

    return KnowledgeGraphResponse(
        nodes=graph_nodes,
        edges=graph_edges,
        stats=stats,
    )


@router.get("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    top_k: int = Query(5, ge=1, le=20, description="Number of results"),
    db: AsyncSession = Depends(get_db),
):
    """Semantic search over the JavaScript knowledge base using vector similarity.

    Returns ranked results with content snippets and similarity scores.
    """
    # Generate embedding for the query
    try:
        query_embedding = embed_one(q)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding generation failed: {str(e)}",
        )

    # Vector search
    results = await vector_search(query_embedding, top_k=top_k)

    search_results = []
    for r in results:
        content = r.get("content_markdown") or ""
        # Truncate content for snippet
        snippet = content[:300] + "..." if len(content) > 300 else content

        search_results.append(KnowledgeSearchResult(
            id=r["id"],
            topic_code=r["topic_code"],
            title=r["title"],
            content_snippet=snippet,
            similarity=round(r.get("similarity", 0.0), 4),
        ))

    return KnowledgeSearchResponse(
        query=q,
        results=search_results,
        total=len(search_results),
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
async def search_knowledge_post(
    data: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Semantic search via POST (alternative to GET /search)."""
    try:
        query_embedding = embed_one(data.query)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding generation failed: {str(e)}",
        )

    results = await vector_search(db, query_embedding, top_k=data.top_k)

    search_results = []
    for r in results:
        content = r.get("content_markdown") or ""
        snippet = content[:300] + "..." if len(content) > 300 else content

        search_results.append(KnowledgeSearchResult(
            id=r["id"],
            topic_code=r["topic_code"],
            title=r["title"],
            content_snippet=snippet,
            similarity=round(r.get("similarity", 0.0), 4),
        ))

    return KnowledgeSearchResponse(
        query=data.query,
        results=search_results,
        total=len(search_results),
    )


@router.get("/nodes/{node_id}", response_model=KnowledgeNodeDetail)
async def get_knowledge_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a single knowledge node, including
    full Markdown content and prerequisite relationships.
    """
    result = await db.execute(
        select(KnowledgeNode).where(KnowledgeNode.id == node_id)
    )
    node = result.scalar_one_or_none()

    if not node:
        raise HTTPException(status_code=404, detail="Knowledge node not found")

    # Get prerequisites
    prereq_result = await db.execute(
        select(KnowledgeRelation).where(
            KnowledgeRelation.target_node_id == node_id,
            KnowledgeRelation.relation_type == "prerequisite",
        )
    )
    prereqs = prereq_result.scalars().all()

    prereq_codes = []
    for pr in prereqs:
        source_result = await db.execute(
            select(KnowledgeNode.topic_code).where(
                KnowledgeNode.id == pr.source_node_id
            )
        )
        tc = source_result.scalar_one_or_none()
        if tc:
            prereq_codes.append(tc)

    return KnowledgeNodeDetail(
        id=node.id,
        topic_code=node.topic_code,
        title=node.title,
        description=node.description,
        difficulty=node.difficulty,
        depth=node.depth,
        keywords=node.keywords or [],
        parent_id=node.parent_id,
        prerequisites=prereq_codes,
        content_markdown=node.content_markdown,
    )


@router.get("/nodes", response_model=list[KnowledgeNodeResponse])
async def list_knowledge_nodes(
    difficulty: str | None = Query(None, description="Filter by difficulty"),
    chapter: int | None = Query(None, description="Filter by chapter depth"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List knowledge nodes with optional filters."""
    conditions = []
    if difficulty:
        conditions.append(KnowledgeNode.difficulty == difficulty)
    if chapter is not None:
        conditions.append(KnowledgeNode.depth == chapter)

    query = (
        select(KnowledgeNode)
        .order_by(KnowledgeNode.depth, KnowledgeNode.sort_order)
        .offset(skip)
        .limit(limit)
    )
    for cond in conditions:
        query = query.where(cond)

    result = await db.execute(query)
    nodes = result.scalars().all()

    return [
        KnowledgeNodeResponse(
            id=n.id,
            topic_code=n.topic_code,
            title=n.title,
            description=n.description,
            difficulty=n.difficulty,
            depth=n.depth,
            keywords=n.keywords or [],
            parent_id=n.parent_id,
            prerequisites=n.prerequisites or [],
        )
        for n in nodes
    ]


def _difficulty_color(difficulty: str) -> str:
    """Map difficulty to a hex color for 3D visualization."""
    colors = {
        "beginner": "#4CAF50",
        "intermediate": "#FF9800",
        "advanced": "#F44336",
    }
    return colors.get(difficulty, "#9E9E9E")
