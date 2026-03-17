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
    gemini_embedding_model: str = "models/gemini-embedding-001"
    gemini_llm_model: str = "models/gemini-2.5-flash"

    # ── Groq ──────────────────────────────────────────────
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Hugging Face Inference (optional LLM fallback) ─────
    huggingface_api_key: str = ""
    huggingface_model: str = "mistralai/Mistral-7B-Instruct-v0.3"
    huggingface_api_base: str = "https://api-inference.huggingface.co/models"
    huggingface_timeout_seconds: int = 45

    # ── LLM routing / fallback strategy ────────────────────
    llm_chat_primary_provider: str = "groq"
    llm_chat_fallback_provider: str = "gemini"
    llm_search_primary_provider: str = "groq"
    llm_search_fallback_provider: str = "gemini"
    llm_summary_primary_provider: str = "groq"
    llm_summary_fallback_provider: str = "gemini"
    llm_extraction_primary_provider: str = "groq"
    llm_extraction_fallback_provider: str = "huggingface"
    llm_retry_attempts: int = 2
    llm_retry_backoff_seconds: float = 0.7
    summary_cache_ttl_seconds: int = 120
    search_cache_ttl_seconds: int = 180
    health_llm_probe: bool = False

    # ── Tavily ────────────────────────────────────────────
    tavily_api_key: str = ""

    # ── JWT ───────────────────────────────────────────────
    jwt_secret: str = "changeme"
    jwt_algorithm: str = "HS256"
    access_token_expire_hours: int = 24

    # ── Reverse Proxy Path Prefix ─────────────────────────
    root_path: str = ""

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
