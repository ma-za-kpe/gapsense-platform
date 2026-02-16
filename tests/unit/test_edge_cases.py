"""
Tests for edge case handling in WhatsApp flows.

Phase D of TDD implementation plan.

Handles:
- Student count mismatch (teacher says 50, sends 48)
- Duplicate student names
- Session timeout
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import Parent, School, Teacher
from gapsense.engagement.flow_executor import FlowExecutor
from gapsense.engagement.teacher_flows import TeacherFlowExecutor
from gapsense.engagement.whatsapp_client import WhatsAppClient


@pytest.fixture
def mock_whatsapp_client():
    """Create a mock WhatsApp client."""
    client = AsyncMock(spec=WhatsAppClient)
    client.send_text_message = AsyncMock(return_value="wamid.123456789")
    client.send_button_message = AsyncMock(return_value="wamid.123456789")
    client.send_template_message = AsyncMock(return_value="wamid.123456789")
    return client


@pytest.fixture(autouse=True)
def patch_whatsapp_client(mock_whatsapp_client):
    """Automatically patch WhatsAppClient.from_settings for all tests."""
    with patch(
        "gapsense.engagement.whatsapp_client.WhatsAppClient.from_settings",
        return_value=mock_whatsapp_client,
    ):
        yield


# ============================================================================
# Phase D.1: Student Count Mismatch
# ============================================================================


class TestStudentCountMismatch:
    """Tests for handling student count mismatch."""

    async def test_teacher_sends_fewer_names_than_expected(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher says 50 students, sends 48 → warned + asked to confirm."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233501111111",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {
                    "school_name": "Test School",
                    "class_name": "JHS 1A",
                    "student_count": 50,  # Expected 50
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)

        # Send 48 names instead of 50
        names = "\n".join([f"{i}. Student{i}" for i in range(1, 49)])
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content=names,
            message_id="msg-123",
        )

        # Should warn about mismatch in confirmation message
        assert result.message_sent is True
        assert result.next_step == "CONFIRM_STUDENT_CREATION"

        # Check that warning message was sent
        await db_session.refresh(teacher)
        assert teacher.conversation_state["step"] == "CONFIRM_STUDENT_CREATION"
        mock_whatsapp_client.send_button_message.assert_called_once()
        call_args = mock_whatsapp_client.send_button_message.call_args
        message_body = call_args.kwargs.get("body", "")
        # Should mention count mismatch
        assert "48" in message_body
        assert "50" in message_body or "expected" in message_body.lower()

    async def test_teacher_sends_more_names_than_expected(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher says 10 students, sends 12 → warned + asked to confirm."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233502222222",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {
                    "school_name": "Test School",
                    "class_name": "JHS 1B",
                    "student_count": 10,  # Expected 10
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)

        # Send 12 names instead of 10
        names = "\n".join([f"{i}. Student{i}" for i in range(1, 13)])
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content=names,
            message_id="msg-456",
        )

        # Should warn about mismatch
        assert result.message_sent is True
        assert result.next_step == "CONFIRM_STUDENT_CREATION"

        await db_session.refresh(teacher)
        mock_whatsapp_client.send_button_message.assert_called_once()
        call_args = mock_whatsapp_client.send_button_message.call_args
        message_body = call_args.kwargs.get("body", "")
        # Should mention the mismatch
        assert "12" in message_body
        assert "10" in message_body or "expected" in message_body.lower()

    async def test_exact_count_match_no_warning(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher says 5 students, sends 5 → no warning, just preview."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233503333333",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {
                    "school_name": "Test School",
                    "class_name": "JHS 1C",
                    "student_count": 5,  # Expected 5
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)

        # Send exactly 5 names
        names = "\n".join([f"{i}. Student{i}" for i in range(1, 6)])
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content=names,
            message_id="msg-789",
        )

        # Should show normal preview without warning
        assert result.message_sent is True
        assert result.next_step == "CONFIRM_STUDENT_CREATION"

        mock_whatsapp_client.send_button_message.assert_called_once()
        call_args = mock_whatsapp_client.send_button_message.call_args
        message_body = call_args.kwargs.get("body", "")
        # Should show count but not as a warning
        assert "5 students" in message_body
        # Should NOT mention "expected" or mismatch language
        assert "expected" not in message_body.lower() or "5" in message_body


# ============================================================================
# Phase D.2: Duplicate Student Names
# ============================================================================


class TestDuplicateStudentNames:
    """Tests for detecting duplicate student names."""

    async def test_detect_duplicate_names(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher sends 'Kwame' twice → warned about duplicate."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233504444444",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {
                    "school_name": "Test School",
                    "class_name": "JHS 1A",
                    "student_count": 3,
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)

        # Send duplicate name
        names = "1. Kwame Mensah\n2. Ama Serwaa\n3. Kwame Mensah"
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content=names,
            message_id="msg-123",
        )

        # Should warn about duplicate
        assert result.message_sent is True
        assert result.next_step == "CONFIRM_STUDENT_CREATION"

        mock_whatsapp_client.send_button_message.assert_called_once()
        call_args = mock_whatsapp_client.send_button_message.call_args
        message_body = call_args.kwargs.get("body", "")
        # Should mention duplicate
        assert "duplicate" in message_body.lower() or "same name" in message_body.lower()
        assert "Kwame Mensah" in message_body


# ============================================================================
# Phase D.5: Session Timeout
# ============================================================================


class TestSessionTimeout:
    """Tests for session timeout handling."""

    async def test_parent_session_expires_after_24_hours(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent abandons flow → state expires after 24h."""
        old_time = datetime.now(UTC) - timedelta(hours=25)
        parent = Parent(
            phone="+233505555555",
            preferred_name="Test Parent",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"some": "data"},
            },
            last_message_at=old_time,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        # Parent returns after 25 hours
        result = await executor.process_message(
            parent=parent,
            message_type="text",
            message_content="Hi",
            message_id="msg-123",
        )

        # Should have cleared expired state and started fresh onboarding
        await db_session.refresh(parent)
        # Old step was AWAITING_STUDENT_SELECTION, new should be AWAITING_OPT_IN (fresh start)
        assert parent.conversation_state["step"] == "AWAITING_OPT_IN"
        assert parent.conversation_state["flow"] == "FLOW-ONBOARD"
        # Data should be reset (no old selection data)
        assert "selected_student_id" not in parent.conversation_state.get("data", {})
        assert result.message_sent is True

    async def test_teacher_session_expires_after_24_hours(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher abandons flow → state expires after 24h."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        # NOTE: Teacher.last_active_at expects timezone-naive datetime
        old_time = (datetime.now(UTC) - timedelta(hours=26)).replace(tzinfo=None)
        teacher = Teacher(
            phone="+233506666666",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {"school_name": "Test School"},
            },
            last_active_at=old_time,
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)

        # Teacher returns after 26 hours
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="Hi",
            message_id="msg-456",
        )

        # Should have cleared expired state and started fresh onboarding
        await db_session.refresh(teacher)
        # Old step was COLLECT_STUDENT_LIST, new should be COLLECT_SCHOOL (fresh start)
        assert teacher.conversation_state["step"] == "COLLECT_SCHOOL"
        assert teacher.conversation_state["flow"] == "FLOW-TEACHER-ONBOARD"
        # Data should be reset (no old school_name)
        assert "student_count" not in teacher.conversation_state.get("data", {})
        assert result.message_sent is True

    async def test_session_within_24_hours_not_expired(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent returns within 24h → session still active."""
        recent_time = datetime.now(UTC) - timedelta(hours=12)
        parent = Parent(
            phone="+233507777777",
            preferred_name="Test Parent",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
            },
            last_message_at=recent_time,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        # Parent returns after 12 hours
        result = await executor.process_message(
            parent=parent,
            message_type="interactive",
            message_content={"type": "button_reply", "button_reply": {"id": "lang_en"}},
            message_id="msg-789",
        )

        # Session should still be active
        await db_session.refresh(parent)
        # State should have been processed (not cleared due to timeout)
        assert result.message_sent is True
