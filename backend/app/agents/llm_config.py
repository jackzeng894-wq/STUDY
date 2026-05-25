"""Shared LLM configuration for all CrewAI crews.

Provides convenience factories with appropriate temperature settings
for different agent roles (interviewer vs analyzer vs tutor).
"""

from crewai import LLM

from app.iflytek.spark_llm import create_spark_llm

# Temperature presets tuned for agent roles
INTERVIEWER_TEMPERATURE = 0.7
ANALYZER_TEMPERATURE = 0.3
TUTOR_TEMPERATURE = 0.7
GENERATOR_TEMPERATURE = 0.6
REVIEWER_TEMPERATURE = 0.3


def get_spark_llm(
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> LLM:
    """Return a CrewAI LLM instance for iFlytek Spark."""
    return create_spark_llm(temperature=temperature, max_tokens=max_tokens)
