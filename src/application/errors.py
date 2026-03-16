from __future__ import annotations

import re


class LLMProviderError(Exception):
    """Normalized exception for upstream LLM provider failures."""

    def __init__(
        self,
        message: str,
        status_code: int = 503,
        code: str = "llm_provider_unavailable",
        provider: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
        self.provider = provider
        self.retry_after_seconds = retry_after_seconds


def map_llm_exception(exc: Exception, provider: str | None = None) -> LLMProviderError:
    """Convert arbitrary provider exceptions into controlled HTTP-oriented errors."""
    msg = str(exc)
    lowered = msg.lower()

    retry_after_seconds: int | None = None
    retry_match = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", lowered)
    if retry_match:
        retry_after_seconds = max(1, int(float(retry_match.group(1))))

    if any(token in lowered for token in ("429", "resourceexhausted", "quota", "rate limit")):
        return LLMProviderError(
            message=msg,
            status_code=429,
            code="llm_rate_limited",
            provider=provider,
            retry_after_seconds=retry_after_seconds,
        )

    return LLMProviderError(
        message=msg,
        status_code=503,
        code="llm_provider_unavailable",
        provider=provider,
        retry_after_seconds=retry_after_seconds,
    )
