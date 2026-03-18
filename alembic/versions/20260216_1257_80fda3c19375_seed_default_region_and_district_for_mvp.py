"""Seed default region and district for MVP

Revision ID: 80fda3c19375
Revises: 9308455ddbbd
Create Date: 2026-02-16 12:57:58.288331+00:00

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80fda3c19375"  # pragma: allowlist secret
down_revision: str | None = "9308455ddbbd"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Seed default region and district for MVP teacher onboarding.

    This fixes Issue #1: Hardcoded district_id=1 in teacher_flows.py
    Teachers need a default district when creating schools during onboarding.
    """
    # Insert default region (Greater Accra)
    op.execute(
        """
        INSERT INTO regions (id, name, code)
        VALUES (1, 'Greater Accra', 'GAR')
        ON CONFLICT (id) DO NOTHING;
        """
    )

    # Insert default district (Accra Metro)
    op.execute(
        """
        INSERT INTO districts (id, region_id, name, ges_district_code)
        VALUES (1, 1, 'Accra Metropolitan', 'GAR-AM-001')
        ON CONFLICT (id) DO NOTHING;
        """
    )


def downgrade() -> None:
    """Remove seeded data."""
    op.execute("DELETE FROM districts WHERE id = 1;")
    op.execute("DELETE FROM regions WHERE id = 1;")
