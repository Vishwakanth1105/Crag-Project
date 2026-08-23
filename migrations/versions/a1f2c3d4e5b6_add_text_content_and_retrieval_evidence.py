"""add document text_content and message retrieval_evidence

Revision ID: a1f2c3d4e5b6
Revises: 8ff8af7ca880
Create Date: 2026-08-22 20:10:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1f2c3d4e5b6"
down_revision: str | None = "8ff8af7ca880"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("text_content", sa.Text(), nullable=True))
    op.add_column(
        "messages",
        sa.Column(
            "retrieval_evidence", sa.JSON(), nullable=False, server_default=sa.text("('[]')")
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "retrieval_evidence")
    op.drop_column("documents", "text_content")
