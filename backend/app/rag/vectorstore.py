"""ChromaDB vector store wrapper for knowledge node embeddings.

Uses ChromaDB (persistent, local) for semantic search over knowledge nodes.
Zero system dependencies — ChromaDB stores everything in files.
"""

from __future__ import annotations

import uuid
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

_client: chromadb.PersistentClient | None = None
_collection: chromadb.Collection | None = None


def _get_collection() -> chromadb.Collection:
    """Lazy-init the ChromaDB persistent client and collection."""
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(
            path=settings.CHROMA_PERSIST_DIR,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = _client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


def add_vector(
    node_id: str,
    embedding: list[float],
    metadata: dict | None = None,
    content: str = "",
) -> None:
    """Insert or update a vector embedding for a knowledge node."""
    coll = _get_collection()
    meta = metadata or {}
    # ChromaDB requires string IDs; store content as document
    coll.upsert(
        ids=[node_id],
        embeddings=[embedding],
        documents=[content],
        metadatas=[meta],
    )


def batch_add_vectors(
    items: list[tuple[str, list[float], dict, str]],
) -> None:
    """Bulk upsert vectors. Each item: (node_id, embedding, metadata, content)."""
    if not items:
        return
    coll = _get_collection()
    ids = [i[0] for i in items]
    embeddings = [i[1] for i in items]
    metadatas = [i[2] for i in items]
    documents = [i[3] for i in items]
    coll.upsert(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=documents,
    )


async def search(
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Semantic search over knowledge nodes using cosine distance.

    Returns list of dicts with keys: id, topic_code, title, content_markdown, similarity.
    """
    coll = _get_collection()

    if coll.count() == 0:
        return []

    results = coll.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, coll.count()),
        include=["documents", "metadatas", "distances"],
    )

    items = []
    if results["ids"] and results["ids"][0]:
        for i, node_id in enumerate(results["ids"][0]):
            meta = (results["metadatas"][0] or [{}])[i] if results["metadatas"] else {}
            doc = (results["documents"][0] or [""])[i] if results["documents"] else ""
            distance = (results["distances"][0] or [1.0])[i] if results["distances"] else 1.0

            items.append({
                "id": node_id,
                "topic_code": meta.get("topic_code", ""),
                "title": meta.get("title", ""),
                "content_markdown": doc,
                "similarity": round(1.0 - distance, 4),  # cosine distance → similarity
            })

    return items


def clear_all() -> None:
    """Remove all vectors (for re-indexing)."""
    global _client, _collection
    if _client is not None:
        try:
            _client.delete_collection(settings.CHROMA_COLLECTION)
        except Exception:
            pass
    _collection = None
    _client = None


def get_count() -> int:
    """Return number of indexed vectors."""
    coll = _get_collection()
    return coll.count()
