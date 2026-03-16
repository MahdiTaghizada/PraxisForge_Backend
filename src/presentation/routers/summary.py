"""Summary router: generate comprehensive project summaries."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dtos.schemas import FactResponseDTO, ProjectSummaryResponseDTO
from src.application.interfaces.llm import LLMService
from src.application.use_cases.project_summary import ProjectSummaryUseCase
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.repositories.task_repo import TaskRepository
from src.infrastructure.cache.in_memory_ttl_cache import InMemoryTTLCache
from src.infrastructure.config import settings
from src.presentation.dependencies.deps import (
    get_chat_repo,
    get_summary_cache,
    get_current_user_id,
    get_fact_repo,
    get_project_repo,
    get_summary_llm_service,
    get_task_repo,
)

router = APIRouter(prefix="/projects/{project_id}/summary", tags=["Summary"])


@router.get("/", response_model=ProjectSummaryResponseDTO)
async def generate_project_summary(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    fact_repo: FactRepository = Depends(get_fact_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    llm: LLMService = Depends(get_summary_llm_service),
    cache: InMemoryTTLCache[dict] = Depends(get_summary_cache),
) -> ProjectSummaryResponseDTO:
    """Generate a full project summary with architecture, facts, and insights."""
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    use_case = ProjectSummaryUseCase(
        llm=llm,
        fact_repo=fact_repo,
        task_repo=task_repo,
        chat_repo=chat_repo,
        cache=cache,
        cache_ttl_seconds=settings.summary_cache_ttl_seconds,
    )
    result = await use_case.execute(project)

    return ProjectSummaryResponseDTO(
        project_name=result["project_name"],
        project_mode=result["project_mode"],
        summary=result["summary"],
        architecture_overview=result["architecture_overview"],
        key_facts=[
            FactResponseDTO(
                id=f.id,
                project_id=f.project_id,
                category=f.category,
                content=f.content,
                source_message_id=f.source_message_id,
                created_at=f.created_at,
            )
            for f in result["key_facts"]
        ],
        recommended_db_structure=result["recommended_db_structure"],
        key_insights=result["key_insights"],
        task_overview=result["task_overview"],
    )
