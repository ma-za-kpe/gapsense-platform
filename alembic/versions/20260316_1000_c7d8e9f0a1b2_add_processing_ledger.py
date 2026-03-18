"""Add processing_ledger table for SQS message idempotency

Revision ID: c7d8e9f0a1b2
Revises: b6e696c45284
Create Date: 2026-03-16 10:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d8e9f0a1b2"  # pragma: allowlist secret
down_revision: str | None = "b6e696c45284"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "processing_ledger",
        sa.Column("id", sa.dialects.postgresql.UUID(), primary_key=True),
        sa.Column("sqs_message_id", sa.String(255), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default="processing", nullable=False),
        sa.Column("student_id", sa.dialects.postgresql.UUID(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW() + INTERVAL '48 hours'"),
            nullable=False,
        ),
        sa.UniqueConstraint("sqs_message_id", "task_type", name="uq_ledger_msg_task"),
    )
    op.create_index("idx_ledger_expires", "processing_ledger", ["expires_at"])


def downgrade() -> None:
    op.drop_index("idx_ledger_expires", table_name="processing_ledger")
    op.drop_table("processing_ledger")
