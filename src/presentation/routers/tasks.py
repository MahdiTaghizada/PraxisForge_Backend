from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.application.dtos.schemas import TaskCreateDTO, TaskResponseDTO, TaskUpdateDTO
from src.domain.entities.models import Task
from src.domain.repositories.member_repo import MemberRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.repositories.task_repo import TaskRepository
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_member_repo,
    get_project_repo,
    get_task_repo,
)

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])


async def _verify_project_access(
    project_id: uuid.UUID,
    owner_id: str,
    project_repo: ProjectRepository,
) -> None:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


async def _validate_assignee(
    assignee_id: uuid.UUID | None,
    project_id: uuid.UUID,
    member_repo: MemberRepository,
) -> None:
    """Ensure the assignee is a member of the project."""
    if assignee_id is None:
        return
    member = await member_repo.get_by_project_and_user(project_id, str(assignee_id))
    if not member:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Assignee {assignee_id} is not a member of this project",
        )


async def _validate_dependencies(
    dependency_ids: list[uuid.UUID],
    project_id: uuid.UUID,
    task_repo: TaskRepository,
    exclude_task_id: uuid.UUID | None = None,
) -> None:
    """Ensure all dependency task IDs exist within the same project and don't self-reference."""
    if not dependency_ids:
        return
    if exclude_task_id and exclude_task_id in dependency_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A task cannot depend on itself",
        )
    found = await task_repo.get_by_ids(dependency_ids, project_id)
    found_ids = {t.id for t in found}
    missing = set(dependency_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Dependency tasks not found in project: {[str(m) for m in missing]}",
        )


@router.post("/", response_model=TaskResponseDTO, status_code=status.HTTP_201_CREATED)
async def create_task(
    project_id: uuid.UUID,
    body: TaskCreateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    member_repo: MemberRepository = Depends(get_member_repo),
) -> TaskResponseDTO:
    await _verify_project_access(project_id, owner_id, project_repo)
    await _validate_assignee(body.assignee_id, project_id, member_repo)
    await _validate_dependencies(body.dependencies, project_id, task_repo)
    task = Task(
        project_id=project_id,
        title=body.title,
        description=body.description,
        assignee_id=body.assignee_id,
        priority=body.priority,
        tags=body.tags,
        dependencies=body.dependencies,
        deadline=body.deadline,
    )
    created = await task_repo.create(task)
    return TaskResponseDTO(**created.__dict__)


@router.get("/", response_model=list[TaskResponseDTO])
async def list_tasks(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
) -> list[TaskResponseDTO]:
    await _verify_project_access(project_id, owner_id, project_repo)
    tasks = await task_repo.list_by_project(project_id)
    return [TaskResponseDTO(**t.__dict__) for t in tasks]


@router.get(
    "/{task_id}",
    response_model=TaskResponseDTO,
    responses={
        404: {"description": "Project or task not found"},
    },
)
async def get_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
) -> TaskResponseDTO:
    await _verify_project_access(project_id, owner_id, project_repo)
    task = await task_repo.get_by_id(task_id, project_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return TaskResponseDTO(**task.__dict__)


@router.patch("/{task_id}", response_model=TaskResponseDTO)
async def update_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskUpdateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    member_repo: MemberRepository = Depends(get_member_repo),
) -> TaskResponseDTO:
    await _verify_project_access(project_id, owner_id, project_repo)
    existing = await task_repo.get_by_id(task_id, project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if body.assignee_id is not None:
        await _validate_assignee(body.assignee_id, project_id, member_repo)
    if body.dependencies is not None:
        await _validate_dependencies(body.dependencies, project_id, task_repo, exclude_task_id=task_id)
    if body.title is not None:
        existing.title = body.title
    if body.description is not None:
        existing.description = body.description
    if body.assignee_id is not None:
        existing.assignee_id = body.assignee_id
    if body.priority is not None:
        existing.priority = body.priority
    if body.tags is not None:
        existing.tags = body.tags
    if body.dependencies is not None:
        existing.dependencies = body.dependencies
    if body.deadline is not None:
        existing.deadline = body.deadline
    if body.status is not None:
        existing.status = body.status
    updated = await task_repo.update(existing)
    return TaskResponseDTO(**updated.__dict__)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_task(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
):
    await _verify_project_access(project_id, owner_id, project_repo)
    deleted = await task_repo.delete(task_id, project_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
