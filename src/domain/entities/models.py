from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from src.domain.value_objects.enums import (
    ChatRole,
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


@dataclass
class Project:
    """Core domain entity representing a user project."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    owner_id: str = ""
    name: str = ""
    description: str = ""
    mode: ProjectMode = ProjectMode.STARTUP
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class File:
    """Domain entity for an uploaded project file."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    filename: str = ""
    file_path: str = ""
    size_bytes: int = 0
    mime_type: str = ""
    status: FileStatus = FileStatus.PROCESSING
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Task:
    """Domain entity for a project task (auto-extracted or manual)."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    title: str = ""
    description: str = ""
    assignee_id: uuid.UUID | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    tags: list[str] = field(default_factory=list)
    dependencies: list[uuid.UUID] = field(default_factory=list)
    deadline: datetime | None = None
    status: TaskStatus = TaskStatus.TODO
    created_by: str = "user"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatMessage:
    """Domain entity for a single message in a chat history."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    role: ChatRole = ChatRole.USER
    content: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class StructuredFact:
    """Domain entity for an AI-extracted insight from chat interactions."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    category: FactCategory = FactCategory.GENERAL
    content: str = ""
    source_message_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ProjectMember:
    """Domain entity for project collaboration membership."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    user_id: str = ""
    email: str = ""
    role: MemberRole = MemberRole.MEMBER
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Comment:
    """Domain entity for a comment on a task."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    task_id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    author_id: str = ""
    content: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Knowledge Graph Entities ──────────────────────────────


@dataclass
class KnowledgeEntity:
    """A node in the project knowledge graph."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    name: str = ""
    entity_type: EntityType = EntityType.CONCEPT
    description: str = ""
    properties: dict = field(default_factory=dict)
    source_message_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KnowledgeRelationship:
    """An edge connecting two entities in the knowledge graph."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    source_entity_id: uuid.UUID = field(default_factory=uuid.uuid4)
    target_entity_id: uuid.UUID = field(default_factory=uuid.uuid4)
    relationship_type: RelationshipType = RelationshipType.RELATED_TO
    description: str = ""
    confidence: float = 1.0
    source_message_id: uuid.UUID | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)


# ── Multimodal Document Processing ───────────────────────


@dataclass
class DocumentAnalysis:
    """Result of multimodal analysis on an uploaded file."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    file_id: uuid.UUID = field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = field(default_factory=uuid.uuid4)
    extracted_text: str = ""
    ai_analysis: str = ""
    content_type: str = ""  # "image", "pdf", "diagram", "document"
    processing_status: DocumentProcessingStatus = DocumentProcessingStatus.PENDING
    metadata: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
