from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from src.domain.entities.models import ChatMessage


class ChatRepository(ABC):
    """Abstract repository for ChatMessage persistence."""

    @abstractmethod
    async def add_message(self, message: ChatMessage) -> ChatMessage: ...

    @abstractmethod
    async def get_history(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> list[ChatMessage]: ...

    @abstractmethod
    async def clear_history(self, project_id: uuid.UUID) -> None: ...
