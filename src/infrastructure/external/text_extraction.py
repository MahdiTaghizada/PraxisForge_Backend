"""Text extraction service for documents (PDF + OCR)."""

from __future__ import annotations

import asyncio
import io
import logging
from functools import partial

logger = logging.getLogger(__name__)

# Image MIME types that need OCR
_IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp", "image/tiff"}
_PDF_MIMES = {"application/pdf"}


def _extract_text_from_pdf(content: bytes) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed — PDF text extraction unavailable")
        return ""

    text_parts: list[str] = []
    with fitz.open(stream=content, filetype="pdf") as doc:
        for page in doc:
            text_parts.append(page.get_text())
    return "\n".join(text_parts).strip()


def _extract_text_with_ocr(image_bytes: bytes) -> str:
    """Extract text from an image using Tesseract OCR."""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract/Pillow not installed — OCR unavailable")
        return ""

    image = Image.open(io.BytesIO(image_bytes))
    return pytesseract.image_to_string(image).strip()


class TextExtractionService:
    """Extracts text from PDFs and images using appropriate methods."""

    async def extract(self, content: bytes, mime_type: str) -> str:
        """Extract text from content based on MIME type.

        Returns extracted text or empty string if extraction not possible.
        """
        loop = asyncio.get_running_loop()

        if mime_type in _PDF_MIMES:
            text = await loop.run_in_executor(None, partial(_extract_text_from_pdf, content))
            if text:
                return text
            # If PDF text extraction yields nothing, try OCR on rendered pages
            return await self._ocr_pdf_pages(content)

        if mime_type in _IMAGE_MIMES:
            return await loop.run_in_executor(None, partial(_extract_text_with_ocr, content))

        # For text-based files, try UTF-8 decode
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return ""

    async def _ocr_pdf_pages(self, content: bytes) -> str:
        """Render PDF pages to images and OCR them."""
        loop = asyncio.get_running_loop()

        def _render_and_ocr() -> str:
            try:
                import fitz
                import pytesseract
                from PIL import Image
            except ImportError:
                return ""

            text_parts: list[str] = []
            with fitz.open(stream=content, filetype="pdf") as doc:
                for page in doc:
                    pix = page.get_pixmap(dpi=200)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    page_text = pytesseract.image_to_string(img)
                    if page_text.strip():
                        text_parts.append(page_text.strip())
            return "\n".join(text_parts)

        return await loop.run_in_executor(None, _render_and_ocr)
