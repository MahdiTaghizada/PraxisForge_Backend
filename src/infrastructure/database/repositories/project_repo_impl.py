from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import Project
from src.domain.repositories.project_repo import ProjectRepository
from src.infrastructure.database.models.tables import ProjectModel


class PostgresProjectRepository(ProjectRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, project: Project) -> Project:
        row = ProjectModel(
            id=project.id,
            owner_id=project.owner_id,
            name=project.name,
            description=project.description,
            mode=project.mode.value,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(self, project_id: uuid.UUID, owner_id: str) -> Project | None:
        stmt = select(ProjectModel).where(
            ProjectModel.id == project_id,
            ProjectModel.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_owner(self, owner_id: str) -> list[Project]:
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.owner_id == owner_id)
            .order_by(ProjectModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def delete(self, project_id: uuid.UUID, owner_id: str) -> bool:
        stmt = select(ProjectModel).where(
            ProjectModel.id == project_id,
            ProjectModel.owner_id == owner_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    async def update(self, project: Project) -> Project:
        stmt = select(ProjectModel).where(ProjectModel.id == project.id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError(f"Project {project.id} not found")
        row.name = project.name
        row.description = project.description
        row.mode = project.mode.value if hasattr(project.mode, "value") else project.mode
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    @staticmethod
    def _to_entity(row: ProjectModel) -> Project:
        return Project(
            id=row.id,
            owner_id=row.owner_id,
            name=row.name,
            description=row.description,
            mode=row.mode,  # type: ignore[arg-type]
            created_at=row.created_at,
        )
