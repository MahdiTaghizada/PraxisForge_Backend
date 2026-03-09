from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from src.domain.value_objects.enums import (
    DocumentProcessingStatus,
    EntityType,
    FactCategory,
    FileStatus,
    MemberRole,
    ProjectMode,
    RelationshipType,
    TaskPriority,
    TaskStatus,
)


# ── User DTOs ─────────────────────────────────────────────


class UserResponseDTO(BaseModel):
    id: str
    email: str | None = None


# ── Project DTOs ──────────────────────────────────────────


class ProjectCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    mode: ProjectMode = ProjectMode.STARTUP


class ProjectUpdateDTO(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    mode: ProjectMode | None = None


class ProjectResponseDTO(BaseModel):
    id: uuid.UUID
    owner_id: str
    name: str
    description: str
    mode: ProjectMode
    created_at: datetime


# ── Project Member DTOs ───────────────────────────────────


class ProjectMemberCreateDTO(BaseModel):
    email: EmailStr
    role: MemberRole = MemberRole.MEMBER


class ProjectMemberDTO(BaseModel):
    user_id: str
    email: str
    role: MemberRole


# ── File DTOs ─────────────────────────────────────────────


class FileResponseDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    size_bytes: int
    mime_type: str
    status: FileStatus
    created_at: datetime


# ── Task DTOs ─────────────────────────────────────────────


class TaskCreateDTO(BaseModel):
    title: str = Field(..., min_length=1, max_length=512)
    description: str = ""
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: list[str] = Field(default_factory=list)
    dependencies: list[uuid.UUID] = Field(default_factory=list)
    deadline: datetime | None = None


class TaskUpdateDTO(BaseModel):
    title: str | None = None
    description: str | None = None
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority | None = None
    tags: list[str] | None = None
    dependencies: list[uuid.UUID] | None = None
    deadline: datetime | None = None
    status: TaskStatus | None = None


class TaskResponseDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str
    assignee_id: uuid.UUID | None
    priority: TaskPriority
    tags: list[str]
    dependencies: list[uuid.UUID]
    deadline: datetime | None
    status: TaskStatus
    created_by: str = "user"
    created_at: datetime


# ── Comment DTOs ──────────────────────────────────────────


class CommentCreateDTO(BaseModel):
    content: str = Field(..., min_length=1)


class CommentUpdateDTO(BaseModel):
    content: str = Field(..., min_length=1)


class CommentResponseDTO(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    project_id: uuid.UUID
    author_id: str
    content: str
    created_at: datetime


# ── Chat DTOs ─────────────────────────────────────────────


class ChatRequestDTO(BaseModel):
    message: str = Field(..., min_length=1)


class ChatMessageDTO(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatResponseDTO(BaseModel):
    answer: str
    history: list[ChatMessageDTO]


# ── Search / SWOT DTOs ───────────────────────────────────


class SearchRequestDTO(BaseModel):
    query: str | None = None  # if None, auto-generate from project description


class SWOTAnalysis(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    opportunities: list[str]
    threats: list[str]


class SearchResponseDTO(BaseModel):
    summary: str
    competitors: list[str]
    swot: SWOTAnalysis
    sources: list[str]


# ── Structured Fact DTOs ─────────────────────────────────


class FactResponseDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    category: FactCategory
    content: str
    source_message_id: uuid.UUID | None
    created_at: datetime


class FactUpdateDTO(BaseModel):
    content: str = Field(..., min_length=1)
    category: FactCategory | None = None


class InsightsResponseDTO(BaseModel):
    technical_decisions: list[FactResponseDTO]
    key_players: list[FactResponseDTO]
    milestones: list[FactResponseDTO]
    deadlines: list[FactResponseDTO]


# ── Project Summary DTOs ─────────────────────────────────


class ProjectSummaryResponseDTO(BaseModel):
    project_name: str
    project_mode: str
    summary: str
    architecture_overview: str
    key_facts: list[FactResponseDTO]
    recommended_db_structure: str
    key_insights: list[str]
    task_overview: dict


# ── Knowledge Graph DTOs ──────────────────────────────────


class KnowledgeEntityCreateDTO(BaseModel):
    name: str = Field(..., min_length=1, max_length=512)
    entity_type: EntityType = EntityType.CONCEPT
    description: str = ""
    properties: dict = Field(default_factory=dict)


class KnowledgeEntityResponseDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    entity_type: EntityType
    description: str
    properties: dict
    created_at: datetime


class KnowledgeRelationshipCreateDTO(BaseModel):
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: RelationshipType = RelationshipType.RELATED_TO
    description: str = ""


class KnowledgeRelationshipResponseDTO(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: RelationshipType
    description: str
    confidence: float
    created_at: datetime


class KnowledgeGraphResponseDTO(BaseModel):
    entities: list[KnowledgeEntityResponseDTO]
    relationships: list[KnowledgeRelationshipResponseDTO]


# ── Document Analysis DTOs ────────────────────────────────


class DocumentAnalysisResponseDTO(BaseModel):
    id: uuid.UUID
    file_id: uuid.UUID
    project_id: uuid.UUID
    extracted_text: str
    ai_analysis: str
    content_type: str
    processing_status: DocumentProcessingStatus
    metadata: dict
    created_at: datetime


# ── Project Brain DTOs ────────────────────────────────────


class BrainChatRequestDTO(BaseModel):
    message: str = Field(..., min_length=1)


class BrainSummaryResponseDTO(BaseModel):
    project_name: str
    project_mode: str
    tech_stack: list[str]
    architecture_components: list[str]
    facts_count: int
    facts_by_category: dict[str, int]
    task_stats: dict[str, int]
    has_knowledge_graph: bool
    documents_analyzed: int
