from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import StructuredFact


class FactRepository(ABC):
    """Abstract repository for StructuredFact persistence."""

    @abstractmethod
    async def create(self, fact: StructuredFact) -> StructuredFact: ...

    @abstractmethod
    async def get_by_id(self, fact_id: uuid.UUID, project_id: uuid.UUID) -> StructuredFact | None: ...

    @abstractmethod
    async def list_by_project(
        self, project_id: uuid.UUID, category: str | None = None
    ) -> list[StructuredFact]: ...

    @abstractmethod
    async def update(self, fact: StructuredFact) -> StructuredFact: ...

    @abstractmethod
    async def delete(self, fact_id: uuid.UUID, project_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def delete_by_project(self, project_id: uuid.UUID) -> None: ...
