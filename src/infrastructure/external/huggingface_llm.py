from __future__ import annotations

import asyncio
import json
from functools import partial
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.application.interfaces.llm import LLMService
from src.infrastructure.config import settings


class HuggingFaceLLMService(LLMService):
    """LLM implementation using Hugging Face Inference API."""

    def __init__(self) -> None:
        self._api_key = settings.huggingface_api_key
        self._model = settings.huggingface_model
        self._base_url = settings.huggingface_api_base.rstrip("/")
        self._timeout = settings.huggingface_timeout_seconds

    def _call_inference(self, prompt: str, system: str | None = None) -> str:
        merged_prompt = prompt if not system else f"{system}\n\n{prompt}"
        payload = {
            "inputs": merged_prompt,
            "parameters": {
                "temperature": 0.3,
                "max_new_tokens": 1024,
                "return_full_text": False,
            },
        }
        data = json.dumps(payload).encode("utf-8")

        url = f"{self._base_url}/{self._model}"
        req = Request(
            url=url,
            data=data,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HuggingFace HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise RuntimeError(f"HuggingFace network error: {exc.reason}") from exc

        parsed = json.loads(raw)
        if isinstance(parsed, list) and parsed:
            first = parsed[0]
            if isinstance(first, dict):
                return first.get("generated_text", "") or ""
        if isinstance(parsed, dict):
            if "generated_text" in parsed:
                return parsed.get("generated_text", "") or ""
            if "error" in parsed:
                raise RuntimeError(f"HuggingFace error: {parsed['error']}")

        raise RuntimeError("HuggingFace returned an unexpected response format")

    async def generate(self, prompt: str, system: str | None = None) -> str:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(self._call_inference, prompt, system))
