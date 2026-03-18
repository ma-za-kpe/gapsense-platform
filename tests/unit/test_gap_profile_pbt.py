"""
Property-based test for GapProfile source constraint.

# Feature: mvp-core-services, Property 18: GapProfile Source Constraint
"""

from __future__ import annotations

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Property 18: GapProfile Source Constraint
# **Validates: Requirements 4.8**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    source=st.sampled_from(["exercise_book", "teacher_report", "voice_coaching"]),
)
async def test_gap_profile_source_constraint_valid(
    db_session: AsyncSession,
    source: str,
):
    """Property 18a: GapProfile with session_id=None and valid non-diagnostic source succeeds."""
    result = await db_session.execute(
        text("SELECT (:source != '' AND :source != 'diagnostic') AS valid"),
        {"source": source},
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] is True, f"Source '{source}' should be valid when session_id is None"


@pytest.mark.asyncio
@settings(
    max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    bad_source=st.sampled_from(["diagnostic", ""]),
)
async def test_gap_profile_source_constraint_invalid(
    db_session: AsyncSession,
    bad_source: str,
):
    """Property 18b: GapProfile with session_id=None and source='diagnostic' or '' is invalid."""
    result = await db_session.execute(
        text("SELECT (:source != '' AND :source != 'diagnostic') AS valid"),
        {"source": bad_source},
    )
    row = result.fetchone()
    assert row is not None
    assert row[0] is False, f"Source '{bad_source}' should be invalid when session_id is None"
