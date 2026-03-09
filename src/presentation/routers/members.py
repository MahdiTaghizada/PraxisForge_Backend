"""Members router: project collaboration membership management."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dtos.schemas import ProjectMemberCreateDTO, ProjectMemberDTO
from src.domain.entities.models import ProjectMember
from src.domain.repositories.member_repo import MemberRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_member_repo,
    get_project_repo,
)

router = APIRouter(
    prefix="/projects/{project_id}/members",
    tags=["Project Members"],
)


async def _verify_project_access(
    project_id: uuid.UUID,
    owner_id: str,
    project_repo: ProjectRepository,
) -> None:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


@router.post(
    "/",
    response_model=ProjectMemberDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {"description": "Only project owner can invite members"},
        404: {"description": "Project not found"},
        409: {"description": "Member already exists"},
    },
)
async def invite_member(
    project_id: uuid.UUID,
    body: ProjectMemberCreateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    member_repo: MemberRepository = Depends(get_member_repo),
) -> ProjectMemberDTO:
    await _verify_project_access(project_id, owner_id, project_repo)

    # Generate a deterministic user_id from email for invited users
    member_user_id = str(uuid.uuid5(uuid.NAMESPACE_URL, body.email))

    existing = await member_repo.get_by_project_and_user(project_id, member_user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Member already exists in this project",
        )

    member = ProjectMember(
        project_id=project_id,
        user_id=member_user_id,
        email=body.email,
        role=body.role,
    )
    created = await member_repo.add(member)
    return ProjectMemberDTO(
        user_id=created.user_id,
        email=created.email,
        role=created.role,
    )


@router.get(
    "/",
    response_model=list[ProjectMemberDTO],
    responses={
        404: {"description": "Project not found"},
    },
)
async def list_members(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    member_repo: MemberRepository = Depends(get_member_repo),
) -> list[ProjectMemberDTO]:
    await _verify_project_access(project_id, owner_id, project_repo)
    members = await member_repo.list_by_project(project_id)
    return [
        ProjectMemberDTO(
            user_id=m.user_id,
            email=m.email,
            role=m.role,
        )
        for m in members
    ]
