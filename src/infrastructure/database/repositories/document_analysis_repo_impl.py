from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.models import DocumentAnalysis
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.infrastructure.database.models.tables import DocumentAnalysisModel


class PostgresDocumentAnalysisRepository(DocumentAnalysisRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, analysis: DocumentAnalysis) -> DocumentAnalysis:
        row = DocumentAnalysisModel(
            id=analysis.id,
            file_id=analysis.file_id,
            project_id=analysis.project_id,
            extracted_text=analysis.extracted_text,
            ai_analysis=analysis.ai_analysis,
            content_type=analysis.content_type,
            processing_status=analysis.processing_status.value,
            metadata_json=analysis.metadata,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_entity(row)

    async def get_by_id(
        self, analysis_id: uuid.UUID, project_id: uuid.UUID
    ) -> DocumentAnalysis | None:
        stmt = select(DocumentAnalysisModel).where(
            DocumentAnalysisModel.id == analysis_id,
            DocumentAnalysisModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def get_by_file_id(
        self, file_id: uuid.UUID, project_id: uuid.UUID
    ) -> DocumentAnalysis | None:
        stmt = select(DocumentAnalysisModel).where(
            DocumentAnalysisModel.file_id == file_id,
            DocumentAnalysisModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def list_by_project(
        self, project_id: uuid.UUID
    ) -> list[DocumentAnalysis]:
        stmt = (
            select(DocumentAnalysisModel)
            .where(DocumentAnalysisModel.project_id == project_id)
            .order_by(DocumentAnalysisModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(r) for r in result.scalars().all()]

    async def update_status(self, analysis_id: uuid.UUID, status: str) -> None:
        stmt = (
            update(DocumentAnalysisModel)
            .where(DocumentAnalysisModel.id == analysis_id)
            .values(processing_status=status)
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def update(self, analysis: DocumentAnalysis) -> DocumentAnalysis:
        stmt = (
            update(DocumentAnalysisModel)
            .where(
                DocumentAnalysisModel.id == analysis.id,
                DocumentAnalysisModel.project_id == analysis.project_id,
            )
            .values(
                extracted_text=analysis.extracted_text,
                ai_analysis=analysis.ai_analysis,
                content_type=analysis.content_type,
                processing_status=str(analysis.processing_status),
                metadata_json=analysis.metadata,
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()
        return analysis

    async def delete(self, analysis_id: uuid.UUID, project_id: uuid.UUID) -> bool:
        stmt = delete(DocumentAnalysisModel).where(
            DocumentAnalysisModel.id == analysis_id,
            DocumentAnalysisModel.project_id == project_id,
        )
        result = await self._session.execute(stmt)
        await self._session.commit()
        return result.rowcount > 0

    @staticmethod
    def _to_entity(row: DocumentAnalysisModel) -> DocumentAnalysis:
        return DocumentAnalysis(
            id=row.id,
            file_id=row.file_id,
            project_id=row.project_id,
            extracted_text=row.extracted_text,
            ai_analysis=row.ai_analysis,
            content_type=row.content_type,
            processing_status=row.processing_status,  # type: ignore[arg-type]
            metadata=row.metadata_json or {},
            created_at=row.created_at,
        )
