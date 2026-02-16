"""
Tests for error recovery commands (RESTART, CANCEL, HELP, STATUS).

Phase B of TDD implementation plan.
"""

from unittest.mock import AsyncMock

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
    client.send_text_message = AsyncMock(return_value=True)
    client.send_template_message = AsyncMock(return_value=True)
    return client


# ============================================================================
# Phase B.1: RESTART Command
# ============================================================================


class TestRestartCommand:
    """Tests for RESTART command - clear conversation state and start over."""

    async def test_parent_restart_during_onboarding(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent sends RESTART while in onboarding - should clear state."""
        parent = Parent(
            phone="+233501111111",
            first_name="Test",
            last_name="Parent",
            conversation_state={
                "step": "AWAITING_LANGUAGE",
                "data": {"selected_student_id": "some-uuid"},
            },
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="RESTART"
        )

        assert result.success is True
        await db_session.refresh(parent)
        assert parent.conversation_state is None

    async def test_teacher_restart_during_onboarding(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher sends RESTART while collecting student list - should clear state."""
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
                "data": {"school_name": "Test School", "class_name": "Basic 7"},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="RESTART",
            message_id="msg-123",
        )

        assert result.message_sent is True
        await db_session.refresh(teacher)
        assert teacher.conversation_state is None

    async def test_restart_variations(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Should handle RESTART in various forms (case insensitive)."""
        variations = ["RESTART", "restart", "Restart", "  restart  "]

        for variation in variations:
            parent = Parent(
                phone=f"+23350{variation.strip().lower()}",
                first_name="Test",
                last_name="Parent",
                conversation_state={"step": "AWAITING_LANGUAGE"},
                is_active=True,
            )
            db_session.add(parent)
            await db_session.commit()

            executor = FlowExecutor(db=db_session)
            result = await executor.process_message(
                parent=parent, message_type="text", message_content=variation
            )

            assert result.success is True
            await db_session.refresh(parent)
            assert parent.conversation_state is None


# ============================================================================
# Phase B.2: CANCEL Command
# ============================================================================


class TestCancelCommand:
    """Tests for CANCEL command - cancel current operation."""

    async def test_parent_cancel_during_onboarding(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent sends CANCEL during onboarding - should clear state and send confirmation."""
        parent = Parent(
            phone="+233503333333",
            first_name="Test",
            last_name="Parent",
            conversation_state={
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"student_ids_map": {"1": "uuid-1"}},
            },
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="CANCEL"
        )

        assert result.success is True
        await db_session.refresh(parent)
        assert parent.conversation_state is None

    async def test_cancel_when_no_active_flow(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Sending CANCEL when no active flow - should send help message."""
        parent = Parent(
            phone="+233504444444",
            first_name="Test",
            last_name="Parent",
            conversation_state=None,
            onboarded_at=None,
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="CANCEL"
        )

        assert result.success is True
        # Should send "Nothing to cancel" or similar


# ============================================================================
# Phase B.3: HELP Command
# ============================================================================


class TestHelpCommand:
    """Tests for HELP command - show available commands and guidance."""

    async def test_parent_help_during_onboarding(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent sends HELP during onboarding - should show context-specific help."""
        parent = Parent(
            phone="+233505555555",
            first_name="Test",
            last_name="Parent",
            conversation_state={"step": "AWAITING_LANGUAGE"},
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="HELP"
        )

        assert result.success is True
        # Should send helpful message about current step

    async def test_teacher_help_general(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher sends HELP with no active flow - should show general help."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233506666666",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state=None,
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="HELP",
            message_id="msg-456",
        )

        assert result.message_sent is True

    async def test_help_shows_available_commands(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """HELP message should list available commands."""
        parent = Parent(
            phone="+233507777777",
            first_name="Test",
            last_name="Parent",
            conversation_state=None,
            onboarded_at=None,
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="HELP"
        )

        assert result.success is True
        # Should mention: RESTART, CANCEL, HELP, STATUS, START


# ============================================================================
# Phase B.4: STATUS Command
# ============================================================================


class TestStatusCommand:
    """Tests for STATUS command - show current progress/state."""

    async def test_parent_status_during_onboarding(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Parent sends STATUS during onboarding - should show progress."""
        parent = Parent(
            phone="+233508888888",
            first_name="Test",
            last_name="Parent",
            conversation_state={
                "step": "AWAITING_LANGUAGE",
                "data": {"selected_student_id": "uuid-123"},
            },
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="STATUS"
        )

        assert result.success is True
        # Should show "Onboarding: Step 3 of 4" or similar

    async def test_teacher_status_during_onboarding(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Teacher sends STATUS during onboarding - should show progress."""
        school = School(name="Test School", district_id=1, school_type="jhs", is_active=True)
        db_session.add(school)
        await db_session.flush()

        teacher = Teacher(
            phone="+233509999999",
            first_name="Test",
            last_name="Teacher",
            school_id=school.id,
            conversation_state={
                "flow": "FLOW-TEACHER-ONBOARD",
                "step": "COLLECT_CLASS",
                "data": {"school_name": "Test School"},
            },
            is_active=True,
        )
        db_session.add(teacher)
        await db_session.commit()

        executor = TeacherFlowExecutor(db=db_session)
        result = await executor.process_teacher_message(
            teacher=teacher,
            message_type="text",
            message_content="STATUS",
            message_id="msg-789",
        )

        assert result.message_sent is True
        # Should show "Teacher Onboarding: Collecting class name (Step 2 of 4)"

    async def test_status_when_no_active_flow(
        self, db_session: AsyncSession, mock_whatsapp_client: AsyncMock
    ):
        """Sending STATUS when no active flow - should show account info."""
        parent = Parent(
            phone="+233500000000",
            first_name="Test",
            last_name="Parent",
            conversation_state=None,
            onboarded_at=None,
            is_active=True,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)
        result = await executor.process_message(
            parent=parent, message_type="text", message_content="STATUS"
        )

        assert result.success is True
        # Should show "No active flow. Send START to begin onboarding."
