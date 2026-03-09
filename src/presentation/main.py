from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.infrastructure.database.session import Base, engine
from src.infrastructure.external.gemini_embedding import GeminiEmbeddingService
from src.infrastructure.vector_store.qdrant_store import QdrantVectorStore
from src.presentation.routers import (
    chat, comments, files, health, insights, members, projects, search, tasks, users,
)
from src.presentation.routers import summary
from src.presentation.routers import brain, documents, knowledge_graph

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables + Qdrant collection
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    embedding_svc = GeminiEmbeddingService()
    vector_store = QdrantVectorStore(embedding_svc)
    await vector_store.ensure_collection()
    logger.info("Qdrant collection ensured")

    yield

    await engine.dispose()


app = FastAPI(
    title="PraxisForge",
    description="AI-driven Project Management & Growth Platform",
    version="0.3.0",
    lifespan=lifespan,
)

# ── CORS middleware ──────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(files.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(summary.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(members.router, prefix="/api/v1")
app.include_router(comments.router, prefix="/api/v1")
app.include_router(knowledge_graph.router, prefix="/api/v1")
app.include_router(brain.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(health.router)  # No prefix - /health, /health/ready, /health/live
