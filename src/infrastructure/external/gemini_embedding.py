from __future__ import annotations

import asyncio
from functools import partial

import google.generativeai as genai

from src.application.interfaces.embedding import EmbeddingService
from src.infrastructure.config import settings


class GeminiEmbeddingService(EmbeddingService):
    """Embedding implementation using Google Gemini Embedding API."""

    def __init__(self) -> None:
        genai.configure(api_key=settings.gemini_api_key)
        self._model = settings.gemini_embedding_model

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                genai.embed_content,
                model=self._model,
                content=texts,
                task_type="retrieval_document",
            ),
        )
        return result["embedding"]

    async def embed_query(self, text: str) -> list[float]:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            partial(
                genai.embed_content,
                model=self._model,
                content=text,
                task_type="retrieval_query",
            ),
        )
        return result["embedding"]
