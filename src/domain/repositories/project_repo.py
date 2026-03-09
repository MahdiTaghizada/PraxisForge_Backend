from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import Project


class ProjectRepository(ABC):
    """Abstract repository for Project persistence."""

    @abstractmethod
    async def create(self, project: Project) -> Project: ...

    @abstractmethod
    async def get_by_id(self, project_id: uuid.UUID, owner_id: str) -> Project | None: ...

    @abstractmethod
    async def list_by_owner(self, owner_id: str) -> list[Project]: ...

    @abstractmethod
    async def update(self, project: Project) -> Project: ...

    @abstractmethod
    async def delete(self, project_id: uuid.UUID, owner_id: str) -> bool: ...
