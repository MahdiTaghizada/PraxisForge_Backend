from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import KnowledgeEntity, KnowledgeRelationship


class KnowledgeEntityRepository(ABC):
    """Abstract repository for KnowledgeEntity persistence."""

    @abstractmethod
    async def create(self, entity: KnowledgeEntity) -> KnowledgeEntity: ...

    @abstractmethod
    async def get_by_id(self, entity_id: uuid.UUID, project_id: uuid.UUID) -> KnowledgeEntity | None: ...

    @abstractmethod
    async def find_by_name(self, project_id: uuid.UUID, name: str) -> KnowledgeEntity | None: ...

    @abstractmethod
    async def list_by_project(
        self, project_id: uuid.UUID, entity_type: str | None = None
    ) -> list[KnowledgeEntity]: ...

    @abstractmethod
    async def update(self, entity: KnowledgeEntity) -> KnowledgeEntity: ...

    @abstractmethod
    async def delete(self, entity_id: uuid.UUID, project_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def delete_by_project(self, project_id: uuid.UUID) -> None: ...


class KnowledgeRelationshipRepository(ABC):
    """Abstract repository for KnowledgeRelationship persistence."""

    @abstractmethod
    async def create(self, rel: KnowledgeRelationship) -> KnowledgeRelationship: ...

    @abstractmethod
    async def get_by_id(self, rel_id: uuid.UUID, project_id: uuid.UUID) -> KnowledgeRelationship | None: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[KnowledgeRelationship]: ...

    @abstractmethod
    async def list_by_entity(
        self, entity_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[KnowledgeRelationship]: ...

    @abstractmethod
    async def delete(self, rel_id: uuid.UUID, project_id: uuid.UUID) -> bool: ...

    @abstractmethod
    async def delete_by_project(self, project_id: uuid.UUID) -> None: ...
