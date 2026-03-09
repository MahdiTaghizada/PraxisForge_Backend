from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingService(ABC):
    """Application-layer interface for text embedding."""

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Return embedding vectors for a list of texts."""
        ...

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Return an embedding vector for a single query."""
        ...
