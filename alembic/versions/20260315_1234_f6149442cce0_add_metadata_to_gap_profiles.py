"""add_metadata_to_gap_profiles

Revision ID: f6149442cce0
Revises: a1b2c3d4e5f6
Create Date: 2026-03-15 12:34:53.882445+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f6149442cce0'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add analysis_metadata JSONB column to gap_profiles
    op.add_column('gap_profiles', sa.Column('analysis_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Analysis metadata: errors, patterns, focus_areas, reasoning, etc.'))


def downgrade() -> None:
    # Remove analysis_metadata column
    op.drop_column('gap_profiles', 'analysis_metadata')
