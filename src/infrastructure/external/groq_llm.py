from __future__ import annotations

import asyncio
from functools import partial

from groq import Groq

from src.application.interfaces.llm import LLMService
from src.infrastructure.config import settings


class GroqLLMService(LLMService):
    """LLM implementation using Groq for fast inference."""

    def __init__(self) -> None:
        self._client = Groq(api_key=settings.groq_api_key)
        self._model = settings.groq_model

    async def generate(self, prompt: str, system: str | None = None) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self._client.chat.completions.create,
                model=self._model,
                messages=messages,
                temperature=0.3,
                max_tokens=4096,
            ),
        )
        return response.choices[0].message.content or ""
