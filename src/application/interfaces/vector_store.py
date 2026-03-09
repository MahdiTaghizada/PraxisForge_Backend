from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class VectorChunk:
    """A single chunk to be stored/retrieved from the vector store."""

    text: str
    project_id: uuid.UUID
    file_id: uuid.UUID | None = None
    chunk_type: str = "document"  # "document" | "fact"
    metadata: dict | None = None


@dataclass
class VectorSearchResult:
    """A result returned from a vector similarity search."""

    text: str
    score: float
    metadata: dict


class VectorStoreService(ABC):
    """Application-layer interface for vector storage operations."""

    @abstractmethod
    async def ensure_collection(self) -> None:
        """Create the collection if it does not exist."""
        ...

    @abstractmethod
    async def upsert_chunks(self, chunks: list[VectorChunk]) -> None:
        """Embed and store a batch of text chunks."""
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        project_id: uuid.UUID,
        limit: int = 5,
        chunk_type: str | None = None,
    ) -> list[VectorSearchResult]:
        """Search for similar chunks scoped to a project."""
        ...

    @abstractmethod
    async def delete_by_file(self, project_id: uuid.UUID, file_id: uuid.UUID) -> None:
        """Remove all vectors associated with a specific file."""
        ...
