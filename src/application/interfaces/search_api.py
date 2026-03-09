from __future__ import annotations

from abc import ABC, abstractmethod


class SearchAPIService(ABC):
    """Application-layer interface for web search."""

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Execute a web search and return raw results."""
        ...
