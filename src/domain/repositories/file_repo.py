from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import File


class FileRepository(ABC):
    """Abstract repository for File persistence."""

    @abstractmethod
    async def create(self, file: File) -> File: ...

    @abstractmethod
    async def get_by_id(self, file_id: uuid.UUID, project_id: uuid.UUID) -> File | None: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[File]: ...

    @abstractmethod
    async def update_status(self, file_id: uuid.UUID, status: str) -> None: ...

    @abstractmethod
    async def delete(self, file_id: uuid.UUID, project_id: uuid.UUID) -> bool: ...
