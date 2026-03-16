"""Use case: AI-powered project uniqueness search with SWOT analysis."""

from __future__ import annotations

import json
import logging
import hashlib

from src.application.dtos.schemas import SWOTAnalysis
from src.application.interfaces.llm import LLMService
from src.application.interfaces.search_api import SearchAPIService
from src.infrastructure.cache.in_memory_ttl_cache import InMemoryTTLCache

logger = logging.getLogger(__name__)


class ProjectSearchUseCase:
    def __init__(
        self,
        search_api: SearchAPIService,
        llm: LLMService,
        cache: InMemoryTTLCache[dict] | None = None,
        cache_ttl_seconds: int = 180,
    ) -> None:
        self._search = search_api
        self._llm = llm
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    @staticmethod
    def _cache_key(project_name: str, project_description: str, custom_query: str | None) -> str:
        raw = f"{project_name}|{project_description}|{custom_query or ''}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return f"search:{digest}"

    async def execute(
        self,
        project_name: str,
        project_description: str,
        custom_query: str | None = None,
    ) -> dict:
        """Search the web for similar projects and produce a SWOT analysis."""

        cache_key = self._cache_key(project_name, project_description, custom_query)
        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # 1. Build search queries
        if custom_query:
            queries = [custom_query]
        else:
            queries = [
                f"{project_name} similar projects competitors",
                f"{project_description[:200]} existing solutions market",
            ]

        # 2. Gather raw search results
        all_results: list[dict] = []
        for q in queries:
            results = await self._search.search(q, max_results=5)
            all_results.extend(results)

        # De-duplicate by URL
        seen_urls: set[str] = set()
        unique_results: list[dict] = []
        for r in all_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)

        sources = [r["url"] for r in unique_results]
        search_context = "\n\n".join(
            f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content']}"
            for r in unique_results[:8]
        )

        # 3. Ask LLM to analyse uniqueness and produce SWOT
        analysis_prompt = (
            f"You are a competitive analysis expert.\n\n"
            f"PROJECT NAME: {project_name}\n"
            f"PROJECT DESCRIPTION: {project_description}\n\n"
            f"SEARCH RESULTS:\n{search_context}\n\n"
            f"Based on these search results, provide:\n"
            f"1. A concise summary of how unique this project is.\n"
            f"2. A list of competitor names found.\n"
            f"3. A SWOT analysis with exactly these keys: strengths, weaknesses, opportunities, threats. "
            f"Each value must be a JSON list of short strings.\n\n"
            f"Return ONLY valid JSON in this exact format:\n"
            f'{{"summary": "...", "competitors": ["..."], '
            f'"swot": {{"strengths": ["..."], "weaknesses": ["..."], '
            f'"opportunities": ["..."], "threats": ["..."]}}}}'
        )

        raw = await self._llm.generate(prompt=analysis_prompt)

        # 4. Parse LLM output
        try:
            # Strip markdown code fence if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Failed to parse SWOT JSON from LLM, returning raw text")
            parsed = {
                "summary": raw,
                "competitors": [],
                "swot": {
                    "strengths": [],
                    "weaknesses": [],
                    "opportunities": [],
                    "threats": [],
                },
            }

        swot_data = parsed.get("swot", {})
        result = {
            "summary": parsed.get("summary", raw),
            "competitors": parsed.get("competitors", []),
            "swot": SWOTAnalysis(
                strengths=swot_data.get("strengths", []),
                weaknesses=swot_data.get("weaknesses", []),
                opportunities=swot_data.get("opportunities", []),
                threats=swot_data.get("threats", []),
            ),
            "sources": sources,
        }

        if self._cache:
            self._cache.set(cache_key, result, self._cache_ttl_seconds)

        return result
