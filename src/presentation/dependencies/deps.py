from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.embedding import EmbeddingService
from src.application.interfaces.llm import LLMService
from src.application.interfaces.search_api import SearchAPIService
from src.application.interfaces.vector_store import VectorStoreService
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.repositories.comment_repo import CommentRepository
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.file_repo import FileRepository
from src.domain.repositories.knowledge_graph_repo import (
    KnowledgeEntityRepository,
    KnowledgeRelationshipRepository,
)
from src.domain.repositories.member_repo import MemberRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.repositories.task_repo import TaskRepository
from src.infrastructure.config import settings
from src.infrastructure.database.repositories import (
    PostgresChatRepository,
    PostgresCommentRepository,
    PostgresDocumentAnalysisRepository,
    PostgresFactRepository,
    PostgresFileRepository,
    PostgresKnowledgeEntityRepository,
    PostgresKnowledgeRelationshipRepository,
    PostgresMemberRepository,
    PostgresProjectRepository,
    PostgresTaskRepository,
)
from src.infrastructure.database.session import get_db_session
from src.infrastructure.external.gemini_embedding import GeminiEmbeddingService
from src.infrastructure.external.gemini_llm import GeminiLLMService
from src.infrastructure.external.gemini_vision import GeminiVisionService
from src.infrastructure.external.groq_llm import GroqLLMService
from src.infrastructure.external.tavily_search import TavilySearchService
from src.infrastructure.external.text_extraction import TextExtractionService
from src.infrastructure.vector_store.qdrant_store import QdrantVectorStore

_bearer_scheme = HTTPBearer()


# ── Authentication ────────────────────────────────────────


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> str:
    """Extract owner_id from a JWT Bearer token."""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing 'sub' claim",
            )
        return user_id
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )


# ── Database Repositories ────────────────────────────────


async def get_project_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ProjectRepository:
    return PostgresProjectRepository(session)


async def get_file_repo(
    session: AsyncSession = Depends(get_db_session),
) -> FileRepository:
    return PostgresFileRepository(session)


async def get_task_repo(
    session: AsyncSession = Depends(get_db_session),
) -> TaskRepository:
    return PostgresTaskRepository(session)


async def get_chat_repo(
    session: AsyncSession = Depends(get_db_session),
) -> ChatRepository:
    return PostgresChatRepository(session)


async def get_fact_repo(
    session: AsyncSession = Depends(get_db_session),
) -> FactRepository:
    return PostgresFactRepository(session)


async def get_member_repo(
    session: AsyncSession = Depends(get_db_session),
) -> MemberRepository:
    return PostgresMemberRepository(session)


async def get_comment_repo(
    session: AsyncSession = Depends(get_db_session),
) -> CommentRepository:
    return PostgresCommentRepository(session)


# ── External Services ────────────────────────────────────


def get_embedding_service() -> EmbeddingService:
    return GeminiEmbeddingService()


def get_vector_store(
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> VectorStoreService:
    return QdrantVectorStore(embedding_service)


def get_llm_service() -> LLMService:
    """Primary LLM used for chat (Gemini)."""
    return GeminiLLMService()


def get_extraction_llm() -> LLMService:
    """Fast LLM used for background extraction tasks (Groq)."""
    return GroqLLMService()


def get_search_api() -> SearchAPIService:
    return TavilySearchService()


# ── New Feature Dependencies ──────────────────────────────


async def get_entity_repo(
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeEntityRepository:
    return PostgresKnowledgeEntityRepository(session)


async def get_relationship_repo(
    session: AsyncSession = Depends(get_db_session),
) -> KnowledgeRelationshipRepository:
    return PostgresKnowledgeRelationshipRepository(session)


async def get_document_analysis_repo(
    session: AsyncSession = Depends(get_db_session),
) -> DocumentAnalysisRepository:
    return PostgresDocumentAnalysisRepository(session)


def get_vision_service() -> GeminiVisionService:
    return GeminiVisionService()


def get_text_extractor() -> TextExtractionService:
    return TextExtractionService()
