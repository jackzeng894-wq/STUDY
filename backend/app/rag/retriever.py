"""RAG retriever: orchestrate embedder + ChromaDB vectorstore for semantic search.

Provides convenience methods that return prompt-ready context snippets.
"""

from app.rag.embedder import embed_one
from app.rag.vectorstore import search


async def retrieve(
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Semantic search the knowledge base. Returns ranked results with metadata."""
    embedding = embed_one(query)
    return await search(embedding, top_k=top_k)


async def retrieve_context(
    query: str,
    top_k: int = 5,
    max_tokens: int = 2000,
) -> str:
    """Return concatenated knowledge base snippets ready for LLM prompt injection.

    Truncates output to approximately max_tokens (Chinese characters ~1 token each,
    English ~1.3 tokens per word — we approximate with character count).
    """
    results = await retrieve(query, top_k=top_k)

    if not results:
        return "（未找到相关知识点）"

    snippets = []
    char_count = 0
    char_limit = max_tokens * 2  # rough char-to-token estimate

    for r in results:
        title = r.get("title", "未知")
        content = r.get("content_markdown") or ""
        snippet = f"## {title}\n\n{content}"
        if char_count + len(snippet) > char_limit:
            remaining = char_limit - char_count
            snippets.append(snippet[:remaining] + "...")
            break
        snippets.append(snippet)
        char_count += len(snippet)

    return "\n\n---\n\n".join(snippets)
