"""Make teacher school_id nullable for onboarding flow

Revision ID: 9053af4ce460
Revises: 7a3674609a3b
Create Date: 2026-02-16 21:02:44.425064+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9053af4ce460"  # pragma: allowlist secret
down_revision: str | None = "7a3674609a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make teacher.school_id nullable (set during onboarding via invitation code)
    op.alter_column(
        "teachers",
        "school_id",
        existing_type=sa.UUID(),
        nullable=True,
        comment="Set during onboarding via invitation code",
    )

    # Make teacher.first_name and last_name nullable (set during onboarding)
    op.alter_column("teachers", "first_name", existing_type=sa.VARCHAR(length=100), nullable=True)

    op.alter_column("teachers", "last_name", existing_type=sa.VARCHAR(length=100), nullable=True)


def downgrade() -> None:
    # Reverse changes - make fields NOT NULL again
    op.alter_column("teachers", "last_name", existing_type=sa.VARCHAR(length=100), nullable=False)

    op.alter_column("teachers", "first_name", existing_type=sa.VARCHAR(length=100), nullable=False)

    op.alter_column("teachers", "school_id", existing_type=sa.UUID(), nullable=False)
