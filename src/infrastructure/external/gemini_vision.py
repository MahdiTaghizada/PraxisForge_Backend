"""Gemini Vision service for multimodal image/document analysis."""

from __future__ import annotations

import asyncio
import base64
import logging
from functools import partial

import google.generativeai as genai

from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


class GeminiVisionService:
    """Analyse images and documents using Gemini's multimodal capabilities."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_llm_model

    async def analyze_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        prompt: str | None = None,
    ) -> str:
        """Analyze an image and return a text description."""
        loop = asyncio.get_running_loop()
        model = genai.GenerativeModel(model_name=self._model_name)

        analysis_prompt = prompt or (
            "Analyze this image in detail. Describe:\n"
            "1. What the image shows\n"
            "2. If it's a diagram/architecture: identify components, connections, and patterns\n"
            "3. If it's a screenshot: identify the application, UI elements, and state\n"
            "4. Any text visible in the image\n"
            "5. Key technical insights\n\n"
            "Be specific and structured in your analysis."
        )

        image_part = {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8"),
        }

        response = await loop.run_in_executor(
            None,
            partial(model.generate_content, [analysis_prompt, image_part]),
        )
        return response.text or ""

    async def analyze_document_with_context(
        self,
        text_content: str,
        project_context: str = "",
    ) -> str:
        """Analyze extracted document text in the context of the project."""
        loop = asyncio.get_running_loop()
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=(
                "You are a technical document analyst. Analyze the content and "
                "extract key insights, decisions, components, and action items."
            ),
        )

        prompt = (
            f"PROJECT CONTEXT:\n{project_context}\n\n"
            f"DOCUMENT CONTENT:\n{text_content}\n\n"
            "Provide a structured analysis covering:\n"
            "1. Summary of the document\n"
            "2. Key technical components mentioned\n"
            "3. Architecture decisions or patterns\n"
            "4. Action items or tasks implied\n"
            "5. Technologies and tools referenced"
        )

        response = await loop.run_in_executor(
            None,
            partial(model.generate_content, prompt),
        )
        return response.text or ""
