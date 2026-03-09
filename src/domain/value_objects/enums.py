from enum import StrEnum


class ProjectMode(StrEnum):
    STARTUP = "startup"
    HACKATHON = "hackathon"
    ENTERPRISE = "enterprise"
    IDEA = "idea"


class FileStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class TaskStatus(StrEnum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class FactCategory(StrEnum):
    TECHNICAL_DECISION = "technical_decision"
    KEY_PLAYER = "key_player"
    MILESTONE = "milestone"
    DEADLINE = "deadline"
    ARCHITECTURE = "architecture"
    GENERAL = "general"


class MemberRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class EntityType(StrEnum):
    TECHNOLOGY = "technology"
    ARCHITECTURE_COMPONENT = "architecture_component"
    PROJECT_GOAL = "project_goal"
    MODULE = "module"
    TASK = "task"
    PERSON = "person"
    SERVICE = "service"
    DATABASE = "database"
    CONCEPT = "concept"


class RelationshipType(StrEnum):
    USES = "uses"
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    IMPLEMENTS = "implements"
    CONNECTS_TO = "connects_to"
    PART_OF = "part_of"
    RELATED_TO = "related_to"


class DocumentProcessingStatus(StrEnum):
    PENDING = "pending"
    EXTRACTING_TEXT = "extracting_text"
    ANALYZING = "analyzing"
    EMBEDDING = "embedding"
    READY = "ready"
    FAILED = "failed"
