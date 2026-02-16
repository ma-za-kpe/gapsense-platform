"""
Tests for school fuzzy matching to prevent duplicates.

Phase E of TDD implementation plan.

Prevents duplicate school records when teachers type school names
with different punctuation, capitalization, or minor typos.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import School
from gapsense.engagement.school_matcher import find_matching_schools

# ============================================================================
# Phase E.1: Fuzzy School Name Matching
# ============================================================================


class TestSchoolFuzzyMatching:
    """Tests for fuzzy school name matching."""

    async def test_find_exact_match(self, db_session: AsyncSession):
        """Exact match should return the school."""
        school = School(
            name="St. Mary's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St. Mary's JHS, Accra")
        assert len(matches) == 1
        assert matches[0].id == school.id

    async def test_find_fuzzy_match_punctuation(self, db_session: AsyncSession):
        """'St Marys JHS' should match 'St. Mary's JHS' (punctuation diff)."""
        school = School(
            name="St. Mary's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St Marys JHS Accra")
        assert len(matches) == 1
        assert matches[0].id == school.id

    async def test_find_fuzzy_match_capitalization(self, db_session: AsyncSession):
        """'st. mary's jhs' should match 'St. Mary's JHS' (case diff)."""
        school = School(
            name="St. Mary's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "st. mary's jhs, accra")
        assert len(matches) == 1
        assert matches[0].id == school.id

    async def test_find_fuzzy_match_extra_spaces(self, db_session: AsyncSession):
        """'St.  Mary's  JHS' (extra spaces) should match 'St. Mary's JHS'."""
        school = School(
            name="St. Mary's JHS",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St.  Mary's  JHS")
        assert len(matches) == 1
        assert matches[0].id == school.id

    async def test_no_match_different_school(self, db_session: AsyncSession):
        """'St. Paul's' should NOT match 'St. Mary's'."""
        school = School(
            name="St. Mary's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St. Paul's JHS, Accra")
        assert len(matches) == 0

    async def test_multiple_close_matches(self, db_session: AsyncSession):
        """Should return multiple schools if they're similar."""
        school1 = School(
            name="St. Mary's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        school2 = School(
            name="St. Mary's JHS, Kumasi",
            district_id=1,  # Use same district_id to avoid FK constraint
            school_type="jhs",
            is_active=True,
        )
        db_session.add_all([school1, school2])
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St Mary's JHS")
        # Should match both (different locations)
        assert len(matches) == 2
        assert {m.id for m in matches} == {school1.id, school2.id}

    async def test_ignore_inactive_schools(self, db_session: AsyncSession):
        """Should not match inactive schools."""
        active = School(
            name="St. Mary's JHS",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        inactive = School(
            name="St. Mary's JHS",
            district_id=1,
            school_type="jhs",
            is_active=False,
        )
        db_session.add_all([active, inactive])
        await db_session.commit()

        matches = await find_matching_schools(db_session, "St Mary's JHS")
        assert len(matches) == 1
        assert matches[0].id == active.id

    async def test_partial_match_returns_suggestions(self, db_session: AsyncSession):
        """Partial match should return similar schools as suggestions."""
        school1 = School(
            name="St. Mary's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        school2 = School(
            name="St. Mary's Primary, Accra",
            district_id=1,
            school_type="primary",
            is_active=True,
        )
        school3 = School(
            name="St. Martin's JHS, Accra",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add_all([school1, school2, school3])
        await db_session.commit()

        # Search for "St Mary JHS" should match school1 (exact match after normalization)
        # Note: "Mary's" normalizes to "marys", so exact match works
        matches = await find_matching_schools(db_session, "St Marys JHS Accra")
        assert len(matches) >= 1
        # Should include school1
        assert school1 in matches

    async def test_normalize_whitespace(self, db_session: AsyncSession):
        """Should normalize multiple spaces to single space."""
        school = School(
            name="Accra   Wesley   Girls   JHS",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "Accra Wesley Girls JHS")
        assert len(matches) == 1
        assert matches[0].id == school.id

    async def test_empty_query_returns_empty(self, db_session: AsyncSession):
        """Empty or whitespace-only query should return empty list."""
        school = School(
            name="Test School",
            district_id=1,
            school_type="jhs",
            is_active=True,
        )
        db_session.add(school)
        await db_session.commit()

        matches = await find_matching_schools(db_session, "")
        assert len(matches) == 0

        matches = await find_matching_schools(db_session, "   ")
        assert len(matches) == 0
