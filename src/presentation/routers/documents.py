"""Document Analysis router: multimodal file analysis endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dtos.schemas import DocumentAnalysisResponseDTO
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_document_analysis_repo,
    get_project_repo,
)

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["Document Analysis"])


@router.get("/", response_model=list[DocumentAnalysisResponseDTO])
async def list_document_analyses(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    analysis_repo: DocumentAnalysisRepository = Depends(get_document_analysis_repo),
) -> list[DocumentAnalysisResponseDTO]:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    analyses = await analysis_repo.list_by_project(project_id)
    return [
        DocumentAnalysisResponseDTO(
            id=a.id,
            file_id=a.file_id,
            project_id=a.project_id,
            extracted_text=a.extracted_text,
            ai_analysis=a.ai_analysis,
            content_type=a.content_type,
            processing_status=a.processing_status,
            metadata=a.metadata,
            created_at=a.created_at,
        )
        for a in analyses
    ]


@router.get("/{file_id}/analysis", response_model=DocumentAnalysisResponseDTO)
async def get_document_analysis(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    analysis_repo: DocumentAnalysisRepository = Depends(get_document_analysis_repo),
) -> DocumentAnalysisResponseDTO:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    analysis = await analysis_repo.get_by_file_id(file_id, project_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No analysis found for this file",
        )
    return DocumentAnalysisResponseDTO(
        id=analysis.id,
        file_id=analysis.file_id,
        project_id=analysis.project_id,
        extracted_text=analysis.extracted_text,
        ai_analysis=analysis.ai_analysis,
        content_type=analysis.content_type,
        processing_status=analysis.processing_status,
        metadata=analysis.metadata,
        created_at=analysis.created_at,
    )
