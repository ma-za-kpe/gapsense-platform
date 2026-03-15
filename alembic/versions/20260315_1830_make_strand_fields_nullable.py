"""Make strand_id and sub_strand_id nullable in curriculum_nodes

Revision ID: 5bc892a1d3e7
Revises: f6149442cce0
Create Date: 2026-03-15 18:30:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5bc892a1d3e7'
down_revision = 'f6149442cce0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make strand_id and sub_strand_id nullable to support non-math curriculum."""
    # Make columns nullable
    op.alter_column('curriculum_nodes', 'strand_id',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('curriculum_nodes', 'sub_strand_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    """Revert strand_id and sub_strand_id to not nullable."""
    # Note: This will fail if there are NULL values in these columns
    op.alter_column('curriculum_nodes', 'sub_strand_id',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('curriculum_nodes', 'strand_id',
               existing_type=sa.INTEGER(),
               nullable=False)
