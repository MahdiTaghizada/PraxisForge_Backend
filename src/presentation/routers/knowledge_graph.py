"""Knowledge Graph router: manage project entities and relationships."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.application.dtos.schemas import (
    KnowledgeEntityCreateDTO,
    KnowledgeEntityResponseDTO,
    KnowledgeGraphResponseDTO,
    KnowledgeRelationshipCreateDTO,
    KnowledgeRelationshipResponseDTO,
)
from src.domain.entities.models import KnowledgeEntity, KnowledgeRelationship
from src.domain.repositories.knowledge_graph_repo import (
    KnowledgeEntityRepository,
    KnowledgeRelationshipRepository,
)
from src.domain.repositories.project_repo import ProjectRepository
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_entity_repo,
    get_project_repo,
    get_relationship_repo,
)

router = APIRouter(prefix="/projects/{project_id}/knowledge-graph", tags=["Knowledge Graph"])


async def _verify_project(
    project_id: uuid.UUID,
    owner_id: str,
    project_repo: ProjectRepository,
) -> None:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


# ── Entities ──────────────────────────────────────────────


@router.get("/", response_model=KnowledgeGraphResponseDTO)
async def get_knowledge_graph(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
    rel_repo: KnowledgeRelationshipRepository = Depends(get_relationship_repo),
) -> KnowledgeGraphResponseDTO:
    await _verify_project(project_id, owner_id, project_repo)
    entities = await entity_repo.list_by_project(project_id)
    relationships = await rel_repo.list_by_project(project_id)

    return KnowledgeGraphResponseDTO(
        entities=[
            KnowledgeEntityResponseDTO(
                id=e.id,
                project_id=e.project_id,
                name=e.name,
                entity_type=e.entity_type,
                description=e.description,
                properties=e.properties,
                created_at=e.created_at,
            )
            for e in entities
        ],
        relationships=[
            KnowledgeRelationshipResponseDTO(
                id=r.id,
                project_id=r.project_id,
                source_entity_id=r.source_entity_id,
                target_entity_id=r.target_entity_id,
                relationship_type=r.relationship_type,
                description=r.description,
                confidence=r.confidence,
                created_at=r.created_at,
            )
            for r in relationships
        ],
    )


@router.get("/entities", response_model=list[KnowledgeEntityResponseDTO])
async def list_entities(
    project_id: uuid.UUID,
    entity_type: str | None = None,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
) -> list[KnowledgeEntityResponseDTO]:
    await _verify_project(project_id, owner_id, project_repo)
    entities = await entity_repo.list_by_project(project_id, entity_type=entity_type)
    return [
        KnowledgeEntityResponseDTO(
            id=e.id,
            project_id=e.project_id,
            name=e.name,
            entity_type=e.entity_type,
            description=e.description,
            properties=e.properties,
            created_at=e.created_at,
        )
        for e in entities
    ]


@router.post("/entities", response_model=KnowledgeEntityResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_entity(
    project_id: uuid.UUID,
    body: KnowledgeEntityCreateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
) -> KnowledgeEntityResponseDTO:
    await _verify_project(project_id, owner_id, project_repo)

    # Deduplicate by name
    existing = await entity_repo.find_by_name(project_id, body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Entity '{body.name}' already exists in this project",
        )

    entity = KnowledgeEntity(
        project_id=project_id,
        name=body.name,
        entity_type=body.entity_type,
        description=body.description,
        properties=body.properties,
    )
    created = await entity_repo.create(entity)
    return KnowledgeEntityResponseDTO(
        id=created.id,
        project_id=created.project_id,
        name=created.name,
        entity_type=created.entity_type,
        description=created.description,
        properties=created.properties,
        created_at=created.created_at,
    )


@router.delete("/entities/{entity_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_entity(
    project_id: uuid.UUID,
    entity_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
):
    await _verify_project(project_id, owner_id, project_repo)
    deleted = await entity_repo.delete(entity_id, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")


# ── Relationships ─────────────────────────────────────────


@router.post("/relationships", response_model=KnowledgeRelationshipResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    project_id: uuid.UUID,
    body: KnowledgeRelationshipCreateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
    rel_repo: KnowledgeRelationshipRepository = Depends(get_relationship_repo),
) -> KnowledgeRelationshipResponseDTO:
    await _verify_project(project_id, owner_id, project_repo)

    # Verify both entities exist
    source = await entity_repo.get_by_id(body.source_entity_id, project_id)
    target = await entity_repo.get_by_id(body.target_entity_id, project_id)
    if not source or not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source or target entity not found",
        )

    relationship = KnowledgeRelationship(
        project_id=project_id,
        source_entity_id=body.source_entity_id,
        target_entity_id=body.target_entity_id,
        relationship_type=body.relationship_type,
        description=body.description,
    )
    created = await rel_repo.create(relationship)
    return KnowledgeRelationshipResponseDTO(
        id=created.id,
        project_id=created.project_id,
        source_entity_id=created.source_entity_id,
        target_entity_id=created.target_entity_id,
        relationship_type=created.relationship_type,
        description=created.description,
        confidence=created.confidence,
        created_at=created.created_at,
    )


@router.delete("/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_relationship(
    project_id: uuid.UUID,
    rel_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    rel_repo: KnowledgeRelationshipRepository = Depends(get_relationship_repo),
):
    await _verify_project(project_id, owner_id, project_repo)
    deleted = await rel_repo.delete(rel_id, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Relationship not found")
