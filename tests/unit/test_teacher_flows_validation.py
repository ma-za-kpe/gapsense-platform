"""
Tests for teacher flow input validation integration.

Verifies that teacher flows properly validate and normalize user input.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import Teacher
from gapsense.engagement.teacher_flows import TeacherFlowExecutor
from gapsense.engagement.whatsapp_client import WhatsAppClient


@pytest.fixture
def mock_whatsapp_client():
    """Create a mock WhatsApp client."""
    client = AsyncMock(spec=WhatsAppClient)
    client.send_text_message = AsyncMock(return_value="msg-123")
    client.send_button_message = AsyncMock(return_value="msg-123")
    client.send_template_message = AsyncMock(return_value="msg-123")
    return client


@pytest.fixture(autouse=True)
def patch_whatsapp_client(mock_whatsapp_client):
    """Automatically patch WhatsAppClient.from_settings for all tests."""
    from unittest.mock import patch

    with patch(
        "gapsense.engagement.whatsapp_client.WhatsAppClient.from_settings",
        return_value=mock_whatsapp_client,
    ):
        yield


@pytest.fixture
async def teacher(db_session: AsyncSession, region_district_school):
    """Create a test teacher with school."""
    _region, _district, school = region_district_school

    # Create teacher linked to school
    teacher = Teacher(
        phone="+233501234567",
        first_name="Test",
        last_name="Teacher",
        school_id=school.id,
        conversation_state=None,
        is_active=True,
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


# ============================================================================
# School Name Validation Integration
# ============================================================================


class TestSchoolNameValidationIntegration:
    """Tests for school name validation in teacher onboarding."""

    async def test_accepts_valid_school_name(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should accept valid school name and normalize it."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="St. Mary's JHS, Accra",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state["data"]["school_name"] == "St. Mary's JHS, Accra"

    async def test_normalizes_school_name_whitespace(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should normalize multiple spaces in school name."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="  St.  Mary's   JHS  ",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state["data"]["school_name"] == "St. Mary's JHS"

    async def test_rejects_too_short_school_name(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject school names that are too short."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="AB",
            message_id="msg-test",
        )

        assert result.error is not None
        assert "at least 3 characters" in result.error.lower()

    async def test_rejects_numbers_only_school_name(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject school names with only numbers."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="12345",
            message_id="msg-test",
        )

        assert result.error is not None
        assert "must contain letters" in result.error.lower()


# ============================================================================
# Class Name Validation Integration
# ============================================================================


class TestClassNameValidationIntegration:
    """Tests for class name validation in teacher onboarding."""

    async def test_accepts_valid_class_name_basic_7(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should accept 'Basic 7' format."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_CLASS",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="Basic 7",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state["data"]["class_name"] == "Basic 7"

    async def test_normalizes_class_name_case(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should normalize class name to title case."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_CLASS",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="basic 7",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state["data"]["class_name"] == "Basic 7"

    async def test_accepts_jhs_format(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should accept 'JHS 1' format with uppercase JHS."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_CLASS",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="jhs 1",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state["data"]["class_name"] == "JHS 1"

    async def test_rejects_invalid_grade_level(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject invalid grade levels."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_CLASS",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="Basic 15",
            message_id="msg-test",
        )

        assert result.error is not None
        assert "invalid grade level" in result.error.lower()


# ============================================================================
# Student Count Validation Integration
# ============================================================================


class TestStudentCountValidationIntegration:
    """Tests for student count validation in teacher onboarding."""

    async def test_accepts_valid_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should accept valid student count."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="25",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state["data"]["student_count"] == 25

    async def test_rejects_zero_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject zero student count."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="0",
            message_id="msg-test",
        )

        assert result.error is not None
        assert "must be positive" in result.error.lower()

    async def test_rejects_negative_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject negative student count."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="-5",
            message_id="msg-test",
        )

        assert result.error is not None
        # Validation treats negative numbers as non-numeric
        assert "must be a number" in result.error.lower()

    async def test_rejects_non_numeric_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject non-numeric student count."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="twenty",
            message_id="msg-test",
        )

        assert result.error is not None
        assert "must be a number" in result.error.lower()


# ============================================================================
# Student Names Validation Integration
# ============================================================================


class TestStudentNamesValidationIntegration:
    """Tests for student name validation in teacher onboarding."""

    async def test_normalizes_student_names_from_list(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should normalize all student names in a list."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_STUDENT_LIST",
            "data": {
                "school_name": "Test School",
                "class_name": "Basic 7",
                "student_count": 3,
            },
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="1. kwame mensah\n2. ama serwaa\n3. kofi agyeman",
            message_id="msg-test",
        )

        assert result.error is None
        assert result.message_sent is True
        await db_session.refresh(teacher)
        # Should normalize to title case and strip numbering, then move to confirmation
        assert teacher.conversation_state["step"] == "CONFIRM_STUDENT_CREATION"
        parsed_names = teacher.conversation_state["data"].get("parsed_names", [])
        assert len(parsed_names) == 3
        assert parsed_names[0] == "Kwame Mensah"
        assert parsed_names[1] == "Ama Serwaa"
        assert parsed_names[2] == "Kofi Agyeman"

    async def test_rejects_student_name_too_short(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject student names that are too short."""
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_STUDENT_LIST",
            "data": {
                "school_name": "Test School",
                "class_name": "Basic 7",
                "student_count": 1,
            },
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="K",
            message_id="msg-test",
        )

        assert result.error is not None
        assert "at least 2 characters" in result.error.lower()
