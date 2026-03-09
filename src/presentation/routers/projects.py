from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.application.dtos.schemas import ProjectCreateDTO, ProjectResponseDTO, ProjectUpdateDTO
from src.domain.entities.models import Project
from src.domain.repositories.project_repo import ProjectRepository
from src.presentation.dependencies.deps import get_current_user_id, get_project_repo

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreateDTO,
    owner_id: str = Depends(get_current_user_id),
    repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponseDTO:
    project = Project(
        owner_id=owner_id,
        name=body.name,
        description=body.description,
        mode=body.mode,
    )
    created = await repo.create(project)
    return ProjectResponseDTO(**created.__dict__)


@router.get("/", response_model=list[ProjectResponseDTO])
async def list_projects(
    owner_id: str = Depends(get_current_user_id),
    repo: ProjectRepository = Depends(get_project_repo),
) -> list[ProjectResponseDTO]:
    projects = await repo.list_by_owner(owner_id)
    return [ProjectResponseDTO(**p.__dict__) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponseDTO)
async def get_project(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponseDTO:
    project = await repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return ProjectResponseDTO(**project.__dict__)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponseDTO,
    responses={
        404: {"description": "Project not found"},
    },
)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdateDTO,
    owner_id: str = Depends(get_current_user_id),
    repo: ProjectRepository = Depends(get_project_repo),
) -> ProjectResponseDTO:
    project = await repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    if body.name is not None:
        project.name = body.name
    if body.description is not None:
        project.description = body.description
    if body.mode is not None:
        project.mode = body.mode
    updated = await repo.update(project)
    return ProjectResponseDTO(**updated.__dict__)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_project(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    repo: ProjectRepository = Depends(get_project_repo),
):
    deleted = await repo.delete(project_id, owner_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
