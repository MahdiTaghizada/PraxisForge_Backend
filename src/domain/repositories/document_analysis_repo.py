from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import DocumentAnalysis


class DocumentAnalysisRepository(ABC):
    """Abstract repository for DocumentAnalysis persistence."""

    @abstractmethod
    async def create(self, analysis: DocumentAnalysis) -> DocumentAnalysis: ...

    @abstractmethod
    async def get_by_id(self, analysis_id: uuid.UUID, project_id: uuid.UUID) -> DocumentAnalysis | None: ...

    @abstractmethod
    async def get_by_file_id(self, file_id: uuid.UUID, project_id: uuid.UUID) -> DocumentAnalysis | None: ...

    @abstractmethod
    async def list_by_project(self, project_id: uuid.UUID) -> list[DocumentAnalysis]: ...

    @abstractmethod
    async def update_status(self, analysis_id: uuid.UUID, status: str) -> None: ...

    @abstractmethod
    async def update(self, analysis: DocumentAnalysis) -> DocumentAnalysis: ...

    @abstractmethod
    async def delete(self, analysis_id: uuid.UUID, project_id: uuid.UUID) -> bool: ...
