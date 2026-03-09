"""Comments router: task-level discussion threads."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status

from src.application.dtos.schemas import CommentCreateDTO, CommentResponseDTO, CommentUpdateDTO
from src.domain.entities.models import Comment
from src.domain.repositories.comment_repo import CommentRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.repositories.task_repo import TaskRepository
from src.presentation.dependencies.deps import (
    get_comment_repo,
    get_current_user_id,
    get_project_repo,
    get_task_repo,
)

router = APIRouter(
    prefix="/projects/{project_id}/tasks/{task_id}/comments",
    tags=["Comments"],
)


async def _verify_task_access(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    owner_id: str,
    project_repo: ProjectRepository,
    task_repo: TaskRepository,
) -> None:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    task = await task_repo.get_by_id(task_id, project_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")


@router.post(
    "/",
    response_model=CommentResponseDTO,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "Project or task not found"},
    },
)
async def create_comment(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    body: CommentCreateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
) -> CommentResponseDTO:
    await _verify_task_access(project_id, task_id, owner_id, project_repo, task_repo)
    comment = Comment(
        task_id=task_id,
        project_id=project_id,
        author_id=owner_id,
        content=body.content,
    )
    created = await comment_repo.create(comment)
    return CommentResponseDTO(
        id=created.id,
        task_id=created.task_id,
        project_id=created.project_id,
        author_id=created.author_id,
        content=created.content,
        created_at=created.created_at,
    )


@router.get(
    "/",
    response_model=list[CommentResponseDTO],
    responses={
        404: {"description": "Project or task not found"},
    },
)
async def list_comments(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
) -> list[CommentResponseDTO]:
    await _verify_task_access(project_id, task_id, owner_id, project_repo, task_repo)
    comments = await comment_repo.list_by_task(task_id, project_id)
    return [
        CommentResponseDTO(
            id=c.id,
            task_id=c.task_id,
            project_id=c.project_id,
            author_id=c.author_id,
            content=c.content,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.get(
    "/{comment_id}",
    response_model=CommentResponseDTO,
    responses={404: {"description": "Project, task, or comment not found"}},
)
async def get_comment(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
) -> CommentResponseDTO:
    await _verify_task_access(project_id, task_id, owner_id, project_repo, task_repo)
    comment = await comment_repo.get_by_id(comment_id, task_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return CommentResponseDTO(
        id=comment.id,
        task_id=comment.task_id,
        project_id=comment.project_id,
        author_id=comment.author_id,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.patch(
    "/{comment_id}",
    response_model=CommentResponseDTO,
    responses={
        403: {"description": "Only the comment author can edit"},
        404: {"description": "Comment not found"},
    },
)
async def update_comment(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    body: CommentUpdateDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
) -> CommentResponseDTO:
    await _verify_task_access(project_id, task_id, owner_id, project_repo, task_repo)
    existing = await comment_repo.get_by_id(comment_id, task_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if existing.author_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the comment author can edit")
    existing.content = body.content
    updated = await comment_repo.update(existing)
    return CommentResponseDTO(
        id=updated.id,
        task_id=updated.task_id,
        project_id=updated.project_id,
        author_id=updated.author_id,
        content=updated.content,
        created_at=updated.created_at,
    )


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses={
        403: {"description": "Only the comment author can delete"},
        404: {"description": "Comment not found"},
    },
)
async def delete_comment(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    comment_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
) -> Response:
    await _verify_task_access(project_id, task_id, owner_id, project_repo, task_repo)
    existing = await comment_repo.get_by_id(comment_id, task_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    if existing.author_id != owner_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the comment author can delete")
    await comment_repo.delete(comment_id, task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
