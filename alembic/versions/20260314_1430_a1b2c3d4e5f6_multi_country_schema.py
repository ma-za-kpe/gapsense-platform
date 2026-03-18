"""Multi-country schema: add country/subject/level to curriculum_nodes, source to gap_profiles

Revision ID: a1b2c3d4e5f6
Revises: 9053af4ce460
Create Date: 2026-03-14 14:30:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "9053af4ce460"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- CurriculumNode table changes ---
    op.add_column(
        "curriculum_nodes",
        sa.Column("country", sa.String(5), nullable=False, server_default="GH"),
    )
    op.add_column(
        "curriculum_nodes",
        sa.Column("subject", sa.String(50), nullable=False, server_default="mathematics"),
    )
    op.add_column(
        "curriculum_nodes",
        sa.Column("level", sa.String(20), nullable=False, server_default="primary"),
    )
    op.create_index(
        "idx_curriculum_nodes_country_subject_level_grade",
        "curriculum_nodes",
        ["country", "subject", "level", "grade"],
    )

    # --- GapProfile table changes ---
    op.alter_column(
        "gap_profiles",
        "session_id",
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=True,
    )
    op.add_column(
        "gap_profiles",
        sa.Column("source", sa.String(30), nullable=False, server_default="diagnostic"),
    )
    op.create_check_constraint(
        "ck_gap_profiles_source_when_no_session",
        "gap_profiles",
        "session_id IS NOT NULL OR (source != '' AND source != 'diagnostic')",
    )


def downgrade() -> None:
    # --- Reverse GapProfile changes ---
    op.drop_constraint("ck_gap_profiles_source_when_no_session", "gap_profiles", type_="check")
    op.drop_column("gap_profiles", "source")

    # Backfill any NULL session_ids with a placeholder UUID before making NOT NULL
    op.execute("UPDATE gap_profiles SET session_id = gen_random_uuid() WHERE session_id IS NULL")
    op.alter_column(
        "gap_profiles",
        "session_id",
        existing_type=sa.dialects.postgresql.UUID(),
        nullable=False,
    )

    # --- Reverse CurriculumNode changes ---
    op.drop_index("idx_curriculum_nodes_country_subject_level_grade", table_name="curriculum_nodes")
    op.drop_column("curriculum_nodes", "level")
    op.drop_column("curriculum_nodes", "subject")
    op.drop_column("curriculum_nodes", "country")
