"""Use case: AI Project Brain — unified context orchestration layer.

Builds a comprehensive project context from all available data sources
before any AI response is generated. This ensures the LLM always has
the full picture of the project.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field

from src.application.interfaces.llm import LLMService
from src.application.interfaces.vector_store import VectorStoreService
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.knowledge_graph_repo import (
    KnowledgeEntityRepository,
    KnowledgeRelationshipRepository,
)
from src.domain.repositories.task_repo import TaskRepository

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Structured project context assembled by the Project Brain."""

    project_name: str = ""
    project_description: str = ""
    project_mode: str = ""

    # Gathered data
    facts_by_category: dict[str, list[str]] = field(default_factory=dict)
    tech_stack: list[str] = field(default_factory=list)
    architecture_components: list[str] = field(default_factory=list)
    tasks_summary: str = ""
    task_count: dict[str, int] = field(default_factory=dict)
    knowledge_graph_summary: str = ""
    document_summaries: list[str] = field(default_factory=list)
    recent_chat: str = ""
    vector_context: str = ""

    def to_prompt_section(self) -> str:
        """Render the full context into a prompt-ready text block."""
        sections: list[str] = []

        sections.append(f"PROJECT: {self.project_name}")
        sections.append(f"DESCRIPTION: {self.project_description}")
        sections.append(f"MODE: {self.project_mode}")

        if self.tech_stack:
            sections.append(f"\n=== TECH STACK ===\n" + ", ".join(self.tech_stack))

        if self.architecture_components:
            sections.append(
                "\n=== ARCHITECTURE COMPONENTS ===\n"
                + "\n".join(f"  • {c}" for c in self.architecture_components)
            )

        if self.facts_by_category:
            sections.append("\n=== PROJECT FACTS ===")
            for category, facts in self.facts_by_category.items():
                sections.append(f"\n[{category.upper()}]")
                for fact in facts[:10]:  # Limit per category
                    sections.append(f"  - {fact}")

        if self.tasks_summary:
            sections.append(f"\n=== TASKS & DEADLINES ===\n{self.tasks_summary}")

        if self.knowledge_graph_summary:
            sections.append(
                f"\n=== KNOWLEDGE GRAPH ===\n{self.knowledge_graph_summary}"
            )

        if self.document_summaries:
            sections.append("\n=== IMPORTANT DOCUMENTS ===")
            for doc in self.document_summaries[:5]:
                sections.append(f"  • {doc}")

        if self.vector_context:
            sections.append(f"\n=== RELEVANT CONTEXT (VECTOR SEARCH) ===\n{self.vector_context}")

        if self.recent_chat:
            sections.append(f"\n=== RECENT CONVERSATION ===\n{self.recent_chat}")

        return "\n".join(sections)


