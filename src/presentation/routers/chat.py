"""Chat router: RAG-powered conversational AI with background extraction and knowledge graph."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status

from src.application.dtos.schemas import (
    ChatMessageDTO,
    ChatRequestDTO,
    ChatResponseDTO,
)
from src.application.interfaces.llm import LLMService
from src.application.interfaces.vector_store import VectorStoreService
from src.application.prompts import get_system_prompt
from src.application.use_cases.knowledge_graph import KnowledgeGraphExtractionUseCase
from src.application.use_cases.project_brain import ProjectBrainUseCase
from src.application.use_cases.smart_extraction import SmartExtractionUseCase
from src.domain.entities.models import ChatMessage
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.value_objects.enums import ChatRole
from src.infrastructure.database.repositories import (
    PostgresDocumentAnalysisRepository,
    PostgresFactRepository,
    PostgresKnowledgeEntityRepository,
    PostgresKnowledgeRelationshipRepository,
    PostgresTaskRepository,
)
from src.infrastructure.database.session import async_session_factory
from src.presentation.dependencies.deps import (
    get_chat_repo,
    get_current_user_id,
    get_document_analysis_repo,
    get_entity_repo,
    get_extraction_llm,
    get_fact_repo,
    get_llm_service,
    get_project_repo,
    get_relationship_repo,
    get_task_repo,
    get_vector_store,
)

router = APIRouter(prefix="/projects/{project_id}/chat", tags=["Chat"])


async def _run_extraction(
    project_id: uuid.UUID,
    conversation_snippet: str,
    project_mode: str,
    llm: LLMService,
    vector_store: VectorStoreService,
) -> None:
    """Background task wrapper — creates its own DB session to avoid
    using the request-scoped session after the response is sent.
    Runs both smart extraction and knowledge graph extraction."""
    async with async_session_factory() as session:
        fact_repo = PostgresFactRepository(session)
        task_repo = PostgresTaskRepository(session)
        entity_repo = PostgresKnowledgeEntityRepository(session)
        relationship_repo = PostgresKnowledgeRelationshipRepository(session)

        # Smart extraction (facts + tasks)
        extraction = SmartExtractionUseCase(
            llm=llm,
            vector_store=vector_store,
            fact_repo=fact_repo,
            task_repo=task_repo,
        )
        await extraction.execute(
            project_id=project_id,
            conversation_snippet=conversation_snippet,
            project_mode=project_mode,
        )

        # Knowledge graph extraction (entities + relationships)
        graph_extraction = KnowledgeGraphExtractionUseCase(
            llm=llm,
            entity_repo=entity_repo,
            relationship_repo=relationship_repo,
        )
        await graph_extraction.extract_from_conversation(
            project_id=project_id,
            conversation_snippet=conversation_snippet,
        )


@router.post("/", response_model=ChatResponseDTO)
async def send_message(
    project_id: uuid.UUID,
    body: ChatRequestDTO,
    background_tasks: BackgroundTasks,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    llm: LLMService = Depends(get_llm_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    extraction_llm: LLMService = Depends(get_extraction_llm),
    fact_repo=Depends(get_fact_repo),
    task_repo=Depends(get_task_repo),
    entity_repo=Depends(get_entity_repo),
    relationship_repo=Depends(get_relationship_repo),
    analysis_repo=Depends(get_document_analysis_repo),
) -> ChatResponseDTO:
    # Verify project ownership
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Use Project Brain for context-rich responses
    brain = ProjectBrainUseCase(
        llm=llm,
        vector_store=vector_store,
        fact_repo=fact_repo,
        task_repo=task_repo,
        chat_repo=chat_repo,
        entity_repo=entity_repo,
        relationship_repo=relationship_repo,
        analysis_repo=analysis_repo,
    )

    system_prompt = get_system_prompt(project.mode)
    answer = await brain.chat_with_brain(
        project_id=project_id,
        project_name=project.name,
        project_description=project.description,
        project_mode=project.mode,
        user_message=body.message,
        system_prompt=system_prompt,
    )

    # Persist both messages
    user_msg = ChatMessage(project_id=project_id, role=ChatRole.USER, content=body.message)
    assistant_msg = ChatMessage(project_id=project_id, role=ChatRole.ASSISTANT, content=answer)
    await chat_repo.add_message(user_msg)
    await chat_repo.add_message(assistant_msg)

    history = await chat_repo.get_history(project_id, limit=50)

    # Schedule background extraction (uses its own DB session)
    snippet = f"USER: {body.message}\nASSISTANT: {answer}"
    background_tasks.add_task(
        _run_extraction,
        project_id=project_id,
        conversation_snippet=snippet,
        project_mode=project.mode,
        llm=extraction_llm,
        vector_store=vector_store,
    )

    return ChatResponseDTO(
        answer=answer,
        history=[
            ChatMessageDTO(
                role=m.role, content=m.content, created_at=m.created_at
            )
            for m in history
        ],
    )


@router.get("/history", response_model=list[ChatMessageDTO])
async def get_chat_history(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
) -> list[ChatMessageDTO]:
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    messages = await chat_repo.get_history(project_id, limit=100)
    return [
        ChatMessageDTO(role=m.role, content=m.content, created_at=m.created_at)
        for m in messages
    ]


@router.delete("/history", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
async def clear_chat_history(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
):
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    await chat_repo.clear_history(project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


