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


def _contains_azerbaijani_chars(text: str) -> bool:
    lowered = text.lower()
    return any(ch in lowered for ch in "əğıöşüç")


def _looks_azerbaijani_text(text: str) -> bool:
    lowered = text.lower()
    markers = [" və ", " üçün ", " layihə", "bazar", "rəqib", "məlumat"]
    hits = sum(1 for marker in markers if marker in lowered)
    return _contains_azerbaijani_chars(lowered) or hits >= 2


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

    async def _expand_queries(
        self,
        project_name: str,
        project_description: str,
        custom_query: str | None,
    ) -> list[str]:
        seed_query = custom_query or f"{project_name} {project_description[:240]}"
        fallback_queries = [
            seed_query,
            f"{project_name} similar products competitors pricing",
            f"{project_name} startup idea validation market gap",
            f"{project_description[:220]} existing solutions case studies",
            f"{project_name} alternatives review",
            f"{project_name} industry trends 2025 2026",
        ]

        query_prompt = (
            "You are generating web search queries for deep market research.\n"
            f"Project name: {project_name}\n"
            f"Project description: {project_description}\n"
            f"User query: {custom_query or ''}\n\n"
            "Generate 8 concise, high-signal search queries.\n"
            "Requirements:\n"
            "- Include mostly English queries for broader web coverage.\n"
            "- Include 1-2 local-language variants if useful.\n"
            "- Cover competitors, alternatives, pricing, user pain points, and market gap.\n"
            "Return ONLY JSON: {\"queries\": [\"...\"]}"
        )

        try:
            raw = await self._llm.generate(prompt=query_prompt)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())
            generated = [str(q).strip() for q in parsed.get("queries", []) if str(q).strip()]
        except (json.JSONDecodeError, IndexError, TypeError, ValueError):
            generated = []

        ordered: list[str] = []
        seen: set[str] = set()
        for q in [*generated, *fallback_queries]:
            norm = q.strip().lower()
            if not norm or norm in seen:
                continue
            seen.add(norm)
            ordered.append(q.strip())

        return ordered[:10]

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

        # 1. Build richer multilingual query set (English-first for better recall)
        queries = await self._expand_queries(project_name, project_description, custom_query)

        # 2. Gather raw search results
        all_results: list[dict] = []
        for q in queries:
            results = await self._search.search(q, max_results=8)
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
            for r in unique_results[:20]
        )

        prefer_azerbaijani = _looks_azerbaijani_text(custom_query or "")
        output_language_instruction = (
            "Respond in Azerbaijani because user query is Azerbaijani."
            if prefer_azerbaijani
            else "Respond in English (default)."
        )

        # 3. Ask LLM to analyse uniqueness and produce SWOT
        analysis_prompt = (
            f"You are a market research and competitive intelligence analyst.\n\n"
            f"PROJECT NAME: {project_name}\n"
            f"PROJECT DESCRIPTION: {project_description}\n\n"
            f"SEARCH RESULTS:\n{search_context}\n\n"
            f"Provide a detailed analysis:\n"
            f"1) A detailed uniqueness summary with concrete market signals.\n"
            f"2) Competitor names and brief why they are relevant.\n"
            f"3) SWOT analysis (strengths, weaknesses, opportunities, threats), each as short bullet strings.\n"
            f"4) Early-stage scoring (0-100): uniqueness_score, market_gap_score, feasibility_score, innovation_score, early_stage_fit_score.\n"
            f"5) A final verdict and 4-8 concrete recommendations.\n\n"
            f"Rules:\n"
            f"- {output_language_instruction}\n"
            f"- Scores must be integers from 0 to 100.\n"
            f"- Base conclusions on the provided search results; avoid fabricated claims.\n"
            f"- Return only valid JSON.\n\n"
            f"Use this exact JSON format:\n"
            f'{{"summary": "...", "competitors": ["..."], '
            f'"swot": {{"strengths": ["..."], "weaknesses": ["..."], '
            f'"opportunities": ["..."], "threats": ["..."]}}, '
            f'"evaluation": {{'
            f'"uniqueness_score": 0, "market_gap_score": 0, "feasibility_score": 0, '
            f'"innovation_score": 0, "early_stage_fit_score": 0, '
            f'"verdict": "...", "recommendations": ["..."]}}}}'
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
                "evaluation": {
                    "uniqueness_score": 0,
                    "market_gap_score": 0,
                    "feasibility_score": 0,
                    "innovation_score": 0,
                    "early_stage_fit_score": 0,
                    "verdict": "Could not parse analysis output.",
                    "recommendations": [],
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
            "evaluation": parsed.get("evaluation", {
                "uniqueness_score": 0,
                "market_gap_score": 0,
                "feasibility_score": 0,
                "innovation_score": 0,
                "early_stage_fit_score": 0,
                "verdict": "No evaluation data provided.",
                "recommendations": [],
            }),
            "sources": sources,
        }

        if self._cache:
            self._cache.set(cache_key, result, self._cache_ttl_seconds)

        return result
