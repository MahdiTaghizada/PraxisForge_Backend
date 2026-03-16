"""Use case: generate a comprehensive project summary from all stored data."""

from __future__ import annotations

import json
import logging
from src.infrastructure.cache.in_memory_ttl_cache import InMemoryTTLCache

from src.application.interfaces.llm import LLMService
from src.domain.entities.models import Project, StructuredFact, Task
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.task_repo import TaskRepository
from src.domain.value_objects.enums import FactCategory

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """\
You are an expert project analyst. Given the following project data, generate a \
comprehensive project summary.

PROJECT: {project_name}
DESCRIPTION: {project_description}
MODE: {project_mode}

=== STORED PROJECT FACTS ===
{facts_text}

=== TASK OVERVIEW ===
{tasks_text}

=== RECENT CONVERSATIONS ===
{chat_text}

Generate a JSON response with exactly this structure:
{{
    "summary": "A comprehensive 3-5 paragraph summary of the project's current state, goals, and progress.",
    "architecture_overview": "A description of the technical architecture, tech stack decisions, and system design based on the stored facts.",
    "recommended_db_structure": "Based on the project's domain, recommend a database schema with key tables and relationships.",
    "key_insights": ["insight 1", "insight 2", "insight 3"]
}}

LANGUAGE RULE:
{language_instruction}

CRITICAL STYLE RULE:
- Be realistic and candid.
- Highlight concrete risks, weak assumptions, and missing decisions.
- Avoid generic motivational phrasing.

Base everything on the actual data provided. Do not invent information.
Return ONLY valid JSON (no markdown fences).
"""


def _contains_azerbaijani_chars(text: str) -> bool:
    lowered = text.lower()
    return any(ch in lowered for ch in "əğıöşüç")


def _looks_azerbaijani_text(text: str) -> bool:
    lowered = text.lower()
    az_markers = [
        " və ", " üçün ", " layihə", "məlumat", "xülasə", "deyil", "olaraq", "hansı",
    ]
    marker_hits = sum(1 for marker in az_markers if marker in lowered)
    return _contains_azerbaijani_chars(lowered) or marker_hits >= 2


class ProjectSummaryUseCase:
    def __init__(
        self,
        llm: LLMService,
        fact_repo: FactRepository,
        task_repo: TaskRepository,
        chat_repo: ChatRepository,
        cache: InMemoryTTLCache[dict] | None = None,
        cache_ttl_seconds: int = 120,
    ) -> None:
        self._llm = llm
        self._fact_repo = fact_repo
        self._task_repo = task_repo
        self._chat_repo = chat_repo
        self._cache = cache
        self._cache_ttl_seconds = cache_ttl_seconds

    async def execute(self, project: Project, force_refresh: bool = False) -> dict:
        """Generate a full project summary combining all stored data."""

        cache_key = f"summary:{project.id}"
        if self._cache and not force_refresh:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        # Gather all facts
        all_facts = await self._fact_repo.list_by_project(project.id)
        facts_by_category: dict[str, list[str]] = {}
        for f in all_facts:
            cat = str(f.category)
            facts_by_category.setdefault(cat, []).append(f.content)

        facts_text_parts: list[str] = []
        for cat, items in facts_by_category.items():
            facts_text_parts.append(f"\n[{cat.upper()}]")
            for item in items:
                facts_text_parts.append(f"  - {item}")
        facts_text = "\n".join(facts_text_parts) if facts_text_parts else "No facts extracted yet."

        # Gather tasks
        all_tasks = await self._task_repo.list_by_project(project.id)
        task_stats = {"total": len(all_tasks), "todo": 0, "in_progress": 0, "done": 0}
        tasks_text_parts: list[str] = []
        for t in all_tasks:
            status_str = str(t.status)
            if status_str == "todo":
                task_stats["todo"] += 1
            elif status_str == "in_progress":
                task_stats["in_progress"] += 1
            elif status_str == "done":
                task_stats["done"] += 1
            tasks_text_parts.append(
                f"- [{t.status}] {t.title} (priority: {t.priority})"
            )
        tasks_text = "\n".join(tasks_text_parts) if tasks_text_parts else "No tasks created yet."

        # Gather recent chat
        messages = await self._chat_repo.get_history(project.id, limit=20)
        chat_text = "\n".join(
            f"{m.role.upper()}: {m.content[:200]}" for m in messages[-10:]
        ) if messages else "No conversations yet."

        language_instruction = (
            "Respond in Azerbaijani because recent conversation appears to be in Azerbaijani."
            if _looks_azerbaijani_text(chat_text)
            else "Respond in English unless the conversation clearly requires another language."
        )

        # Generate summary via LLM
        prompt = _SUMMARY_PROMPT.format(
            project_name=project.name,
            project_description=project.description,
            project_mode=str(project.mode),
            facts_text=facts_text,
            tasks_text=tasks_text,
            chat_text=chat_text,
            language_instruction=language_instruction,
        )

        raw = await self._llm.generate(prompt=prompt)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            parsed = json.loads(cleaned.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Summary LLM returned unparseable JSON")
            parsed = {
                "summary": raw,
                "architecture_overview": "Strukturlaşdırılmış cavab parse edilə bilmədi.",
                "recommended_db_structure": "Strukturlaşdırılmış cavab parse edilə bilmədi.",
                "key_insights": [],
            }

        result = {
            "project_name": project.name,
            "project_mode": str(project.mode),
            "summary": parsed.get("summary", ""),
            "architecture_overview": parsed.get("architecture_overview", ""),
            "key_facts": all_facts,
            "recommended_db_structure": parsed.get("recommended_db_structure", ""),
            "key_insights": parsed.get("key_insights", []),
            "task_overview": task_stats,
        }

        if self._cache:
            self._cache.set(cache_key, result, self._cache_ttl_seconds)

        return result
