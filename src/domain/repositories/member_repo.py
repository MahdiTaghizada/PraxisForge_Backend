from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import ProjectMember


class MemberRepository(ABC):
    """Abstract repository for ProjectMember persistence."""

    @abstractmethod
    async def add(self, member: ProjectMember) -> ProjectMember: ...

    @abstractmethod
    async def get_by_project_and_user(
        self, project_id: uuid.UUID, user_id: str
    ) -> ProjectMember | None: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[ProjectMember]: ...

    @abstractmethod
    async def remove(self, project_id: uuid.UUID, user_id: str) -> bool: ...
