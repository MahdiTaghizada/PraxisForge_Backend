"""add created_by to tasks

Revision ID: 004
Revises: 003_task_dependencies_idea_mode
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "004"
down_revision = "003_task_dependencies_idea_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("created_by", sa.String(50), server_default="user", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("tasks", "created_by")
