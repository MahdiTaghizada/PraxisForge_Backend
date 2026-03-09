"""Add task dependencies column; support IDEA project mode

Revision ID: 003_task_dependencies_idea_mode
Revises: 002_expand_schema
Create Date: 2026-03-08

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_task_dependencies_idea_mode"
down_revision: Union[str, None] = "002_expand_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Task dependencies: array of UUIDs referencing other task IDs
    op.add_column(
        "tasks",
        sa.Column("dependencies", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "dependencies")
