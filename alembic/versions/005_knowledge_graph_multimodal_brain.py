"""add knowledge graph and document analysis tables

Revision ID: 005
Revises: 004
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Knowledge Entities ────────────────────────────────
    op.create_table(
        "knowledge_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("properties", postgresql.JSON, server_default="{}"),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_knowledge_entities_project_id", "knowledge_entities", ["project_id"])
    op.create_index("ix_knowledge_entities_entity_type", "knowledge_entities", ["entity_type"])

    # ── Knowledge Relationships ───────────────────────────
    op.create_table(
        "knowledge_relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_entity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_entities.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("relationship_type", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("confidence", sa.Float, server_default="1.0"),
        sa.Column("source_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_knowledge_relationships_project_id", "knowledge_relationships", ["project_id"])
    op.create_index("ix_knowledge_relationships_source_entity_id", "knowledge_relationships", ["source_entity_id"])
    op.create_index("ix_knowledge_relationships_target_entity_id", "knowledge_relationships", ["target_entity_id"])
    op.create_index("ix_knowledge_relationships_relationship_type", "knowledge_relationships", ["relationship_type"])

    # ── Document Analyses ─────────────────────────────────
    op.create_table(
        "document_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("files.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("extracted_text", sa.Text, server_default=""),
        sa.Column("ai_analysis", sa.Text, server_default=""),
        sa.Column("content_type", sa.String(100), server_default="document"),
        sa.Column("processing_status", sa.String(50), server_default="pending"),
        sa.Column("metadata_json", postgresql.JSON, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_document_analyses_file_id", "document_analyses", ["file_id"])
    op.create_index("ix_document_analyses_project_id", "document_analyses", ["project_id"])


def downgrade() -> None:
    op.drop_table("document_analyses")
    op.drop_table("knowledge_relationships")
    op.drop_table("knowledge_entities")
