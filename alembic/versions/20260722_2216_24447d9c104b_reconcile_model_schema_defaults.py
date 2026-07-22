"""Reconcile model schema defaults.

Revision ID: 24447d9c104b
Revises: f00f469d61b1
Create Date: 2026-07-22 22:16:31.499718+00:00

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "24447d9c104b"
down_revision: str | None = "f00f469d61b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add missing database defaults and normalize the severity index."""
    timestamp_columns = (
        ("curriculum_nodes", "created_at", "Creation timestamp (UTC)"),
        ("curriculum_nodes", "updated_at", "Last update timestamp (UTC)"),
        ("districts", "created_at", "Creation timestamp (UTC)"),
        ("districts", "updated_at", "Last update timestamp (UTC)"),
        ("parents", "created_at", "Creation timestamp (UTC)"),
        ("parents", "updated_at", "Last update timestamp (UTC)"),
        ("prompt_versions", "created_at", "Creation timestamp (UTC)"),
        ("prompt_versions", "updated_at", "Last update timestamp (UTC)"),
        ("schools", "created_at", "Creation timestamp (UTC)"),
        ("schools", "updated_at", "Last update timestamp (UTC)"),
        ("students", "created_at", "Creation timestamp (UTC)"),
        ("students", "updated_at", "Last update timestamp (UTC)"),
        ("teachers", "created_at", "Creation timestamp (UTC)"),
        ("teachers", "updated_at", "Last update timestamp (UTC)"),
    )
    for table_name, column_name, comment in timestamp_columns:
        op.alter_column(
            table_name,
            column_name,
            existing_type=postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("NOW()"),
            existing_comment=comment,
            existing_nullable=False,
        )

    op.drop_index(op.f("idx_curriculum_nodes_severity"), table_name="curriculum_nodes")
    op.create_index(
        "idx_curriculum_nodes_severity",
        "curriculum_nodes",
        ["severity"],
        unique=False,
    )


def downgrade() -> None:
    """Restore the previous defaults and descending index expression."""
    op.drop_index("idx_curriculum_nodes_severity", table_name="curriculum_nodes")
    op.create_index(
        op.f("idx_curriculum_nodes_severity"),
        "curriculum_nodes",
        [sa.literal_column("severity DESC")],
        unique=False,
    )

    timestamp_columns = (
        ("teachers", "updated_at", "Last update timestamp (UTC)"),
        ("teachers", "created_at", "Creation timestamp (UTC)"),
        ("students", "updated_at", "Last update timestamp (UTC)"),
        ("students", "created_at", "Creation timestamp (UTC)"),
        ("schools", "updated_at", "Last update timestamp (UTC)"),
        ("schools", "created_at", "Creation timestamp (UTC)"),
        ("prompt_versions", "updated_at", "Last update timestamp (UTC)"),
        ("prompt_versions", "created_at", "Creation timestamp (UTC)"),
        ("parents", "updated_at", "Last update timestamp (UTC)"),
        ("parents", "created_at", "Creation timestamp (UTC)"),
        ("districts", "updated_at", "Last update timestamp (UTC)"),
        ("districts", "created_at", "Creation timestamp (UTC)"),
        ("curriculum_nodes", "updated_at", "Last update timestamp (UTC)"),
        ("curriculum_nodes", "created_at", "Creation timestamp (UTC)"),
    )
    for table_name, column_name, comment in timestamp_columns:
        op.alter_column(
            table_name,
            column_name,
            existing_type=postgresql.TIMESTAMP(timezone=True),
            server_default=None,
            existing_comment=comment,
            existing_nullable=False,
        )
