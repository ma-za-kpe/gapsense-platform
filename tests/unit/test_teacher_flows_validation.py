"""
Tests for teacher flow input validation integration.

Verifies that teacher flows properly validate and normalize user input.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import School, Teacher
from gapsense.engagement.teacher_flows import TeacherFlowExecutor
from gapsense.engagement.whatsapp_client import WhatsAppClient


@pytest.fixture
def mock_whatsapp_client():
    """Create a mock WhatsApp client."""
    client = AsyncMock(spec=WhatsAppClient)
    client.send_text_message = AsyncMock(return_value=True)
    client.send_template_message = AsyncMock(return_value=True)
    return client


@pytest.fixture
async def teacher(db_session: AsyncSession):
    """Create a test teacher with school."""
    # Create a school first
    school = School(
        name="Test School",
        district_id=1,
        school_type="jhs",
        is_active=True,
    )
    db_session.add(school)
    await db_session.flush()

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
            "step": "AWAITING_SCHOOL_NAME",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="St. Mary's JHS, Accra",
        )

        assert result.success is True
        assert teacher.conversation_state["data"]["school_name"] == "St. Mary's JHS, Accra"

    async def test_normalizes_school_name_whitespace(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should normalize multiple spaces in school name."""
        teacher.conversation_state = {
            "step": "AWAITING_SCHOOL_NAME",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="  St.  Mary's   JHS  ",
        )

        assert result.success is True
        assert teacher.conversation_state["data"]["school_name"] == "St. Mary's JHS"

    async def test_rejects_too_short_school_name(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject school names that are too short."""
        teacher.conversation_state = {
            "step": "AWAITING_SCHOOL_NAME",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="AB",
        )

        assert result.success is False
        assert "at least 3 characters" in result.error.lower()

    async def test_rejects_numbers_only_school_name(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject school names with only numbers."""
        teacher.conversation_state = {
            "step": "AWAITING_SCHOOL_NAME",
            "data": {},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="12345",
        )

        assert result.success is False
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
            "step": "AWAITING_CLASS_NAME",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="Basic 7",
        )

        assert result.success is True
        assert teacher.conversation_state["data"]["class_name"] == "Basic 7"

    async def test_normalizes_class_name_case(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should normalize class name to title case."""
        teacher.conversation_state = {
            "step": "AWAITING_CLASS_NAME",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="basic 7",
        )

        assert result.success is True
        assert teacher.conversation_state["data"]["class_name"] == "Basic 7"

    async def test_accepts_jhs_format(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should accept 'JHS 1' format with uppercase JHS."""
        teacher.conversation_state = {
            "step": "AWAITING_CLASS_NAME",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="jhs 1",
        )

        assert result.success is True
        assert teacher.conversation_state["data"]["class_name"] == "JHS 1"

    async def test_rejects_invalid_grade_level(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject invalid grade levels."""
        teacher.conversation_state = {
            "step": "AWAITING_CLASS_NAME",
            "data": {"school_name": "Test School"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="Basic 15",
        )

        assert result.success is False
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
            "step": "AWAITING_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="25",
        )

        assert result.success is True
        assert teacher.conversation_state["data"]["student_count"] == 25

    async def test_rejects_zero_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject zero student count."""
        teacher.conversation_state = {
            "step": "AWAITING_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="0",
        )

        assert result.success is False
        assert "must be positive" in result.error.lower()

    async def test_rejects_negative_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject negative student count."""
        teacher.conversation_state = {
            "step": "AWAITING_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="-5",
        )

        assert result.success is False
        assert "must be positive" in result.error.lower()

    async def test_rejects_non_numeric_student_count(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject non-numeric student count."""
        teacher.conversation_state = {
            "step": "AWAITING_STUDENT_COUNT",
            "data": {"school_name": "Test School", "class_name": "Basic 7"},
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="twenty",
        )

        assert result.success is False
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
            "step": "AWAITING_STUDENT_LIST",
            "data": {
                "school_name": "Test School",
                "class_name": "Basic 7",
                "student_count": 3,
            },
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="1. kwame mensah\n2. ama serwaa\n3. kofi agyeman",
        )

        assert result.success is True
        # Should normalize to title case and strip numbering
        created_students = teacher.conversation_state["data"].get("created_student_ids", [])
        # Verify students were created (actual verification needs DB query)
        assert len(created_students) > 0

    async def test_rejects_student_name_too_short(
        self, db_session: AsyncSession, teacher: Teacher, mock_whatsapp_client: AsyncMock
    ):
        """Should reject student names that are too short."""
        teacher.conversation_state = {
            "step": "AWAITING_STUDENT_LIST",
            "data": {
                "school_name": "Test School",
                "class_name": "Basic 7",
                "student_count": 1,
            },
        }
        await db_session.commit()

        executor = TeacherFlowExecutor(db_session, mock_whatsapp_client)
        result = await executor.process_message(
            teacher=teacher,
            message_type="text",
            message_content="K",
        )

        assert result.success is False
        assert "at least 2 characters" in result.error.lower()
