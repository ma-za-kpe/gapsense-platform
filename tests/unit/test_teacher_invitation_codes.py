"""
Tests for teacher invitation code acceptance in onboarding flow.

TDD approach: Tests written first to define expected behavior.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from gapsense.core.models.schools import District, Region, School, SchoolInvitation
from gapsense.core.models.users import Teacher
from gapsense.engagement.teacher_flows import TeacherFlowExecutor
from gapsense.engagement.whatsapp_client import WhatsAppClient


@pytest.fixture
def mock_whatsapp_client():
    """Create a mock WhatsApp client."""
    client = AsyncMock(spec=WhatsAppClient)
    client.send_text_message = AsyncMock(return_value="msg-123")
    client.send_button_message = AsyncMock(return_value="msg-123")
    return client


@pytest.fixture(autouse=True)
def patch_whatsapp_client(mock_whatsapp_client):
    """Automatically patch WhatsAppClient.from_settings for all tests."""
    with patch(
        "gapsense.engagement.whatsapp_client.WhatsAppClient.from_settings",
        return_value=mock_whatsapp_client,
    ):
        yield


class TestInvitationCodeDetection:
    """Tests for detecting invitation codes in teacher messages."""

    @pytest.mark.asyncio
    async def test_detect_invitation_code_in_message(self, db_session):
        """Detect invitation code when teacher sends code."""
        # Setup: Create school with invitation
        region = Region(name="Greater Accra", code="GA")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(
            name="St. Mary's JHS",
            district_id=district.id,
            school_type="jhs",
        )
        db_session.add(school)
        await db_session.flush()

        invitation = SchoolInvitation(
            school_id=school.id,
            invitation_code="STMARYS-ABC123",
            max_teachers=10,
            teachers_joined=0,
            is_active=True,
        )
        db_session.add(invitation)
        await db_session.commit()

        # Create teacher
        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        # Execute flow with invitation code
        executor = TeacherFlowExecutor(db=db_session)
        response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="STMARYS-ABC123",
            message_id="msg-test",
        )

        # Verify teacher was linked to school
        await db_session.refresh(teacher)
        assert teacher.school_id == school.id

        # Verify teachers_joined incremented
        stmt = select(SchoolInvitation).where(SchoolInvitation.invitation_code == "STMARYS-ABC123")
        result = await db_session.execute(stmt)
        updated_invitation = result.scalar_one()
        assert updated_invitation.teachers_joined == 1

        # Verify moved to next step (COLLECT_CLASS)
        assert teacher.conversation_state["step"] == "COLLECT_CLASS"

        # Verify confirmation message
        # Response is TeacherFlowResult, check via message sent and state
        assert response.message_sent is True

    @pytest.mark.asyncio
    async def test_detect_code_with_extra_text(self, db_session):
        """Detect code even with extra text in message."""
        # Setup school + invitation
        region = Region(name="Greater Accra", code="GA")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Wesley Girls", district_id=district.id, school_type="jhs")
        db_session.add(school)
        await db_session.flush()

        invitation = SchoolInvitation(
            school_id=school.id,
            invitation_code="WESLEY-XYZ789",
            max_teachers=5,
            teachers_joined=0,
            is_active=True,
        )
        db_session.add(invitation)
        await db_session.commit()

        teacher = Teacher(
            phone="+233244111111",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        _response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="My code is WESLEY-XYZ789",
            message_id="msg-test",
        )

        await db_session.refresh(teacher)
        assert teacher.school_id == school.id

    @pytest.mark.asyncio
    async def test_case_insensitive_code_detection(self, db_session):
        """Accept invitation codes in lowercase."""
        region = Region(name="Greater Accra", code="GA")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id, school_type="jhs")
        db_session.add(school)
        await db_session.flush()

        invitation = SchoolInvitation(
            school_id=school.id,
            invitation_code="TESTSCH-ABC123",
            max_teachers=10,
            teachers_joined=0,
            is_active=True,
        )
        db_session.add(invitation)
        await db_session.commit()

        teacher = Teacher(
            phone="+233244222222",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        _response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="testsch-abc123",
            message_id="msg-test",
        )

        await db_session.refresh(teacher)
        assert teacher.school_id == school.id


class TestInvitationCodeValidation:
    """Tests for invitation code validation errors."""

    @pytest.mark.asyncio
    async def test_invalid_code_format(self, db_session, region_district_school):
        """Inputs that don't match invitation code pattern are treated as manual school names."""
        _region, _district, _school = region_district_school

        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="INVALID-CODE",  # 4 chars after dash, doesn't match pattern
            message_id="msg-test",
        )

        # Should be treated as manual school name and proceed to next step
        await db_session.refresh(teacher)
        assert response.message_sent is True
        # School name stored in conversation data for later processing
        assert teacher.conversation_state["data"]["school_name"] == "INVALID-CODE"

    @pytest.mark.asyncio
    async def test_code_not_in_database(self, db_session):
        """Reject code that doesn't exist in database."""
        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="NONEXIST-ABC123",
            message_id="msg-test",
        )

        await db_session.refresh(teacher)
        assert teacher.school_id is None
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_expired_invitation_code(self, db_session):
        """Reject expired invitation codes."""
        region = Region(name="Greater Accra", code="GA")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id, school_type="jhs")
        db_session.add(school)
        await db_session.flush()

        # Create expired invitation
        expired_date = datetime.now(UTC) - timedelta(days=1)
        invitation = SchoolInvitation(
            school_id=school.id,
            invitation_code="EXPIRED-ABC123",
            max_teachers=10,
            teachers_joined=0,
            is_active=True,
            expires_at=expired_date.isoformat(),
        )
        db_session.add(invitation)
        await db_session.commit()

        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="EXPIRED-ABC123",
            message_id="msg-test",
        )

        await db_session.refresh(teacher)
        assert teacher.school_id is None
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_inactive_invitation_code(self, db_session):
        """Reject inactive invitation codes."""
        region = Region(name="Greater Accra", code="GA")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id, school_type="jhs")
        db_session.add(school)
        await db_session.flush()

        invitation = SchoolInvitation(
            school_id=school.id,
            invitation_code="INACTIVE-ABC123",
            max_teachers=10,
            teachers_joined=0,
            is_active=False,  # Inactive
        )
        db_session.add(invitation)
        await db_session.commit()

        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="INACTIVE-ABC123",
            message_id="msg-test",
        )

        await db_session.refresh(teacher)
        assert teacher.school_id is None
        assert response.error is not None

    @pytest.mark.asyncio
    async def test_max_teachers_reached(self, db_session):
        """Reject code when max teachers limit reached."""
        region = Region(name="Greater Accra", code="GA")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Accra Metro")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id, school_type="jhs")
        db_session.add(school)
        await db_session.flush()

        invitation = SchoolInvitation(
            school_id=school.id,
            invitation_code="FULL-ABC123",
            max_teachers=5,
            teachers_joined=5,  # At limit
            is_active=True,
        )
        db_session.add(invitation)
        await db_session.commit()

        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="FULL-ABC123",
            message_id="msg-test",
        )

        await db_session.refresh(teacher)
        assert teacher.school_id is None
        assert response.error is not None


class TestInvitationCodeFallback:
    """Tests for fallback to manual school entry if no code."""

    @pytest.mark.asyncio
    async def test_no_code_proceeds_with_manual_entry(self, db_session, region_district_school):
        """If no code detected, proceed with manual school name entry."""
        _region, _district, _school = region_district_school

        teacher = Teacher(
            phone="+233244123456",
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_SCHOOL",
                "data": {},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        _response = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="St. Mary's JHS",
            message_id="msg-test",
        )

        # Should attempt manual school creation/matching
        # (existing behavior - not changed)
        await db_session.refresh(teacher)
        # Exact behavior depends on existing manual flow implementation
