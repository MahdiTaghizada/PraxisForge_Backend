from __future__ import annotations

from abc import ABC, abstractmethod


class LLMService(ABC):
    """Application-layer interface for LLM interactions."""

    @abstractmethod
    async def generate(self, prompt: str, system: str | None = None) -> str:
        """Generate a single text response."""
        ...
