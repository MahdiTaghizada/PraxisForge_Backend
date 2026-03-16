"""Search router: AI-powered project uniqueness analysis with SWOT."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dtos.schemas import SearchRequestDTO, SearchResponseDTO
from src.application.interfaces.llm import LLMService
from src.application.interfaces.search_api import SearchAPIService
from src.application.use_cases.project_search import ProjectSearchUseCase
from src.domain.repositories.project_repo import ProjectRepository
from src.infrastructure.cache.in_memory_ttl_cache import InMemoryTTLCache
from src.infrastructure.config import settings
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_project_repo,
    get_search_cache,
    get_search_llm_service,
    get_search_api,
)

router = APIRouter(prefix="/projects/{project_id}/search", tags=["Search"])


@router.post("/", response_model=SearchResponseDTO)
async def search_project_uniqueness(
    project_id: uuid.UUID,
    body: SearchRequestDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    search_api: SearchAPIService = Depends(get_search_api),
    llm: LLMService = Depends(get_search_llm_service),
    cache: InMemoryTTLCache[dict] = Depends(get_search_cache),
) -> SearchResponseDTO:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    use_case = ProjectSearchUseCase(
        search_api=search_api,
        llm=llm,
        cache=cache,
        cache_ttl_seconds=settings.search_cache_ttl_seconds,
    )
    result = await use_case.execute(
        project_name=project.name,
        project_description=project.description,
        custom_query=body.query,
    )

    return SearchResponseDTO(**result)
