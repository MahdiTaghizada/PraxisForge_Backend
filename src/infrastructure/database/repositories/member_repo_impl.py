from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import ProjectMember
from src.domain.repositories.member_repo import MemberRepository
from src.infrastructure.database.models.tables import ProjectMemberModel


class PostgresMemberRepository(MemberRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, member: ProjectMember) -> ProjectMember:
        row = ProjectMemberModel(
            id=member.id,
            project_id=member.project_id,
            user_id=member.user_id,
            email=member.email,
            role=member.role.value if hasattr(member.role, "value") else member.role,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_project_and_user(
        self, project_id: uuid.UUID, user_id: str
    ) -> ProjectMember | None:
        stmt = select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_project(self, project_id: uuid.UUID) -> list[ProjectMember]:
        stmt = (
            select(ProjectMemberModel)
            .where(ProjectMemberModel.project_id == project_id)
            .order_by(ProjectMemberModel.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def remove(self, project_id: uuid.UUID, user_id: str) -> bool:
        stmt = select(ProjectMemberModel).where(
            ProjectMemberModel.project_id == project_id,
            ProjectMemberModel.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if not row:
            return False
        await self._session.delete(row)
        await self._session.commit()
        return True

    @staticmethod
    def _to_entity(row: ProjectMemberModel) -> ProjectMember:
        return ProjectMember(
            id=row.id,
            project_id=row.project_id,
            user_id=row.user_id,
            email=row.email,
            role=row.role,  # type: ignore[arg-type]
            created_at=row.created_at,
        )
