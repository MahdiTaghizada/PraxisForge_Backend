"""Insights router: view and manage extracted structured facts per project."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.application.dtos.schemas import (
    FactPinDTO,
    FactResponseDTO,
    FactUpdateDTO,
    InsightsResponseDTO,
)
from src.application.interfaces.vector_store import VectorChunk, VectorStoreService
from src.domain.entities.models import StructuredFact
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.value_objects.enums import FactCategory
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_fact_repo,
    get_project_repo,
    get_vector_store,
)

router = APIRouter(prefix="/projects/{project_id}/insights", tags=["Insights"])
_PINNED_PREFIX = "[PINNED] "


def _is_pinned_fact(content: str) -> bool:
    return str(content).strip().lower().startswith(_PINNED_PREFIX.strip().lower())


def _to_pinned_content(content: str) -> str:
    cleaned = content.strip()
    if _is_pinned_fact(cleaned):
        return cleaned
    return f"{_PINNED_PREFIX}{cleaned}"


def _fact_to_dto(f) -> FactResponseDTO:
    return FactResponseDTO(
        id=f.id,
        project_id=f.project_id,
        category=f.category,
        content=f.content,
        source_message_id=f.source_message_id,
        created_at=f.created_at,
    )


@router.get("/", response_model=InsightsResponseDTO)
async def get_project_insights(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    fact_repo: FactRepository = Depends(get_fact_repo),
) -> InsightsResponseDTO:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    tech = await fact_repo.list_by_project(project_id, FactCategory.TECHNICAL_DECISION)
    players = await fact_repo.list_by_project(project_id, FactCategory.KEY_PLAYER)
    milestones = await fact_repo.list_by_project(project_id, FactCategory.MILESTONE)
    deadlines = await fact_repo.list_by_project(project_id, FactCategory.DEADLINE)

    return InsightsResponseDTO(
        technical_decisions=[_fact_to_dto(f) for f in tech],
        key_players=[_fact_to_dto(f) for f in players],
        milestones=[_fact_to_dto(f) for f in milestones],
        deadlines=[_fact_to_dto(f) for f in deadlines],
    )


@router.get("/all", response_model=list[FactResponseDTO])
async def list_all_facts(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    fact_repo: FactRepository = Depends(get_fact_repo),
) -> list[FactResponseDTO]:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    facts = await fact_repo.list_by_project(project_id)
    return [_fact_to_dto(f) for f in facts]


@router.post("/pin", response_model=FactResponseDTO, status_code=status.HTTP_201_CREATED)
async def pin_fact(
    project_id: uuid.UUID,
    body: FactPinDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    fact_repo: FactRepository = Depends(get_fact_repo),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> FactResponseDTO:
    """Persist a critical decision as long-term memory for this project."""
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    pinned_content = _to_pinned_content(body.content)
    existing_facts = await fact_repo.list_by_project(project_id, body.category)
    existing_normalized = {f.content.strip().lower() for f in existing_facts}

    if pinned_content.strip().lower() in existing_normalized:
        existing = next(
            f for f in existing_facts if f.content.strip().lower() == pinned_content.strip().lower()
        )
        return _fact_to_dto(existing)

    fact = StructuredFact(
        project_id=project_id,
        category=body.category,
        content=pinned_content,
        source_message_id=None,
    )
    created = await fact_repo.create(fact)

    await vector_store.upsert_chunks(
        [
            VectorChunk(
                text=created.content,
                project_id=project_id,
                chunk_type="fact",
                metadata={"category": str(created.category), "pinned": True},
            )
        ]
    )

    return _fact_to_dto(created)


@router.patch(
    "/{fact_id}",
    response_model=FactResponseDTO,
    responses={404: {"description": "Fact not found"}},
)
async def update_fact(
    project_id: uuid.UUID,
    fact_id: uuid.UUID,
    body: FactUpdateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    fact_repo: FactRepository = Depends(get_fact_repo),
) -> FactResponseDTO:
    """Edit a stored AI-extracted fact — allows users to correct AI mistakes."""
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    existing = await fact_repo.get_by_id(fact_id, project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")
    existing.content = body.content
    if body.category is not None:
        existing.category = body.category
    updated = await fact_repo.update(existing)
    return _fact_to_dto(updated)


@router.delete(
    "/{fact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={404: {"description": "Fact not found"}},
)
async def delete_fact(
    project_id: uuid.UUID,
    fact_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    fact_repo: FactRepository = Depends(get_fact_repo),
) -> Response:
    """Delete a specific AI-extracted fact."""
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    deleted = await fact_repo.delete(fact_id, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fact not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
