from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── Database ──────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://praxisforge:changeme@localhost:5432/praxisforge"

    # ── Qdrant ────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "praxisforge_docs"

    # ── Gemini ────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_embedding_model: str = "models/text-embedding-004"
    gemini_llm_model: str = "models/gemini-1.5-flash"

    # ── Groq ──────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"

    # ── Tavily ────────────────────────────────────────────
    tavily_api_key: str = ""

    # ── JWT ───────────────────────────────────────────────
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"

    # ── File Storage ──────────────────────────────────────
    upload_dir: str = "./uploads"

    # ── MinIO (optional object storage) ───────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "praxisforge"
    minio_secure: bool = False

    # ── Redis (optional caching) ──────────────────────────
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
