from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import StructuredFact
from src.domain.repositories.fact_repo import FactRepository
from src.infrastructure.database.models.tables import StructuredFactModel


class PostgresFactRepository(FactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, fact: StructuredFact) -> StructuredFact:
        row = StructuredFactModel(
            id=fact.id,
            project_id=fact.project_id,
            category=fact.category.value,
            content=fact.content,
            source_message_id=fact.source_message_id,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(
        self, fact_id: uuid.UUID, project_id: uuid.UUID
    ) -> StructuredFact | None:
        stmt = select(StructuredFactModel).where(
            StructuredFactModel.id == fact_id,
            StructuredFactModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_project(
        self, project_id: uuid.UUID, category: str | None = None
    ) -> list[StructuredFact]:
        stmt = select(StructuredFactModel).where(
            StructuredFactModel.project_id == project_id
        )
        if category:
            stmt = stmt.where(StructuredFactModel.category == category)
        stmt = stmt.order_by(StructuredFactModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def update(self, fact: StructuredFact) -> StructuredFact:
        stmt = (
            update(StructuredFactModel)
            .where(
                StructuredFactModel.id == fact.id,
                StructuredFactModel.project_id == fact.project_id,
            )
            .values(content=fact.content, category=str(fact.category))
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return fact

    async def delete(self, fact_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = delete(StructuredFactModel).where(
            StructuredFactModel.id == fact_id,
            StructuredFactModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def delete_by_project(self, project_id: uuid.UUID) -> None:
        stmt = delete(StructuredFactModel).where(
            StructuredFactModel.project_id == project_id
        )
        await self._session.execute(stmt)
        await self._session.commit()

    @staticmethod
    def _to_entity(row: StructuredFactModel) -> StructuredFact:
        return StructuredFact(
            id=row.id,
            project_id=row.project_id,
            category=row.category,  # type: ignore[arg-type]
            content=row.content,
            source_message_id=row.source_message_id,
            created_at=row.created_at,
        )
