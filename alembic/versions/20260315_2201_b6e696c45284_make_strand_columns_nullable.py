"""make_strand_columns_nullable

Revision ID: b6e696c45284
Revises: 5bc892a1d3e7
Create Date: 2026-03-15 22:01:47.269072+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6e696c45284'
down_revision: Union[str, None] = '5bc892a1d3e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make strand_id and sub_strand_id nullable to support English/Science curriculum."""
    # Make strand_id nullable
    op.alter_column('curriculum_nodes', 'strand_id',
                    existing_type=sa.Integer(),
                    nullable=True)

    # Make sub_strand_id nullable
    op.alter_column('curriculum_nodes', 'sub_strand_id',
                    existing_type=sa.Integer(),
                    nullable=True)


def downgrade() -> None:
    """Revert strand columns to NOT NULL."""
    # Make sub_strand_id NOT NULL again
    op.alter_column('curriculum_nodes', 'sub_strand_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # Make strand_id NOT NULL again
    op.alter_column('curriculum_nodes', 'strand_id',
                    existing_type=sa.Integer(),
                    nullable=False)
