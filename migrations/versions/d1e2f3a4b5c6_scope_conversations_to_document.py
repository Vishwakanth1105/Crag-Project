"""scope conversations to a document

Revision ID: d1e2f3a4b5c6
Revises: c7e8a1f2b3d4
Create Date: 2026-09-05 12:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d1e2f3a4b5c6"
down_revision: str | None = "c7e8a1f2b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("document_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        op.f("ix_conversations_document_id"), "conversations", ["document_id"]
    )
    op.create_foreign_key(
        "fk_conversations_document_id_documents",
        "conversations",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_conversations_document_id_documents", "conversations", type_="foreignkey"
    )
    op.drop_index(op.f("ix_conversations_document_id"), table_name="conversations")
    op.drop_column("conversations", "document_id")