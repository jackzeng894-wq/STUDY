"""Application configuration loaded from environment variables.

Uses pydantic-settings for type-safe configuration management.
Sensitive values like API keys are loaded from .env file or environment.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable loading."""

    # Application
    APP_NAME: str = "PersonalizedLearningAgent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database (PostgreSQL + pgvector or SQLite + ChromaDB)
    DATABASE_URL: str = (
        "sqlite+aiosqlite:///./learning_agent.db"
    )
    DATABASE_URL_SYNC: str = (
        "sqlite:///./learning_agent.db"
    )
    # For PostgreSQL: set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/learning_agent
    #                 DATABASE_URL_SYNC=postgresql://postgres:postgres@localhost:5432/learning_agent

    # ChromaDB (vector store, used when not using pgvector)
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # iFlytek Spark LLM
    SPARK_API_KEY: str = ""
    SPARK_API_BASE: str = "https://spark-api-open.xf-yun.com/v1"
    SPARK_MODEL: str = "4.0Ultra"

    # iFlytek TTS
    IFlyTEK_TTS_APP_ID: str = ""
    IFlyTEK_TTS_API_KEY: str = ""
    IFlyTEK_TTS_API_SECRET: str = ""

    # iFlytek Content Audit
    IFlyTEK_AUDIT_APP_ID: str = ""
    IFlyTEK_AUDIT_API_KEY: str = ""

    # SeeDance Multimodal Generation
    SEEDANCE_API_KEY: str = ""
    SEEDANCE_API_BASE: str = ""

    # JWT Auth
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # RAG (Embedding + ChromaDB vector store)
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    VECTOR_DIMENSION: int = 384
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    CHROMA_COLLECTION: str = "knowledge_base"

    # Code Sandbox
    DENO_PATH: str = "deno"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
