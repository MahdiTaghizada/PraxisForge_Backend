from __future__ import annotations

import asyncio
from functools import partial

import google.generativeai as genai

from src.application.interfaces.llm import LLMService
from src.infrastructure.config import settings


class GeminiLLMService(LLMService):
    """LLM implementation using Google Gemini."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_llm_model

    async def generate(self, prompt: str, system: str | None = None) -> str:
        loop = asyncio.get_running_loop()
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
        )
        response = await loop.run_in_executor(
            None,
            partial(model.generate_content, prompt),
        )
        return response.text or ""
