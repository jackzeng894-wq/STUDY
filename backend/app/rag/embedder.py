"""SentenceTransformer embedder for RAG semantic search.

Uses the multilingual MiniLM model for Chinese+English text embedding.
The model is loaded once at module level (singleton pattern).
"""

from sentence_transformers import SentenceTransformer

from app.config import settings

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    """Lazy-load the embedding model (downloads ~1.2GB on first call)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def embed_one(text: str) -> list[float]:
    """Embed a single text string into a vector of VECTOR_DIMENSION floats."""
    model = _get_model()
    return model.encode(text, normalize_embeddings=True).tolist()


def embed_many(texts: list[str]) -> list[list[float]]:
    """Embed multiple text strings in batch."""
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()
