"""Health check router with detailed service status."""
from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel
from qdrant_client import QdrantClient
from sqlalchemy import text

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

    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "praxisforge")

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

    services = {
        "postgres": postgres_health,
        "qdrant": qdrant_health,
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
