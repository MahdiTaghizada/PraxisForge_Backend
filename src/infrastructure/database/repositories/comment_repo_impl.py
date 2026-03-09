from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import Comment
from src.domain.repositories.comment_repo import CommentRepository
from src.infrastructure.database.models.tables import CommentModel


class PostgresCommentRepository(CommentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, comment: Comment) -> Comment:
        row = CommentModel(
            id=comment.id,
            task_id=comment.task_id,
            project_id=comment.project_id,
            author_id=comment.author_id,
            content=comment.content,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(
        self, comment_id: uuid.UUID, task_id: uuid.UUID
    ) -> Comment | None:
        stmt = select(CommentModel).where(
            CommentModel.id == comment_id,
            CommentModel.task_id == task_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_task(
        self, task_id: uuid.UUID, project_id: uuid.UUID
    ) -> list[Comment]:
        stmt = (
            select(CommentModel)
            .where(
                CommentModel.task_id == task_id,
                CommentModel.project_id == project_id,
            )
            .order_by(CommentModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def update(self, comment: Comment) -> Comment:
        stmt = select(CommentModel).where(CommentModel.id == comment.id)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            raise ValueError(f"Comment {comment.id} not found")
        row.content = comment.content
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def delete(self, comment_id: uuid.UUID, task_id: uuid.UUID) -> bool:
        stmt = select(CommentModel).where(
            CommentModel.id == comment_id,
            CommentModel.task_id == task_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    @staticmethod
    def _to_entity(row: CommentModel) -> Comment:
        return Comment(
            id=row.id,
            task_id=row.task_id,
            project_id=row.project_id,
            author_id=row.author_id,
            content=row.content,
            created_at=row.created_at,
        )
