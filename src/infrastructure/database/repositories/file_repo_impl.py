from __future__ import annotations

import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import File
from src.domain.repositories.file_repo import FileRepository
from src.infrastructure.database.models.tables import FileModel


class PostgresFileRepository(FileRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, file: File) -> File:
        row = FileModel(
            id=file.id,
            project_id=file.project_id,
            filename=file.filename,
            file_path=file.file_path,
            size_bytes=file.size_bytes,
            mime_type=file.mime_type,
            status=file.status.value,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(self, file_id: uuid.UUID, project_id: uuid.UUID) -> File | None:
        stmt = select(FileModel).where(
            FileModel.id == file_id,
            FileModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_project(self, project_id: uuid.UUID) -> list[File]:
        stmt = (
            select(FileModel)
            .where(FileModel.project_id == project_id)
            .order_by(FileModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def update_status(self, file_id: uuid.UUID, status: str) -> None:
        stmt = update(FileModel).where(FileModel.id == file_id).values(status=status)
        await self._session.execute(stmt)
        await self._session.commit()

    async def delete(self, file_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = select(FileModel).where(
            FileModel.id == file_id,
            FileModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    @staticmethod
    def _to_entity(row: FileModel) -> File:
        return File(
            id=row.id,
            project_id=row.project_id,
            filename=row.filename,
            file_path=row.file_path,
            size_bytes=row.size_bytes,
            mime_type=row.mime_type,
            status=row.status,  # type: ignore[arg-type]
            created_at=row.created_at,
        )
