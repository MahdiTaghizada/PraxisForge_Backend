from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import ChatMessage
from src.domain.repositories.chat_repo import ChatRepository
from src.infrastructure.database.models.tables import ChatMessageModel


class PostgresChatRepository(ChatRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_message(self, message: ChatMessage) -> ChatMessage:
        row = ChatMessageModel(
            id=message.id,
            project_id=message.project_id,
            role=message.role.value,
            content=message.content,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_history(
        self, project_id: uuid.UUID, limit: int = 50
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessageModel)
            .where(ChatMessageModel.project_id == project_id)
            .order_by(ChatMessageModel.created_at.asc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def clear_history(self, project_id: uuid.UUID) -> None:
        stmt = delete(ChatMessageModel).where(ChatMessageModel.project_id == project_id)
        await self._session.execute(stmt)
        await self._session.commit()

    @staticmethod
    def _to_entity(row: ChatMessageModel) -> ChatMessage:
        return ChatMessage(
            id=row.id,
            project_id=row.project_id,
            role=row.role,  # type: ignore[arg-type]
            content=row.content,
            created_at=row.created_at,
        )
