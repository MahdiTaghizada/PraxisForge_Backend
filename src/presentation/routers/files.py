from __future__ import annotations

import logging
import mimetypes
import os
import re
import uuid

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse

from src.application.dtos.schemas import FileResponseDTO
from src.application.interfaces.vector_store import VectorChunk, VectorStoreService
from src.application.use_cases.multimodal_processing import MultimodalProcessingUseCase
from src.domain.entities.models import File
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.domain.repositories.file_repo import FileRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.value_objects.enums import FileStatus
from src.infrastructure.config import settings
from src.infrastructure.database.repositories import PostgresDocumentAnalysisRepository
from src.infrastructure.database.session import async_session_factory
from src.infrastructure.external.gemini_vision import GeminiVisionService
from src.infrastructure.external.text_extraction import TextExtractionService
from src.presentation.dependencies.deps import (
    get_current_user_id,
    get_document_analysis_repo,
    get_file_repo,
    get_project_repo,
    get_vector_store,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/files", tags=["Files"])

# ── File upload constraints ───────────────────────────────
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
_ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".pdf", ".doc", ".docx", ".csv", ".json", ".xml",
    ".py", ".js", ".ts", ".java", ".c", ".cpp", ".go", ".rs", ".html", ".css",
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
    ".mp4", ".webm", ".mov",
    ".zip", ".tar", ".gz",
}
_SAFE_FILENAME_RE = re.compile(r"[^\w\-. ]", re.ASCII)

router = APIRouter(prefix="/projects/{project_id}/files", tags=["Files"])

# MIME types that trigger multimodal processing
_MULTIMODAL_MIMES = {
    "image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/tiff",
    "application/pdf",
}


async def _run_multimodal_processing(
    file_id: uuid.UUID,
    project_id: uuid.UUID,
    content: bytes,
    mime_type: str,
    filename: str,
) -> None:
    """Background task for multimodal file processing."""
    from src.infrastructure.external.gemini_embedding import GeminiEmbeddingService
    from src.infrastructure.vector_store.qdrant_store import QdrantVectorStore

    async with async_session_factory() as session:
        analysis_repo = PostgresDocumentAnalysisRepository(session)
        embedding_svc = GeminiEmbeddingService()
        vector_store = QdrantVectorStore(embedding_svc)
        vision_svc = GeminiVisionService()
        text_extractor = TextExtractionService()

        use_case = MultimodalProcessingUseCase(
            vision_service=vision_svc,
            text_extractor=text_extractor,
            vector_store=vector_store,
            analysis_repo=analysis_repo,
        )
        await use_case.process_file(
            file_id=file_id,
            project_id=project_id,
            content=content,
            mime_type=mime_type,
            filename=filename,
        )


async def _verify_project_access(
    project_id: uuid.UUID,
    owner_id: str,
    project_repo: ProjectRepository,
) -> None:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


@router.post("/", response_model=FileResponseDTO, status_code=status.HTTP_201_CREATED)
async def upload_file(
    project_id: uuid.UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    file_repo: FileRepository = Depends(get_file_repo),
    vector_store: VectorStoreService = Depends(get_vector_store),
) -> FileResponseDTO:
    await _verify_project_access(project_id, owner_id, project_repo)

    # Validate filename and extension
    original_name = file.filename or "upload.txt"
    safe_filename = _SAFE_FILENAME_RE.sub("_", os.path.basename(original_name))
    ext = os.path.splitext(safe_filename)[1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type '{ext}' is not allowed",
        )

    # Read and validate size
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {_MAX_FILE_SIZE // (1024*1024)} MB",
        )

    # Persist file to disk
    file_id = uuid.uuid4()
    project_dir = os.path.join(settings.upload_dir, str(project_id))
    os.makedirs(project_dir, exist_ok=True)
    dest_path = os.path.join(project_dir, f"{file_id}_{safe_filename}")

    async with aiofiles.open(dest_path, "wb") as out:
        await out.write(content)

    # Record in Postgres
    content_size = len(content)
    guessed_mime = mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
    file_entity = File(
        id=file_id,
        project_id=project_id,
        filename=safe_filename,
        file_path=dest_path,
        size_bytes=content_size,
        mime_type=guessed_mime,
        status=FileStatus.PROCESSING,
    )
    created = await file_repo.create(file_entity)

    # Chunk + vectorize (runs inline; move to BackgroundTasks for large files)
    try:
        text = content.decode("utf-8", errors="replace")
        chunks = _chunk_text(text)
        vector_chunks = [
            VectorChunk(
                text=chunk,
                project_id=project_id,
                file_id=file_id,
                chunk_type="document",
            )
            for chunk in chunks
        ]
        await vector_store.upsert_chunks(vector_chunks)
        await file_repo.update_status(file_id, FileStatus.READY.value)
        created.status = FileStatus.READY
    except Exception:
        await file_repo.update_status(file_id, FileStatus.FAILED.value)
        created.status = FileStatus.FAILED

    # Trigger multimodal processing for images and PDFs
    if guessed_mime in _MULTIMODAL_MIMES:
        background_tasks.add_task(
            _run_multimodal_processing,
            file_id=file_id,
            project_id=project_id,
            content=content,
            mime_type=guessed_mime,
            filename=safe_filename,
        )

    return FileResponseDTO(
        id=created.id,
        project_id=created.project_id,
        filename=created.filename,
        size_bytes=created.size_bytes,
        mime_type=created.mime_type,
        status=created.status,
        created_at=created.created_at,
    )


@router.get("/", response_model=list[FileResponseDTO])
async def list_files(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    file_repo: FileRepository = Depends(get_file_repo),
) -> list[FileResponseDTO]:
    await _verify_project_access(project_id, owner_id, project_repo)
    files = await file_repo.list_by_project(project_id)
    return [
        FileResponseDTO(
            id=f.id,
            project_id=f.project_id,
            filename=f.filename,
            size_bytes=f.size_bytes,
            mime_type=f.mime_type,
            status=f.status,
            created_at=f.created_at,
        )
        for f in files
    ]


@router.get(
    "/{file_id}/download",
    responses={
        404: {"description": "File not found"},
    },
)
async def download_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    file_repo: FileRepository = Depends(get_file_repo),
) -> FileResponse:
    await _verify_project_access(project_id, owner_id, project_repo)
    existing = await file_repo.get_by_id(file_id, project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if not os.path.exists(existing.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found on disk")
    return FileResponse(
        path=existing.file_path,
        filename=existing.filename,
        media_type=existing.mime_type or "application/octet-stream",
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def delete_file(
    project_id: uuid.UUID,
    file_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    file_repo: FileRepository = Depends(get_file_repo),
    vector_store: VectorStoreService = Depends(get_vector_store),
):
    await _verify_project_access(project_id, owner_id, project_repo)
    existing = await file_repo.get_by_id(file_id, project_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    # Remove vectors, then DB record, then disk
    await vector_store.delete_by_file(project_id, file_id)
    await file_repo.delete(file_id, project_id)
    if os.path.exists(existing.file_path):
        os.remove(existing.file_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
