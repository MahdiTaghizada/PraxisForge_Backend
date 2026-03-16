"""Health check router with detailed service status."""
from __future__ import annotations

from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from fastapi import APIRouter, status
import google.generativeai as genai
from groq import Groq
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sqlalchemy import text

from src.infrastructure.config import settings
from src.infrastructure.database.session import async_session_factory

router = APIRouter(prefix="/health", tags=["Health"])


class ServiceHealth(BaseModel):
    """Health status for a single service."""

    status: str  # "healthy", "unhealthy", "degraded"
    message: str | None = None
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    """Overall health response."""

    status: str  # "healthy", "unhealthy", "degraded"
    version: str
    services: dict[str, ServiceHealth]


async def check_postgres() -> ServiceHealth:
    """Check PostgreSQL connectivity."""
    import time

    start = time.perf_counter()
    try:
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        latency = (time.perf_counter() - start) * 1000
        return ServiceHealth(status="healthy", message="Connected", latency_ms=round(latency, 2))
    except Exception as e:
        return ServiceHealth(status="unhealthy", message=str(e)[:200])


def check_qdrant() -> ServiceHealth:
    """Check Qdrant connectivity and collection status."""
    import time

    qdrant_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"
    collection_name = settings.qdrant_collection

    start = time.perf_counter()
    try:
        client = QdrantClient(url=qdrant_url, timeout=5.0)
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        latency = (time.perf_counter() - start) * 1000

        if collection_name in collection_names:
            info = client.get_collection(collection_name)
            return ServiceHealth(
                status="healthy",
                message=f"Collection '{collection_name}' has {info.points_count} points",
                latency_ms=round(latency, 2),
            )
        else:
            return ServiceHealth(
                status="degraded",
                message=f"Collection '{collection_name}' not found. Run init_qdrant.py",
                latency_ms=round(latency, 2),
            )
    except Exception as e:
        return ServiceHealth(status="unhealthy", message=str(e)[:200])


def _provider_roles(provider_name: str) -> list[str]:
    roles: list[str] = []
    mapping = {
        "chat-primary": settings.llm_chat_primary_provider,
        "chat-fallback": settings.llm_chat_fallback_provider,
        "search-primary": settings.llm_search_primary_provider,
        "search-fallback": settings.llm_search_fallback_provider,
        "summary-primary": settings.llm_summary_primary_provider,
        "summary-fallback": settings.llm_summary_fallback_provider,
        "extraction-primary": settings.llm_extraction_primary_provider,
        "extraction-fallback": settings.llm_extraction_fallback_provider,
    }
    for role, provider in mapping.items():
        if provider == provider_name:
            roles.append(role)
    return roles


def _check_gemini() -> ServiceHealth:
    roles = _provider_roles("gemini")
    if not settings.gemini_api_key:
        return ServiceHealth(status="degraded", message=f"Not configured; roles={roles}")
    if not settings.health_llm_probe:
        return ServiceHealth(status="healthy", message=f"Configured; roles={roles}")
    try:
        genai.configure(api_key=settings.gemini_api_key)
        _ = list(genai.list_models(page_size=1))
        return ServiceHealth(status="healthy", message=f"Configured + probe OK; roles={roles}")
    except Exception as e:
        msg = str(e)
        if "429" in msg or "quota" in msg.lower():
            return ServiceHealth(status="degraded", message=f"Rate limited; roles={roles}")
        return ServiceHealth(status="unhealthy", message=msg[:200])


def _check_groq() -> ServiceHealth:
    roles = _provider_roles("groq")
    if not settings.groq_api_key:
        return ServiceHealth(status="degraded", message=f"Not configured; roles={roles}")
    if not settings.health_llm_probe:
        return ServiceHealth(status="healthy", message=f"Configured; roles={roles}")
    try:
        client = Groq(api_key=settings.groq_api_key)
        _ = client.models.list().data
        return ServiceHealth(status="healthy", message=f"Configured + probe OK; roles={roles}")
    except Exception as e:
        msg = str(e)
        if "429" in msg or "rate" in msg.lower():
            return ServiceHealth(status="degraded", message=f"Rate limited; roles={roles}")
        return ServiceHealth(status="unhealthy", message=msg[:200])


def _check_huggingface() -> ServiceHealth:
    roles = _provider_roles("huggingface")
    if not settings.huggingface_api_key:
        return ServiceHealth(status="degraded", message=f"Not configured; roles={roles}")
    if not settings.health_llm_probe:
        return ServiceHealth(status="healthy", message=f"Configured; roles={roles}")
    try:
        url = f"{settings.huggingface_api_base.rstrip('/')}/{settings.huggingface_model}"
        req = Request(
            url=url,
            headers={"Authorization": f"Bearer {settings.huggingface_api_key}"},
            method="GET",
        )
        with urlopen(req, timeout=settings.huggingface_timeout_seconds):
            pass
        return ServiceHealth(status="healthy", message=f"Configured + probe OK; roles={roles}")
    except URLError as e:
        return ServiceHealth(status="unhealthy", message=str(e.reason)[:200])
    except Exception as e:
        msg = str(e)
        if "429" in msg or "rate" in msg.lower():
            return ServiceHealth(status="degraded", message=f"Rate limited; roles={roles}")
        return ServiceHealth(status="unhealthy", message=msg[:200])


@router.get(
    "",
    response_model=HealthResponse,
    responses={
        200: {"description": "All services healthy"},
        503: {"description": "One or more services unhealthy"},
    },
)
async def detailed_health_check() -> HealthResponse:
    """
    Comprehensive health check for all backend services.

    Returns:
        - **status**: Overall system status (healthy/degraded/unhealthy)
        - **version**: API version
        - **services**: Individual service health status including latency
    """
    postgres_health = await check_postgres()
    qdrant_health = check_qdrant()
    gemini_health = _check_gemini()
    groq_health = _check_groq()
    huggingface_health = _check_huggingface()

    services = {
        "postgres": postgres_health,
        "qdrant": qdrant_health,
        "llm_gemini": gemini_health,
        "llm_groq": groq_health,
        "llm_huggingface": huggingface_health,
    }

    # Determine overall status
    statuses = [s.status for s in services.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return HealthResponse(
        status=overall,
        version="0.2.0",
        services=services,
    )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_probe() -> dict[str, str]:
    """
    Kubernetes readiness probe.

    Returns 200 if the application is ready to accept traffic.
    """
    postgres = await check_postgres()
    if postgres.status == "unhealthy":
        return {"status": "not_ready", "reason": "database unavailable"}
    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_probe() -> dict[str, str]:
    """
    Kubernetes liveness probe.

    Returns 200 if the application process is alive.
    """
    return {"status": "alive"}
