"""
TDD Tests for Diagnostic Session Trigger

Tests that diagnostic sessions are automatically created after parent onboarding
when diagnostic consent is given.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from gapsense.core.models import DiagnosticSession, Parent, Student
from gapsense.engagement.flow_executor import FlowExecutor


@pytest.mark.asyncio
class TestDiagnosticSessionTrigger:
    """Tests for automatic diagnostic session creation after onboarding."""

    async def test_creates_diagnostic_session_when_consent_given(self, db_session):
        """Create diagnostic session after onboarding if parent gave consent."""
        # Setup: Create parent and student (simulate completed onboarding)
        from gapsense.core.models import District, Region, School

        region = Region(name="Greater Accra", code="GAR")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        parent = Parent(
            phone="+233244123456",
            diagnostic_consent=True,  # KEY: Parent consented
            diagnostic_consent_at=datetime.now(UTC),
            preferred_language="en",
            onboarded_at=None,  # Not yet onboarded
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Kwame",
            current_grade="B5",
            age=10,
            home_language="en",
            school_id=school.id,
        )
        db_session.add(student)
        await db_session.flush()

        # Simulate onboarding completion with diagnostic consent
        student.primary_parent_id = parent.id
        parent.onboarded_at = datetime.now(UTC)
        await db_session.commit()

        # Act: Trigger diagnostic session creation (via FlowExecutor or dedicated function)
        executor = FlowExecutor(db=db_session)
        await executor._create_diagnostic_session_if_consented(parent, student)

        # Assert: Diagnostic session was created
        stmt = select(DiagnosticSession).where(DiagnosticSession.student_id == student.id)
        result = await db_session.execute(stmt)
        session = result.scalar_one_or_none()

        assert session is not None
        assert session.student_id == student.id
        assert session.entry_grade == "B5"
        assert session.initiated_by == "parent"
        assert session.channel == "whatsapp"
        assert session.status == "pending"

    async def test_no_session_when_consent_declined(self, db_session):
        """Don't create diagnostic session if parent declined consent."""
        from gapsense.core.models import District, Region, School

        region = Region(name="Greater Accra", code="GAR")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        parent = Parent(
            phone="+233244999999",
            diagnostic_consent=False,  # KEY: Parent declined
            preferred_language="en",
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Ama",
            current_grade="B4",
            school_id=school.id,
            primary_parent_id=parent.id,
        )
        db_session.add(student)
        await db_session.commit()

        # Act: Try to trigger diagnostic session creation
        executor = FlowExecutor(db=db_session)
        await executor._create_diagnostic_session_if_consented(parent, student)

        # Assert: No diagnostic session created
        stmt = select(DiagnosticSession).where(DiagnosticSession.student_id == student.id)
        result = await db_session.execute(stmt)
        session = result.scalar_one_or_none()

        assert session is None

    async def test_no_duplicate_sessions_created(self, db_session):
        """Don't create duplicate diagnostic sessions for same student."""
        from gapsense.core.models import District, Region, School

        region = Region(name="Greater Accra", code="GAR")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        parent = Parent(
            phone="+233244777777",
            diagnostic_consent=True,
            preferred_language="en",
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Kofi",
            current_grade="B3",
            school_id=school.id,
            primary_parent_id=parent.id,
        )
        db_session.add(student)
        await db_session.flush()

        # Pre-create an existing pending session
        existing_session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            channel="whatsapp",
            status="pending",
        )
        db_session.add(existing_session)
        await db_session.commit()

        # Act: Try to trigger diagnostic session creation again
        executor = FlowExecutor(db=db_session)
        await executor._create_diagnostic_session_if_consented(parent, student)

        # Assert: Still only one session exists
        stmt = select(DiagnosticSession).where(DiagnosticSession.student_id == student.id)
        result = await db_session.execute(stmt)
        sessions = result.scalars().all()

        assert len(sessions) == 1
        assert sessions[0].id == existing_session.id
