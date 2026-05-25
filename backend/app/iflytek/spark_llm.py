"""iFlytek Spark LLM factory via LiteLLM + OpenAI-compatible interface.

Encapsulates the configuration pattern verified in validate_spark_crewai.py.
All CrewAI LLM instances are created through this module.
"""

from crewai import LLM

from app.config import settings


def create_spark_llm(
    temperature: float = 0.7,
    max_tokens: int = 4096,
    streaming: bool = True,
    callbacks: list | None = None,
) -> LLM:
    """Create a CrewAI LLM instance configured for iFlytek Spark (OpenAI-compatible).

    Args:
        temperature: 0.0-1.0, lower for analytical tasks, higher for creative.
        max_tokens: Maximum output tokens.
        streaming: Whether to enable token-level streaming.
        callbacks: Optional LiteLLM callback handlers (e.g. for streaming tokens).

    Returns:
        CrewAI LLM instance ready for use with Agent(..., llm=spark_llm).
    """
    llm = LLM(
        model=f"openai/{settings.SPARK_MODEL}",
        base_url=settings.SPARK_API_BASE,
        api_key=settings.SPARK_API_KEY,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    # LiteLLM uses callbacks list for streaming hook support
    if callbacks:
        llm.callbacks = callbacks

    return llm


def create_spark_llm_streaming(callbacks: list | None = None) -> LLM:
    """Shortcut for streaming-enabled LLM (default temperature 0.7)."""
    return create_spark_llm(temperature=0.7, streaming=True, callbacks=callbacks)


def create_spark_llm_precise(callbacks: list | None = None) -> LLM:
    """Shortcut for low-temperature LLM for analysis tasks (temperature 0.3)."""
    return create_spark_llm(temperature=0.3, streaming=True, callbacks=callbacks)
