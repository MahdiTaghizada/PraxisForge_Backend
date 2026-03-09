from __future__ import annotations

import asyncio
from functools import partial

from tavily import TavilyClient

from src.application.interfaces.search_api import SearchAPIService
from src.infrastructure.config import settings


class TavilySearchService(SearchAPIService):
    """Web search implementation using Tavily API."""

    def __init__(self) -> None:
        self._client = TavilyClient(api_key=settings.tavily_api_key)

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self._client.search,
                query=query,
                max_results=max_results,
                search_depth="advanced",
            ),
        )
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
            }
            for r in response.get("results", [])
        ]