class ProjectBrainUseCase:
    """The AI Project Brain — orchestrates all data sources into unified context."""

    def __init__(
        self,
        llm: LLMService,
        vector_store: VectorStoreService,
        fact_repo: FactRepository,
        task_repo: TaskRepository,
        chat_repo: ChatRepository,
        entity_repo: KnowledgeEntityRepository,
        relationship_repo: KnowledgeRelationshipRepository,
        analysis_repo: DocumentAnalysisRepository,
    ) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._fact_repo = fact_repo
        self._task_repo = task_repo
        self._chat_repo = chat_repo
        self._entity_repo = entity_repo
        self._relationship_repo = relationship_repo
        self._analysis_repo = analysis_repo

    async def build_context(
        self,
        project_id: uuid.UUID,
        project_name: str,
        project_description: str,
        project_mode: str,
        user_query: str = "",
    ) -> ProjectContext:
        """Assemble a comprehensive project context from all data sources."""

        ctx = ProjectContext(
            project_name=project_name,
            project_description=project_description,
            project_mode=project_mode,
        )

        # 1. Gather all structured facts
        all_facts = await self._fact_repo.list_by_project(project_id)
        for fact in all_facts:
            cat = str(fact.category)
            ctx.facts_by_category.setdefault(cat, []).append(fact.content)

        # Extract tech stack and architecture from facts
        ctx.tech_stack = [
            f.content
            for f in all_facts
            if str(f.category) == "technical_decision"
        ][:15]
        ctx.architecture_components = [
            f.content
            for f in all_facts
            if str(f.category) == "architecture"
        ][:10]

        # 2. Gather tasks
        all_tasks = await self._task_repo.list_by_project(project_id)
        task_stats = {"total": len(all_tasks), "todo": 0, "in_progress": 0, "done": 0}
        task_lines: list[str] = []
        for t in all_tasks:
            status_str = str(t.status)
            task_stats[status_str] = task_stats.get(status_str, 0) + 1
            deadline_str = f" (due: {t.deadline.strftime('%Y-%m-%d')})" if t.deadline else ""
            task_lines.append(f"[{t.status}] {t.title} — priority: {t.priority}{deadline_str}")

        ctx.task_count = task_stats
        ctx.tasks_summary = "\n".join(task_lines[:20]) if task_lines else "No tasks yet."

        # 3. Gather knowledge graph
        entities = await self._entity_repo.list_by_project(project_id)
        relationships = await self._relationship_repo.list_by_project(project_id)

        if entities:
            entity_map = {e.id: e.name for e in entities}
            graph_lines: list[str] = []
            for e in entities[:20]:
                graph_lines.append(f"• {e.name} ({e.entity_type})")
            for r in relationships[:30]:
                src = entity_map.get(r.source_entity_id, "?")
                tgt = entity_map.get(r.target_entity_id, "?")
                graph_lines.append(f"  {src} → {r.relationship_type} → {tgt}")
            ctx.knowledge_graph_summary = "\n".join(graph_lines)

        # 4. Gather document analyses
        analyses = await self._analysis_repo.list_by_project(project_id)
        for a in analyses[:5]:
            if a.ai_analysis:
                ctx.document_summaries.append(
                    f"{a.content_type}: {a.ai_analysis[:300]}"
                )

        # 5. Recent chat history
        messages = await self._chat_repo.get_history(project_id, limit=20)
        if messages:
            ctx.recent_chat = "\n".join(
                f"{m.role.upper()}: {m.content[:200]}" for m in messages[-10:]
            )

        # 6. Vector search if query is provided
        if user_query:
            doc_results = await self._vector_store.search(
                query=user_query, project_id=project_id, limit=5, chunk_type="document"
            )
            fact_results = await self._vector_store.search(
                query=user_query, project_id=project_id, limit=3, chunk_type="fact"
            )
            analysis_results = await self._vector_store.search(
                query=user_query, project_id=project_id, limit=2, chunk_type="document_analysis"
            )

            context_parts: list[str] = []
            for i, r in enumerate(doc_results, 1):
                context_parts.append(f"[Doc {i} | score={r.score:.2f}] {r.text}")
            for i, r in enumerate(fact_results, 1):
                cat = r.metadata.get("extra", {}).get("category", "general")
                context_parts.append(f"[Fact {i} | {cat}] {r.text}")
            for i, r in enumerate(analysis_results, 1):
                context_parts.append(f"[Analysis {i}] {r.text}")
            ctx.vector_context = "\n".join(context_parts)

        return ctx

    async def chat_with_brain(
        self,
        project_id: uuid.UUID,
        project_name: str,
        project_description: str,
        project_mode: str,
        user_message: str,
        system_prompt: str,
    ) -> str:
        """Generate an AI response using the full Project Brain context."""

        context = await self.build_context(
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            project_mode=project_mode,
            user_query=user_message,
        )

        enhanced_prompt = (
            f"{context.to_prompt_section()}\n\n"
            f"--- USER MESSAGE ---\n{user_message}\n\n"
            "Respond helpfully using ALL the context above. "
            "Reference specific facts, tasks, entities, and documents when relevant. "
            "If the context does not contain the answer, say so honestly."
        )

        return await self._llm.generate(prompt=enhanced_prompt, system=system_prompt)

    async def get_brain_summary(
        self,
        project_id: uuid.UUID,
        project_name: str,
        project_description: str,
        project_mode: str,
    ) -> dict:
        """Return a structured summary of everything the Project Brain knows."""

        context = await self.build_context(
            project_id=project_id,
            project_name=project_name,
            project_description=project_description,
            project_mode=project_mode,
        )

        return {
            "project_name": context.project_name,
            "project_mode": context.project_mode,
            "tech_stack": context.tech_stack,
            "architecture_components": context.architecture_components,
            "facts_count": sum(len(v) for v in context.facts_by_category.values()),
            "facts_by_category": {
                k: len(v) for k, v in context.facts_by_category.items()
            },
            "task_stats": context.task_count,
            "has_knowledge_graph": bool(context.knowledge_graph_summary),
            "documents_analyzed": len(context.document_summaries),
        }
