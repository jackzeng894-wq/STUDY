"""One-shot script to index the JavaScript knowledge base into SQLite + ChromaDB.

Run via: python -m app.rag.indexer

Parses chapters/*.md + metadata.json, splits into per-topic sections,
generates embeddings (SentenceTransformer), stores nodes+relations in
SQLite and vector embeddings in ChromaDB.
"""

import asyncio
import json
import os
import re
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.rag.embedder import embed_one
from app.rag.vectorstore import add_vector, batch_add_vectors, clear_all

KB_DIR = Path(__file__).resolve().parent.parent.parent / "knowledge_base"


def load_metadata() -> dict:
    """Load metadata.json containing 10 chapters and 85 node definitions."""
    with open(KB_DIR / "metadata.json", "r", encoding="utf-8") as f:
        return json.load(f)


def read_chapter(filepath: str) -> str:
    """Read a chapter Markdown file."""
    with open(KB_DIR / filepath, "r", encoding="utf-8") as f:
        return f.read()


def split_into_sections(markdown: str) -> list[dict]:
    """Split a chapter Markdown file into per-topic sections.

    Returns list of {title, content} dicts, one per ### heading.
    """
    sections = []
    parts = re.split(r"\n(?=### )", markdown)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        match = re.match(r"### (.+)", part)
        if match:
            title = match.group(1).strip()
            sections.append({"title": title, "content": part})
    return sections


def build_topic_code_lookup(metadata: dict) -> dict[str, dict]:
    """Build a lookup from topic_code to node metadata from metadata.json."""
    lookup = {}
    for ch in metadata["chapters"]:
        for node in ch["nodes"]:
            lookup[node["code"]] = {
                "code": node["code"],
                "title": node["title"],
                "difficulty": node["difficulty"],
                "chapter_id": ch["id"],
                "chapter_title": ch["title"],
            }
    return lookup


def match_section_to_topic(
    section_title: str, topic_lookup: dict[str, dict]
) -> dict | None:
    """Match a section title to a topic code by finding the best title match."""
    for code, info in topic_lookup.items():
        if info["title"] == section_title:
            return info
    for code, info in topic_lookup.items():
        if info["title"] in section_title or section_title in info["title"]:
            return info
    return None


async def clear_existing(session: AsyncSession) -> None:
    """Remove existing knowledge data for clean re-indexing."""
    await session.execute(text("DELETE FROM knowledge_relations"))
    await session.execute(text("DELETE FROM knowledge_nodes"))
    clear_all()  # ChromaDB


async def insert_node(
    session: AsyncSession,
    topic_code: str,
    title: str,
    content: str,
    difficulty: str,
    chapter_id: str,
    keywords: list[str],
) -> str:
    """Insert a knowledge node into SQLite and return its ID."""
    node_id = str(uuid.uuid4())
    depth = int(chapter_id[2:]) if chapter_id.startswith("ch") else 0
    await session.execute(
        text("""
            INSERT INTO knowledge_nodes
                (id, topic_code, title, description, difficulty, keywords,
                 content_markdown, depth, sort_order)
            VALUES
                (:id, :code, :title, :desc, :diff, :kw,
                 :content, :depth, :sort)
        """),
        {
            "id": node_id,
            "code": topic_code,
            "title": title,
            "desc": content[:200] if content else None,
            "diff": difficulty,
            "kw": json.dumps(keywords),
            "content": content,
            "depth": depth,
            "sort": 0,
        },
    )
    return node_id


async def insert_relation(
    session: AsyncSession,
    source_code: str,
    target_code: str,
    relation_type: str,
    node_id_map: dict[str, str],
) -> None:
    """Insert a knowledge relation edge."""
    source_id = node_id_map.get(source_code)
    target_id = node_id_map.get(target_code)
    if not source_id or not target_id:
        return

    await session.execute(
        text("""
            INSERT INTO knowledge_relations
                (id, source_node_id, target_node_id, relation_type, weight)
            VALUES (:id, :source, :target, :type, :weight)
        """),
        {
            "id": str(uuid.uuid4()),
            "source": source_id,
            "target": target_id,
            "type": relation_type,
            "weight": 1.0,
        },
    )


async def index_all() -> None:
    """Main entry point: index the entire knowledge base."""
    metadata = load_metadata()
    topic_lookup = build_topic_code_lookup(metadata)
    chapters_dir = KB_DIR / "chapters"

    print(f"Indexing {len(metadata['chapters'])} chapters "
          f"({metadata['total_nodes']} knowledge nodes)...")
    print(f"ChromaDB: {settings.CHROMA_PERSIST_DIR}")

    async with async_session() as session:
        await clear_existing(session)

        node_id_map: dict[str, str] = {}
        indexed = 0
        # For batch ChromaDB inserts
        chroma_items: list[tuple[str, list[float], dict, str]] = []

        for ch in metadata["chapters"]:
            filename = f"{ch['id']}_*.md"
            matches = list(chapters_dir.glob(filename))
            if not matches:
                print(f"  [WARN] No file found for {ch['id']}")
                continue

            markdown = read_chapter(str(matches[0].relative_to(KB_DIR)))
            sections = split_into_sections(markdown)

            for section in sections:
                topic = match_section_to_topic(section["title"], topic_lookup)
                if not topic:
                    continue

                embedding = embed_one(section["content"])
                node_id = await insert_node(
                    session=session,
                    topic_code=topic["code"],
                    title=topic["title"],
                    content=section["content"],
                    difficulty=topic["difficulty"],
                    chapter_id=ch["id"],
                    keywords=[topic["title"], topic["code"]],
                )
                node_id_map[topic["code"]] = node_id

                chroma_items.append((
                    node_id,
                    embedding,
                    {"topic_code": topic["code"], "title": topic["title"], "difficulty": topic["difficulty"]},
                    section["content"],
                ))

                indexed += 1
                if indexed % 10 == 0:
                    print(f"  [{indexed}/{metadata['total_nodes']}] {topic['code']}: {topic['title']}")

            # Mark section topics as processed
            for section in sections:
                topic = match_section_to_topic(section["title"], topic_lookup)
                if topic:
                    topic_lookup.pop(topic["code"], None)

        # Batch upload to ChromaDB
        if chroma_items:
            batch_add_vectors(chroma_items)
            print(f"  Embedded {len(chroma_items)} vectors into ChromaDB")

        # Insert cross-chapter dependency relations
        deps = metadata.get("cross_chapter_dependencies", [])
        for dep in deps:
            await insert_relation(
                session, dep["source"], dep["target"], dep["relation"], node_id_map
            )
        print(f"  Inserted {len(deps)} cross-chapter relations")

        await session.commit()
        print(f"Done. Indexed {indexed} nodes into SQLite + ChromaDB.")


def main():
    asyncio.run(index_all())


if __name__ == "__main__":
    main()
