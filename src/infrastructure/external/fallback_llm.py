from __future__ import annotations

import asyncio
import logging

from src.application.errors import LLMProviderError, map_llm_exception
from src.application.interfaces.llm import LLMService

logger = logging.getLogger(__name__)


class FallbackLLMService(LLMService):
    """Attempts providers in order with lightweight retry/backoff for transient errors."""

    def __init__(
        self,
        providers: list[tuple[str, LLMService]],
        retry_attempts: int = 1,
        retry_backoff_seconds: float = 0.6,
    ) -> None:
        if not providers:
            raise ValueError("FallbackLLMService requires at least one provider")
        self._providers = providers
        self._retry_attempts = max(1, retry_attempts)
        self._retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        msg = str(exc).lower()
        retry_signals = (
            "429",
            "resourceexhausted",
            "quota",
            "rate",
            "timeout",
            "temporarily",
            "503",
            "connection reset",
        )
        return any(signal in msg for signal in retry_signals)

    async def generate(self, prompt: str, system: str | None = None) -> str:
        last_exc: Exception | None = None
        last_provider: str | None = None

        for provider_name, provider in self._providers:
            for attempt in range(1, self._retry_attempts + 1):
                try:
                    return await provider.generate(prompt=prompt, system=system)
                except Exception as exc:  # noqa: BLE001
                    last_exc = exc
                    last_provider = provider_name
                    if isinstance(exc, LLMProviderError):
                        last_provider = exc.provider or provider_name
                    should_retry = attempt < self._retry_attempts and self._is_retryable(exc)

                    logger.warning(
                        "LLM provider '%s' failed on attempt %d/%d: %s",
                        provider_name,
                        attempt,
                        self._retry_attempts,
                        exc,
                    )

                    if should_retry:
                        await asyncio.sleep(self._retry_backoff_seconds * (2 ** (attempt - 1)))
                        continue
                    break

        if last_exc is None:
            raise LLMProviderError("All configured LLM providers failed", status_code=503)
        if isinstance(last_exc, LLMProviderError):
            raise last_exc
        raise map_llm_exception(last_exc, provider=last_provider) from last_exc
