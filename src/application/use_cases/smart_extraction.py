"""Background task: extract structured insights from chat interactions.

Runs asynchronously after every chat response to pull out:
- Technical decisions (database, tech stack, architecture)
- Key players (developers, stakeholders)
- Milestones and deadlines
- Tasks to auto-create

Results are saved to both PostgreSQL (structured_facts, tasks tables)
and Qdrant (as 'fact' chunk_type for future RAG retrieval).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime

from src.application.interfaces.llm import LLMService
from src.application.interfaces.vector_store import VectorChunk, VectorStoreService
from src.domain.entities.models import StructuredFact, Task
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.task_repo import TaskRepository
from src.domain.value_objects.enums import FactCategory, ProjectMode

logger = logging.getLogger(__name__)

_MODE_EXTRACTION_HINTS: dict[str, str] = {
    ProjectMode.HACKATHON: (
        "This is a Hackathon project. Prioritise tasks achievable in under 4 hours. "
        "Focus on core demo features, ignore production concerns."
    ),
    ProjectMode.STARTUP: (
        "This is a Startup project. Bias toward small, iteratable deliverables "
        "with 1-2 week deadlines. Focus on MVP and market validation."
    ),
    ProjectMode.ENTERPRISE: (
        "This is an Enterprise project. Include review gates, sign-off steps, "
        "and compliance checkpoints in extracted tasks."
    ),
    ProjectMode.IDEA: (
        "This is an Idea-phase project. Extract research and discovery tasks "
        "(user interviews, market sizing, feasibility spikes) rather than implementation work."
    ),
}

_EXTRACTION_PROMPT = """\
You are an expert project analyst. Given the following conversation snippet, \
extract ALL structured insights.

{mode_hint}

CONVERSATION:
{conversation}

Return ONLY valid JSON in this exact format (no markdown fences):
{{
  "technical_decisions": ["decision 1", "decision 2"],
  "key_players": ["person/role 1"],
  "milestones": ["milestone 1"],
  "deadlines": [{{"task": "...", "deadline": "YYYY-MM-DD"}}],
  "tasks": [{{"title": "...", "description": "..."}}]
}}

If a category has no items, return an empty list. Do not invent information \
that is not clearly stated or implied in the conversation.
"""


class SmartExtractionUseCase:
    def __init__(
        self,
        llm: LLMService,
        vector_store: VectorStoreService,
        fact_repo: FactRepository,
        task_repo: TaskRepository,
    ) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._fact_repo = fact_repo
        self._task_repo = task_repo

    async def execute(
        self,
        project_id: uuid.UUID,
        conversation_snippet: str,
        source_message_id: uuid.UUID | None = None,
        project_mode: ProjectMode | str = ProjectMode.STARTUP,
    ) -> None:
        """Extract facts and tasks from a conversation snippet."""

        mode_hint = _MODE_EXTRACTION_HINTS.get(
            str(project_mode), _MODE_EXTRACTION_HINTS[ProjectMode.STARTUP]
        )
        prompt = _EXTRACTION_PROMPT.format(
            conversation=conversation_snippet, mode_hint=mode_hint
        )
        raw = await self._llm.generate(prompt=prompt)

        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            data = json.loads(cleaned.strip())
        except (json.JSONDecodeError, IndexError):
            logger.warning("Extraction LLM returned unparseable JSON: %s", raw[:200])
            return

        vector_chunks: list[VectorChunk] = []

        # ── Technical decisions ───────────────────────────
        for decision in data.get("technical_decisions", []):
            if not decision:
                continue
            fact = StructuredFact(
                project_id=project_id,
                category=FactCategory.TECHNICAL_DECISION,
                content=decision,
                source_message_id=source_message_id,
            )
            await self._fact_repo.create(fact)
            vector_chunks.append(
                VectorChunk(
                    text=decision,
                    project_id=project_id,
                    chunk_type="fact",
                    metadata={"category": FactCategory.TECHNICAL_DECISION},
                )
            )

        # ── Key players ───────────────────────────────────
        for player in data.get("key_players", []):
            if not player:
                continue
            fact = StructuredFact(
                project_id=project_id,
                category=FactCategory.KEY_PLAYER,
                content=player,
                source_message_id=source_message_id,
            )
            await self._fact_repo.create(fact)
            vector_chunks.append(
                VectorChunk(
                    text=player,
                    project_id=project_id,
                    chunk_type="fact",
                    metadata={"category": FactCategory.KEY_PLAYER},
                )
            )

        # ── Milestones ────────────────────────────────────
        for milestone in data.get("milestones", []):
            if not milestone:
                continue
            fact = StructuredFact(
                project_id=project_id,
                category=FactCategory.MILESTONE,
                content=milestone,
                source_message_id=source_message_id,
            )
            await self._fact_repo.create(fact)
            vector_chunks.append(
                VectorChunk(
                    text=milestone,
                    project_id=project_id,
                    chunk_type="fact",
                    metadata={"category": FactCategory.MILESTONE},
                )
            )

        # ── Deadlines → Facts + Tasks ─────────────────────
        for dl in data.get("deadlines", []):
            if not isinstance(dl, dict):
                continue
            task_name = dl.get("task", "")
            deadline_str = dl.get("deadline", "")
            if not task_name:
                continue

            content = f"{task_name} — due {deadline_str}" if deadline_str else task_name
            fact = StructuredFact(
                project_id=project_id,
                category=FactCategory.DEADLINE,
                content=content,
                source_message_id=source_message_id,
            )
            await self._fact_repo.create(fact)
            vector_chunks.append(
                VectorChunk(
                    text=content,
                    project_id=project_id,
                    chunk_type="fact",
                    metadata={"category": FactCategory.DEADLINE},
                )
            )

            # Auto-create task in Postgres
            deadline_dt = None
            if deadline_str:
                try:
                    deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
                except ValueError:
                    pass
            task = Task(
                project_id=project_id,
                title=task_name,
                description=f"Auto-extracted from chat: {content}",
                deadline=deadline_dt,
                created_by="ai",
            )
            await self._task_repo.create(task)

        # ── Standalone tasks (no deadline) ────────────────
        for t in data.get("tasks", []):
            if not isinstance(t, dict) or not t.get("title"):
                continue
            task = Task(
                project_id=project_id,
                title=t["title"],
                description=t.get("description", "Auto-extracted from chat"),
                created_by="ai",
            )
            await self._task_repo.create(task)

        # ── Upsert all fact vectors into Qdrant ──────────
        if vector_chunks:
            await self._vector_store.upsert_chunks(vector_chunks)
            logger.info(
                "Extracted %d facts for project %s", len(vector_chunks), project_id
            )
