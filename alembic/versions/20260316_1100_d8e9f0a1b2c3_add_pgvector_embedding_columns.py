"""Add pgvector extension and embedding columns to curriculum_indicators

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
Create Date: 2026-03-16 11:00:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"  # pragma: allowlist secret
down_revision: str | None = "c7d8e9f0a1b2"  # pragma: allowlist secret
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable pgvector extension and add embedding columns to curriculum_indicators.

    - Creates the vector extension if not already present
    - Adds embedding column (Vector(1536), nullable) for storing indicator embeddings
    - Adds embedding_model column (String(50), nullable) to track which model generated the embedding
    """
    # Enable pgvector extension (idempotent - succeeds if already exists)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column for storing vector embeddings
    op.add_column(
        "curriculum_indicators",
        sa.Column("embedding", Vector(1536), nullable=True),
    )

    # Add embedding_model column to track which model generated the embedding
    op.add_column(
        "curriculum_indicators",
        sa.Column("embedding_model", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    """Remove embedding columns from curriculum_indicators.

    Note: Does NOT drop the vector extension as other tables may depend on it.
    """
    op.drop_column("curriculum_indicators", "embedding_model")
    op.drop_column("curriculum_indicators", "embedding")
