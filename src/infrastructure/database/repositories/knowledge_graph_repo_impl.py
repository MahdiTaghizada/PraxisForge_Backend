from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import KnowledgeEntity, KnowledgeRelationship
from src.domain.repositories.knowledge_graph_repo import (
    KnowledgeEntityRepository,
    KnowledgeRelationshipRepository,
)
from src.infrastructure.database.models.tables import (
    KnowledgeEntityModel,
    KnowledgeRelationshipModel,
)


class PostgresKnowledgeEntityRepository(KnowledgeEntityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, entity: KnowledgeEntity) -> KnowledgeEntity:
        row = KnowledgeEntityModel(
            id=entity.id,
            project_id=entity.project_id,
            name=entity.name,
            entity_type=entity.entity_type.value,
            description=entity.description,
            properties=entity.properties,
            source_message_id=entity.source_message_id,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(
        self, entity_id: uuid.UUID, project_id: uuid.UUID
    ) -> KnowledgeEntity | None:
        stmt = select(KnowledgeEntityModel).where(
            KnowledgeEntityModel.id == entity_id,
            KnowledgeEntityModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def find_by_name(
        self, project_id: uuid.UUID, name: str
    ) -> KnowledgeEntity | None:
        stmt = select(KnowledgeEntityModel).where(
            KnowledgeEntityModel.project_id == project_id,
            KnowledgeEntityModel.name == name,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_project(
        self, project_id: uuid.UUID, entity_type: str | None = None
    ) -> list[KnowledgeEntity]:
        stmt = select(KnowledgeEntityModel).where(
            KnowledgeEntityModel.project_id == project_id
        )
        if entity_type:
            stmt = stmt.where(KnowledgeEntityModel.entity_type == entity_type)
        stmt = stmt.order_by(KnowledgeEntityModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def update(self, entity: KnowledgeEntity) -> KnowledgeEntity:
        stmt = (
            update(KnowledgeEntityModel)
            .where(
                KnowledgeEntityModel.id == entity.id,
                KnowledgeEntityModel.project_id == entity.project_id,
            )
            .values(
                name=entity.name,
                entity_type=str(entity.entity_type),
                description=entity.description,
                properties=entity.properties,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return entity

    async def delete(self, entity_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = delete(KnowledgeEntityModel).where(
            KnowledgeEntityModel.id == entity_id,
            KnowledgeEntityModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def delete_by_project(self, project_id: uuid.UUID) -> None:
        stmt = delete(KnowledgeEntityModel).where(
            KnowledgeEntityModel.project_id == project_id
        )
        await self._session.execute(stmt)
        await self._session.commit()

    @staticmethod
    def _to_entity(row: KnowledgeEntityModel) -> KnowledgeEntity:
        return KnowledgeEntity(
            id=row.id,
            project_id=row.project_id,
            name=row.name,
            entity_type=row.entity_type,  # type: ignore[arg-type]
            description=row.description,
            properties=row.properties or {},
            source_message_id=row.source_message_id,
            created_at=row.created_at,
        )


class PostgresKnowledgeRelationshipRepository(KnowledgeRelationshipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, rel: KnowledgeRelationship) -> KnowledgeRelationship:
        row = KnowledgeRelationshipModel(
            id=rel.id,
            project_id=rel.project_id,
            source_entity_id=rel.source_entity_id,
            target_entity_id=rel.target_entity_id,
            relationship_type=rel.relationship_type.value,
            description=rel.description,
            confidence=rel.confidence,
            source_message_id=rel.source_message_id,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(
        self, rel_id: uuid.UUID, project_id: uuid.UUID
    ) -> KnowledgeRelationship | None:
        stmt = select(KnowledgeRelationshipModel).where(
            KnowledgeRelationshipModel.id == rel_id,
            KnowledgeRelationshipModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_project(
        self, project_id: uuid.UUID
    ) -> list[KnowledgeRelationship]:
        stmt = (
            select(KnowledgeRelationshipModel)
            .where(KnowledgeRelationshipModel.project_id == project_id)
            .order_by(KnowledgeRelationshipModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def list_by_entity(
        self, entity_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[KnowledgeRelationship]:
        from sqlalchemy import or_

        stmt = (
            select(KnowledgeRelationshipModel)
            .where(
                KnowledgeRelationshipModel.project_id == project_id,
                or_(
                    KnowledgeRelationshipModel.source_entity_id == entity_id,
                    KnowledgeRelationshipModel.target_entity_id == entity_id,
                ),
            )
            .order_by(KnowledgeRelationshipModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def delete(self, rel_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = delete(KnowledgeRelationshipModel).where(
            KnowledgeRelationshipModel.id == rel_id,
            KnowledgeRelationshipModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    async def delete_by_project(self, project_id: uuid.UUID) -> None:
        stmt = delete(KnowledgeRelationshipModel).where(
            KnowledgeRelationshipModel.project_id == project_id
        )
        await self._session.execute(stmt)
        await self._session.commit()

    @staticmethod
    def _to_entity(row: KnowledgeRelationshipModel) -> KnowledgeRelationship:
        return KnowledgeRelationship(
            id=row.id,
            project_id=row.project_id,
            source_entity_id=row.source_entity_id,
            target_entity_id=row.target_entity_id,
            relationship_type=row.relationship_type,  # type: ignore[arg-type]
            description=row.description,
            confidence=row.confidence,
            source_message_id=row.source_message_id,
            created_at=row.created_at,
        )
