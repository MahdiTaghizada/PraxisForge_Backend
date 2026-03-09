"""Project Brain router: unified AI orchestration layer."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from src.application.dtos.schemas import (
    BrainChatRequestDTO,
    BrainSummaryResponseDTO,
    ChatResponseDTO,
    ChatMessageDTO,
)
from src.application.interfaces.llm import LLMService
from src.application.interfaces.vector_store import VectorStoreService
from src.application.prompts import get_system_prompt
from src.application.use_cases.project_brain import ProjectBrainUseCase
from src.domain.entities.models import ChatMessage
from src.domain.repositories.chat_repo import ChatRepository
from src.domain.repositories.document_analysis_repo import DocumentAnalysisRepository
from src.domain.repositories.fact_repo import FactRepository
from src.domain.repositories.knowledge_graph_repo import (
    KnowledgeEntityRepository,
    KnowledgeRelationshipRepository,
)
from src.domain.repositories.project_repo import ProjectRepository
from src.domain.repositories.task_repo import TaskRepository
from src.domain.value_objects.enums import ChatRole
from src.presentation.dependencies.deps import (
    get_chat_repo,
    get_current_user_id,
    get_document_analysis_repo,
    get_entity_repo,
    get_fact_repo,
    get_llm_service,
    get_project_repo,
    get_relationship_repo,
    get_task_repo,
    get_vector_store,
)

router = APIRouter(prefix="/projects/{project_id}/brain", tags=["Project Brain"])


@router.post("/chat", response_model=ChatResponseDTO)
async def brain_chat(
    project_id: uuid.UUID,
    body: BrainChatRequestDTO,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    llm: LLMService = Depends(get_llm_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    fact_repo: FactRepository = Depends(get_fact_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
    relationship_repo: KnowledgeRelationshipRepository = Depends(get_relationship_repo),
    analysis_repo: DocumentAnalysisRepository = Depends(get_document_analysis_repo),
) -> ChatResponseDTO:
    """Chat using the full Project Brain context — combines all data sources."""
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

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
    return ChatResponseDTO(
        answer=answer,
        history=[
            ChatMessageDTO(role=m.role, content=m.content, created_at=m.created_at)
            for m in history
        ],
    )


@router.get("/summary", response_model=BrainSummaryResponseDTO)
async def brain_summary(
    project_id: uuid.UUID,
    owner_id: str = Depends(get_current_user_id),
    project_repo: ProjectRepository = Depends(get_project_repo),
    llm: LLMService = Depends(get_llm_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    fact_repo: FactRepository = Depends(get_fact_repo),
    task_repo: TaskRepository = Depends(get_task_repo),
    chat_repo: ChatRepository = Depends(get_chat_repo),
    entity_repo: KnowledgeEntityRepository = Depends(get_entity_repo),
    relationship_repo: KnowledgeRelationshipRepository = Depends(get_relationship_repo),
    analysis_repo: DocumentAnalysisRepository = Depends(get_document_analysis_repo),
) -> BrainSummaryResponseDTO:
    """Get everything the Project Brain knows about this project."""
    project = await project_repo.get_by_id(project_id, owner_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

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

    summary = await brain.get_brain_summary(
        project_id=project_id,
        project_name=project.name,
        project_description=project.description,
        project_mode=project.mode,
    )

    return BrainSummaryResponseDTO(**summary)
