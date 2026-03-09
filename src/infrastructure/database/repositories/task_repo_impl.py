from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import Task
from src.domain.repositories.task_repo import TaskRepository
from src.infrastructure.database.models.tables import TaskModel


class PostgresTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task: Task) -> Task:
        row = TaskModel(
            id=task.id,
            project_id=task.project_id,
            title=task.title,
            description=task.description,
            assignee_id=task.assignee_id,
            priority=task.priority.value if hasattr(task.priority, "value") else task.priority,
            tags=task.tags or [],
            dependencies=[d for d in task.dependencies] if task.dependencies else [],
            deadline=task.deadline,
            status=task.status.value,
            created_by=task.created_by,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(self, task_id: uuid.UUID, project_id: uuid.UUID) -> Task | None:
        stmt = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_by_ids(self, task_ids: list[uuid.UUID], project_id: uuid.UUID) -> list[Task]:
        if not task_ids:
            return []
        stmt = select(TaskModel).where(
            TaskModel.id.in_(task_ids),
            TaskModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def list_by_project(self, project_id: uuid.UUID) -> list[Task]:
        stmt = (
            select(TaskModel)
            .where(TaskModel.project_id == project_id)
            .order_by(TaskModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def update(self, task: Task) -> Task:
        stmt = select(TaskModel).where(TaskModel.id == task.id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError(f"Task {task.id} not found")
        row.title = task.title
        row.description = task.description
        row.assignee_id = task.assignee_id
        row.priority = task.priority.value if hasattr(task.priority, "value") else task.priority
        row.tags = task.tags or []
        row.dependencies = [d for d in task.dependencies] if task.dependencies else []
        row.deadline = task.deadline
        row.status = task.status.value
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def delete(self, task_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = select(TaskModel).where(
            TaskModel.id == task_id,
            TaskModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    @staticmethod
    def _to_entity(row: TaskModel) -> Task:
        return Task(
            id=row.id,
            project_id=row.project_id,
            title=row.title,
            description=row.description,
            assignee_id=row.assignee_id,
            priority=row.priority,  # type: ignore[arg-type]
            tags=row.tags or [],
            dependencies=list(row.dependencies) if row.dependencies else [],
            deadline=row.deadline,
            status=row.status,  # type: ignore[arg-type]
            created_by=row.created_by,
            created_at=row.created_at,
        )
