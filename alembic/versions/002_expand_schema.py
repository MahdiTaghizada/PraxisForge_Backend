"""Add members, comments tables; task priority/assignee/tags; file size/mime

Revision ID: 002_expand_schema
Revises: 001_initial_schema
Create Date: 2026-03-06

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_expand_schema"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # === NEW COLUMNS ON TASKS TABLE ===
    op.add_column("tasks", sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("tasks", sa.Column("priority", sa.String(50), server_default="medium", nullable=False))
    op.add_column("tasks", sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=True))

    # === NEW COLUMNS ON FILES TABLE ===
    op.add_column("files", sa.Column("size_bytes", sa.Integer(), server_default="0", nullable=False))
    op.add_column("files", sa.Column("mime_type", sa.String(255), server_default="", nullable=False))

    # === PROJECT MEMBERS TABLE ===
    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(50), server_default="member"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # === COMMENTS TABLE ===
    op.create_table(
        "comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("author_id", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("comments")
    op.drop_table("project_members")
    op.drop_column("files", "mime_type")
    op.drop_column("files", "size_bytes")
    op.drop_column("tasks", "tags")
    op.drop_column("tasks", "priority")
    op.drop_column("tasks", "assignee_id")
