"""Use case: multimodal document processing pipeline.

Handles the full pipeline for uploaded documents:
1. Text extraction (OCR/PDF parsing)
2. Image analysis (Gemini Vision)
3. Structured text generation
4. Embedding and storage in Qdrant
"""

from __future__ import annotations

import logging
import uuid

from src.application.interfaces.vector_store import VectorChunk, VectorStoreService
from src.domain.entities.models import DocumentAnalysis
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.domain.value_objects.enums import DocumentProcessingStatus
from src.infrastructure.external.gemini_vision import GeminiVisionService
from src.infrastructure.external.text_extraction import TextExtractionService

logger = logging.getLogger(__name__)

_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/tiff"}
_PDF_MIMES = {"application/pdf"}


def _classify_content(mime_type: str, filename: str) -> str:
    """Determine the content type for processing."""
    if mime_type in _IMAGE_MIMES:
        lower = filename.lower()
        if any(kw in lower for kw in ("arch", "diagram", "flow", "uml", "erd", "design")):
            return "diagram"
        return "image"
    if mime_type in _PDF_MIMES:
        return "pdf"
    return "document"


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split text into overlapping chunks."""
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return [c.strip() for c in chunks if c.strip()]


class MultimodalProcessingUseCase:
    """Orchestrates the full multimodal document processing pipeline."""

    def __init__(
        self,
        vision_service: GeminiVisionService,
        text_extractor: TextExtractionService,
        vector_store: VectorStoreService,
        analysis_repo: DocumentAnalysisRepository,
    ) -> None:
        self._vision = vision_service
        self._extractor = text_extractor
        self._vector_store = vector_store
        self._analysis_repo = analysis_repo

    async def process_file(
        self,
        file_id: uuid.UUID,
        project_id: uuid.UUID,
        content: bytes,
        mime_type: str,
        filename: str,
        project_context: str = "",
    ) -> DocumentAnalysis:
        """Process an uploaded file through the full multimodal pipeline."""

        content_type = _classify_content(mime_type, filename)

        # Create initial analysis record
        analysis = DocumentAnalysis(
            file_id=file_id,
            project_id=project_id,
            content_type=content_type,
            processing_status=DocumentProcessingStatus.EXTRACTING_TEXT,
        )
        analysis = await self._analysis_repo.create(analysis)

        try:
            # Step 1: Extract text
            extracted_text = await self._extractor.extract(content, mime_type)
            analysis.extracted_text = extracted_text

            await self._analysis_repo.update_status(
                analysis.id, DocumentProcessingStatus.ANALYZING.value
            )

            # Step 2: AI analysis
            ai_analysis = ""
            if content_type in ("image", "diagram"):
                # Vision analysis for images
                ai_analysis = await self._vision.analyze_image(
                    image_bytes=content, mime_type=mime_type
                )
            elif extracted_text:
                # Text-based analysis for documents/PDFs
                ai_analysis = await self._vision.analyze_document_with_context(
                    text_content=extracted_text[:8000],
                    project_context=project_context,
                )
            analysis.ai_analysis = ai_analysis

            await self._analysis_repo.update_status(
                analysis.id, DocumentProcessingStatus.EMBEDDING.value
            )

            # Step 3: Build combined text for vectorization
            combined_text = self._build_combined_text(
                filename, content_type, extracted_text, ai_analysis
            )

            # Step 4: Chunk and store in Qdrant
            chunks = _chunk_text(combined_text)
            vector_chunks = [
                VectorChunk(
                    text=chunk,
                    project_id=project_id,
                    file_id=file_id,
                    chunk_type="document",
                    metadata={
                        "content_type": content_type,
                        "filename": filename,
                        "has_ai_analysis": bool(ai_analysis),
                    },
                )
                for chunk in chunks
            ]

            # Also store the AI analysis as a separate fact-like chunk
            if ai_analysis:
                vector_chunks.append(
                    VectorChunk(
                        text=f"[Analysis of {filename}] {ai_analysis[:2000]}",
                        project_id=project_id,
                        file_id=file_id,
                        chunk_type="document_analysis",
                        metadata={
                            "content_type": content_type,
                            "filename": filename,
                        },
                    )
                )

            await self._vector_store.upsert_chunks(vector_chunks)

            # Step 5: Update status to ready
            analysis.processing_status = DocumentProcessingStatus.READY
            analysis.metadata = {
                "chunks_created": len(vector_chunks),
                "extracted_text_length": len(extracted_text),
                "ai_analysis_length": len(ai_analysis),
            }
            await self._analysis_repo.update(analysis)

            return analysis

        except Exception as e:
            logger.error("Multimodal processing failed for file %s: %s", file_id, e)
            analysis.processing_status = DocumentProcessingStatus.FAILED
            analysis.metadata = {"error": str(e)}
            await self._analysis_repo.update(analysis)
            return analysis

    @staticmethod
    def _build_combined_text(
        filename: str,
        content_type: str,
        extracted_text: str,
        ai_analysis: str,
    ) -> str:
        """Combine extracted text and AI analysis into a rich text representation."""
        parts = [f"Document: {filename} (type: {content_type})"]

        if extracted_text:
            parts.append(f"\n--- Extracted Text ---\n{extracted_text}")
        if ai_analysis:
            parts.append(f"\n--- AI Analysis ---\n{ai_analysis}")

        return "\n".join(parts)
