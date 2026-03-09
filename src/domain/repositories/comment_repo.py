from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import Comment


class CommentRepository(ABC):
    """Abstract repository for Comment persistence."""

    @abstractmethod
    async def create(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def get_by_id(
        self, comment_id: uuid.UUID, task_id: uuid.UUID
    ) -> Comment | None: ...

    @abstractmethod
    async def list_by_task(
        self, task_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[Comment]: ...

    @abstractmethod
    async def update(self, comment: Comment) -> Comment: ...

    @abstractmethod
    async def delete(self, comment_id: uuid.UUID, task_id: uuid.UUID) -> bool: ...
