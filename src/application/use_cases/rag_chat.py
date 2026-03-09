"""Use case: RAG-powered contextual chat for a project."""

from __future__ import annotations

import uuid

from src.application.interfaces.llm import LLMService
from src.application.interfaces.vector_store import VectorStoreService
from src.application.prompts import get_system_prompt
from src.domain.entities.models import ChatMessage
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.value_objects.enums import ChatRole, ProjectMode


class RAGChatUseCase:
    def __init__(
        self,
        llm: LLMService,
        vector_store: VectorStoreService,
        chat_repo: ChatRepository,
    ) -> None:
        self._llm = llm
        self._vector_store = vector_store
        self._chat_repo = chat_repo

    async def execute(
        self,
        project_id: uuid.UUID,
        user_message: str,
        project_name: str,
        project_description: str,
        project_mode: ProjectMode | str,
    ) -> tuple[str, list[ChatMessage]]:
        """Run the full RAG pipeline: retrieve → augment → generate → persist."""

        # 1. Retrieve relevant context from Qdrant (documents + facts)
        doc_results = await self._vector_store.search(
            query=user_message, project_id=project_id, limit=5, chunk_type="document"
        )
        fact_results = await self._vector_store.search(
            query=user_message, project_id=project_id, limit=3, chunk_type="fact"
        )

        context_parts: list[str] = []
        if doc_results:
            context_parts.append("=== RELEVANT DOCUMENTS ===")
            for i, r in enumerate(doc_results, 1):
                context_parts.append(f"[Doc {i} | score={r.score:.2f}] {r.text}")

        if fact_results:
            context_parts.append("\n=== KNOWN PROJECT FACTS ===")
            for i, r in enumerate(fact_results, 1):
                cat = r.metadata.get("extra", {}).get("category", "general")
                context_parts.append(f"[Fact {i} | {cat}] {r.text}")

        rag_context = "\n".join(context_parts) if context_parts else "No prior context found."

        # 2. Fetch recent chat history
        history = await self._chat_repo.get_history(project_id, limit=20)
        history_text = "\n".join(
            f"{m.role.upper()}: {m.content}" for m in history[-10:]
        )

        # 3. Augment prompt
        system_prompt = get_system_prompt(project_mode)
        user_prompt = (
            f"PROJECT: {project_name}\n"
            f"DESCRIPTION: {project_description}\n\n"
            f"--- RETRIEVED CONTEXT ---\n{rag_context}\n\n"
            f"--- RECENT CONVERSATION ---\n{history_text}\n\n"
            f"--- USER MESSAGE ---\n{user_message}\n\n"
            "Respond helpfully using the context above. "
            "If the context does not contain the answer, say so honestly."
        )

        # 4. Generate
        answer = await self._llm.generate(prompt=user_prompt, system=system_prompt)

        # 5. Persist both messages
        user_msg = ChatMessage(
            project_id=project_id, role=ChatRole.USER, content=user_message
        )
        assistant_msg = ChatMessage(
            project_id=project_id, role=ChatRole.ASSISTANT, content=answer
        )
        await self._chat_repo.add_message(user_msg)
        saved_assistant = await self._chat_repo.add_message(assistant_msg)

        # 6. Return answer + updated history
        updated_history = await self._chat_repo.get_history(project_id, limit=50)
        return answer, updated_history
