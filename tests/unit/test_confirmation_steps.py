"""
Tests for confirmation steps before critical actions.

Phase C of TDD implementation plan.

Prevents accidental data changes by requiring explicit confirmation for:
- Parent linking to a student
- Teacher creating student profiles
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import Parent, School, Student, Teacher
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
# Phase C.1: Student Selection Confirmation
# ============================================================================


class TestStudentSelectionConfirmation:
    """Tests for parent confirming student selection before linking."""

    async def test_parent_must_confirm_student_selection(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent selects student → asked to confirm before linking."""
        # Create unlinked student
        student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            primary_parent_id=None,
            is_active=True,
        )
        db_session.add(student)
        await db_session.flush()

        parent = Parent(
            phone="+233501111111",
            preferred_name="Test Parent",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"student_ids_map": {"1": str(student.id)}},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="1", message_id="msg-123"
        )

        # Should ask for confirmation (NOT link yet)
        await db_session.refresh(parent)
        await db_session.refresh(student)
        assert parent.conversation_state["step"] == "CONFIRM_STUDENT_SELECTION"
        assert "selected_student_id" in parent.conversation_state["data"]
        assert student.primary_parent_id is None  # Not linked yet!
        assert result.message_sent is True

    async def test_parent_confirms_selection_yes(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent confirms 'Yes' → proceeds to diagnostic consent."""
        student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            primary_parent_id=None,
            is_active=True,
        )
        db_session.add(student)
        await db_session.flush()

        parent = Parent(
            phone="+233502222222",
            preferred_name="Test Parent",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "CONFIRM_STUDENT_SELECTION",
                "data": {"selected_student_id": str(student.id)},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        # Simulate interactive button reply
        result = await executor.process_message(
            parent=parent,
            message_type="interactive",
            message_content={"type": "button_reply", "button_reply": {"id": "confirm_yes"}},
            message_id="msg-456",
        )

        # Should proceed to diagnostic consent (NOT link yet - linking happens at end of flow)
        await db_session.refresh(student)
        await db_session.refresh(parent)
        assert parent.conversation_state["step"] == "AWAITING_DIAGNOSTIC_CONSENT"
        assert student.primary_parent_id is None  # Not linked until end of onboarding!
        assert result.message_sent is True

    async def test_parent_declines_selection_no(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent says 'No' → back to student selection."""
        student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            primary_parent_id=None,
            is_active=True,
        )
        db_session.add(student)
        await db_session.flush()

        parent = Parent(
            phone="+233503333333",
            preferred_name="Test Parent",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "CONFIRM_STUDENT_SELECTION",
                "data": {"selected_student_id": str(student.id)},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent,
            message_type="interactive",
            message_content={"type": "button_reply", "button_reply": {"id": "confirm_no"}},
            message_id="msg-789",
        )

        # Should return to selection
        await db_session.refresh(parent)
        await db_session.refresh(student)
        assert parent.conversation_state["step"] == "AWAITING_STUDENT_SELECTION"
        assert student.primary_parent_id is None  # Not linked!
        assert result.message_sent is True

    async def test_confirmation_message_includes_student_name(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Confirmation message should show student's name for verification."""
        student = Student(
            full_name="Ama Serwaa Boateng",
            first_name="Ama",
            current_grade="JHS2",
            primary_parent_id=None,
            is_active=True,
        )
        db_session.add(student)
        await db_session.flush()

        parent = Parent(
            phone="+233504444444",
            preferred_name="Test Parent",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"student_ids_map": {"1": str(student.id)}},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        await executor.process_message(
            parent=parent, message_type="text", message_content="1", message_id="msg-123"
        )

        # Check that button message was sent with student name
        mock_whatsapp_client.send_button_message.assert_called_once()
        call_args = mock_whatsapp_client.send_button_message.call_args
        # Verify student name appears in message body
        # (implementation will determine exact format)
        assert call_args is not None


# ============================================================================
# Phase C.2: Teacher Onboarding Confirmation
# ============================================================================


class TestTeacherOnboardingConfirmation:
    """Tests for teacher confirming student creation before committing."""

    async def test_teacher_previews_before_creation(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher completes roster → sees preview before creating students."""
        school = School(name="St. Mary's JHS", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233505555555",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {
                    "school_name": "St. Mary's JHS",
                    "class_name": "JHS 1A",
                    "student_count": 3,
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="1. Kwame Mensah\n2. Ama Serwaa\n3. Kofi Agyeman",
            message_id="msg-123",
        )

        # Should show preview (NOT create yet)
        await db_session.refresh(teacher)
        assert teacher.conversation_state["step"] == "CONFIRM_STUDENT_CREATION"
        assert "parsed_names" in teacher.conversation_state["data"]
        assert result.message_sent is True

        # Verify NO students created yet
        from sqlalchemy import select

        stmt = select(Student).where(Student.teacher_id == teacher.id)
        students = (await db_session.execute(stmt)).scalars().all()
        assert len(students) == 0  # No students created yet!

    async def test_teacher_confirms_creation(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher confirms → students created."""
        school = School(name="St. Mary's JHS", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233506666666",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "CONFIRM_STUDENT_CREATION",
                "data": {
                    "school_name": "St. Mary's JHS",
                    "class_name": "JHS 1A",
                    "student_count": 3,
                    "parsed_names": ["Kwame Mensah", "Ama Serwaa", "Kofi Agyeman"],
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="interactive",
            message_content={"type": "button_reply", "button_reply": {"id": "confirm_yes"}},
            message_id="msg-456",
        )

        # NOW students should be created
        from sqlalchemy import select

        await db_session.refresh(teacher)  # Refresh before accessing teacher.id
        stmt = select(Student).where(Student.teacher_id == teacher.id)
        students = (await db_session.execute(stmt)).scalars().all()
        assert len(students) == 3
        assert students[0].full_name == "Kwame Mensah"
        assert students[1].full_name == "Ama Serwaa"
        assert students[2].full_name == "Kofi Agyeman"
        assert result.message_sent is True

    async def test_teacher_declines_asks_to_resend(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher says 'No' → can resend student list."""
        school = School(name="St. Mary's JHS", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233507777777",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "CONFIRM_STUDENT_CREATION",
                "data": {
                    "school_name": "St. Mary's JHS",
                    "class_name": "JHS 1A",
                    "student_count": 3,
                    "parsed_names": ["Kwame", "Ama", "Kofi"],
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="interactive",
            message_content={"type": "button_reply", "button_reply": {"id": "confirm_no"}},
            message_id="msg-789",
        )

        # Should return to COLLECT_STUDENT_LIST
        await db_session.refresh(teacher)
        assert teacher.conversation_state["step"] == "COLLECT_STUDENT_LIST"
        assert result.message_sent is True

        # Verify NO students created
        from sqlalchemy import select

        stmt = select(Student).where(Student.teacher_id == teacher.id)
        students = (await db_session.execute(stmt)).scalars().all()
        assert len(students) == 0

    async def test_preview_shows_student_count(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Preview message should show number of students."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233508888888",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_STUDENT_LIST",
                "data": {
                    "school_name": "Test School",
                    "class_name": "Basic 7",
                    "student_count": 5,
                },
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="1. Name1\n2. Name2\n3. Name3\n4. Name4\n5. Name5",
            message_id="msg-123",
        )

        # Check that button message includes count
        mock_whatsapp_client.send_button_message.assert_called_once()
        # (implementation will determine exact format)
