"""
TDD Tests for Spec-Compliant FLOW-ONBOARD

Based on gapsense_whatsapp_flows.json lines 85-197.

FLOW-ONBOARD should have 7 steps:
1. Template welcome (TMPL-ONBOARD-001)
2. Opt-in button response
3. Collect child's first name
4. Collect child's age
5. Collect child's grade
6. Collect language preference
7. Complete + Create Student record

Current implementation FAILS these tests - this is intentional TDD.
"""

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import Parent, Student
from gapsense.engagement.flow_executor import FlowExecutor


class TestOnboardingSpecCompliance:
    """Test FLOW-ONBOARD matches spec requirements."""

    @pytest.mark.asyncio
    async def test_step1_uses_template_message(self, db_session: AsyncSession) -> None:
        """Step 1: Should use template message, not regular text."""
        # Create new parent
        parent = Parent(phone="+233501234567")
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_template_message.return_value = "wamid.template123"

            # First message should trigger template
            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="Hi",
                message_id="wamid.incoming1",
            )

            # Should use template message, not text message
            mock_client.send_template_message.assert_called_once()
            assert result.message_sent is True
            assert result.completed is False

    @pytest.mark.asyncio
    async def test_step2_opt_in_required(self, db_session: AsyncSession) -> None:
        """Step 2: Should require explicit opt-in before collecting data."""
        # Create parent who has received template
        parent = Parent(
            phone="+233501234567",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_OPT_IN",
                "data": {},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.response1"

            # Parent clicks "Yes, let's start!"
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "yes_start", "title": "Yes, let's start!"},
                },
                message_id="wamid.optin1",
            )

            # Should set opted_in = True
            await db_session.refresh(parent)
            assert parent.opted_in is True
            assert parent.opted_in_at is not None
            assert parent.conversation_state["step"] == "AWAITING_CHILD_NAME"

    @pytest.mark.asyncio
    async def test_step3_collects_child_name_not_parent_name(
        self, db_session: AsyncSession
    ) -> None:
        """Step 3: Should ask for CHILD's first name, not parent's name.

        This is the critical bug - current implementation asks for parent name.
        """
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CHILD_NAME",
                "data": {},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_button_message.return_value = "wamid.age_buttons"

            # Parent provides child's name
            await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="Kwame",
                message_id="wamid.name1",
            )

            # Should store in conversation data (will be used for Student creation)
            await db_session.refresh(parent)
            assert parent.conversation_state["data"]["child_name"] == "Kwame"
            assert parent.conversation_state["step"] == "AWAITING_CHILD_AGE"

            # Should NOT be stored as parent.preferred_name
            assert parent.preferred_name is None

    @pytest.mark.asyncio
    async def test_step4_collects_child_age(self, db_session: AsyncSession) -> None:
        """Step 4: Should collect child's age with button options."""
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CHILD_AGE",
                "data": {"child_name": "Kwame"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_list_message.return_value = "wamid.grade_list"

            # Parent selects "7-8 years" button
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "age_7", "title": "7-8 years"},
                },
                message_id="wamid.age1",
            )

            # Should store age
            await db_session.refresh(parent)
            assert parent.conversation_state["data"]["child_age"] == 7
            assert parent.conversation_state["step"] == "AWAITING_CHILD_GRADE"

    @pytest.mark.asyncio
    async def test_step5_collects_child_grade(self, db_session: AsyncSession) -> None:
        """Step 5: Should collect child's grade with list selection."""
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CHILD_GRADE",
                "data": {"child_name": "Kwame", "child_age": 7},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_button_message.return_value = "wamid.language_buttons"

            # Parent selects "Class 2 (B2)"
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "list_reply",
                    "list_reply": {"id": "grade_B2", "title": "Class 2 (B2)"},
                },
                message_id="wamid.grade1",
            )

            # Should store grade
            await db_session.refresh(parent)
            assert parent.conversation_state["data"]["child_grade"] == "B2"
            assert parent.conversation_state["step"] == "AWAITING_LANGUAGE"

    @pytest.mark.asyncio
    async def test_step6_collects_language(self, db_session: AsyncSession) -> None:
        """Step 6: Should collect language preference."""
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {
                    "child_name": "Kwame",
                    "child_age": 7,
                    "child_grade": "B2",
                },
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.completion"

            # Parent selects "Twi"
            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "lang_twi", "title": "Twi"},
                },
                message_id="wamid.lang1",
            )

            # Should store language AND create Student
            await db_session.refresh(parent)
            assert parent.preferred_language == "tw"
            assert result.completed is True

    @pytest.mark.asyncio
    async def test_step7_creates_student_record(self, db_session: AsyncSession) -> None:
        """Step 7: CRITICAL - Should create Student record with collected data.

        This is the blocking bug - current implementation NEVER creates Student.
        Without Student, diagnostics and activities cannot run.
        """
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {
                    "child_name": "Kwame",
                    "child_age": 7,
                    "child_grade": "B2",
                },
            },
        )
        db_session.add(parent)
        await db_session.commit()
        parent_id = parent.id

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.completion"

            # Complete onboarding
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "lang_en", "title": "English"},
                },
                message_id="wamid.complete1",
            )

            # CRITICAL: Verify Student was created
            stmt = select(Student).where(Student.primary_parent_id == parent_id)
            result_db = await db_session.execute(stmt)
            student = result_db.scalar_one_or_none()

            assert student is not None, "Student record MUST be created at onboarding completion"
            assert student.first_name == "Kwame"
            assert student.age == 7
            assert student.current_grade == "B2"
            assert student.primary_parent_id == parent_id
            assert student.is_active is True

            # Verify onboarding is complete
            await db_session.refresh(parent)
            assert parent.conversation_state is None
            assert parent.onboarded_at is not None

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow_end_to_end(self, db_session: AsyncSession) -> None:
        """Integration test: Complete onboarding flow from start to Student creation."""
        # Start: New parent
        parent = Parent(phone="+233501234567")
        db_session.add(parent)
        await db_session.commit()
        parent_id = parent.id

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_template_message.return_value = "wamid.template"
            mock_client.send_text_message.return_value = "wamid.text"
            mock_client.send_button_message.return_value = "wamid.buttons"
            mock_client.send_list_message.return_value = "wamid.list"

            # Step 1-2: Initial message + opt-in
            await executor.process_message(
                parent=parent, message_type="text", message_content="Hi", message_id="m1"
            )
            await db_session.refresh(parent)

            # Opt in
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "yes_start", "title": "Yes!"},
                },
                message_id="m2",
            )
            await db_session.refresh(parent)

            # Step 3: Provide child name
            await executor.process_message(
                parent=parent, message_type="text", message_content="Kwame", message_id="m3"
            )
            await db_session.refresh(parent)
            assert parent.conversation_state["data"]["child_name"] == "Kwame"

            # Step 4: Select age
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "age_7", "title": "7-8 years"},
                },
                message_id="m4",
            )
            await db_session.refresh(parent)
            assert parent.conversation_state["data"]["child_age"] == 7

            # Step 5: Select grade
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "list_reply",
                    "list_reply": {"id": "grade_B2", "title": "Class 2 (B2)"},
                },
                message_id="m5",
            )
            await db_session.refresh(parent)
            assert parent.conversation_state["data"]["child_grade"] == "B2"

            # Step 6-7: Select language + complete
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "lang_twi", "title": "Twi"},
                },
                message_id="m6",
            )

            # Verify final state
            await db_session.refresh(parent)
            assert parent.opted_in is True
            assert parent.preferred_language == "tw"
            assert parent.onboarded_at is not None
            assert parent.conversation_state is None

            # CRITICAL: Verify Student exists
            stmt = select(Student).where(Student.primary_parent_id == parent_id)
            result = await db_session.execute(stmt)
            student = result.scalar_one()
            assert student.first_name == "Kwame"
            assert student.age == 7
            assert student.current_grade == "B2"
