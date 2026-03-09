from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import Task


class TaskRepository(ABC):
    """Abstract repository for Task persistence."""

    @abstractmethod
    async def create(self, task: Task) -> Task: ...

    @abstractmethod
    async def get_by_id(self, task_id: uuid.UUID, project_id: uuid.UUID) -> Task | None: ...

    @abstractmethod
    async def get_by_ids(self, task_ids: list[uuid.UUID], project_id: uuid.UUID) -> list[Task]: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[Task]: ...

    @abstractmethod
    async def update(self, task: Task) -> Task: ...

    @abstractmethod
    async def delete(self, task_id: uuid.UUID, project_id: uuid.UUID) -> bool: ...
