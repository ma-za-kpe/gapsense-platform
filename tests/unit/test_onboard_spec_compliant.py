"""
TDD Tests for NEW Teacher-Initiated FLOW-ONBOARD

Based on MVP Blueprint specification (teacher-initiated platform).

NEW FLOW-ONBOARD has 6 steps:
1. Template welcome (TMPL-ONBOARD-001)
2. Opt-in button response
3. Show student selection list (from teacher rosters)
4. Parent selects student by number
5. Diagnostic consent
6. Collect language preference
7. Complete + LINK parent to existing student (NOT create)

This replaces the old parent-initiated flow that created students.
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import Parent, School, Student, Teacher
from gapsense.engagement.flow_executor import FlowExecutor


class TestTeacherInitiatedOnboarding:
    """Test NEW teacher-initiated FLOW-ONBOARD."""

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
    async def test_step2_opt_in_shows_student_list(self, db_session: AsyncSession) -> None:
        """Step 2: After opt-in, should show student selection list."""
        # Create school and teacher
        school = School(name="Test School", district_id=1, school_type="jhs")
        db_session.add(school)
        await db_session.commit()

        teacher = Teacher(
            phone="+233200000001",
            first_name="Ms.",
            last_name="Teacher",
            school_id=school.id,
            grade_taught="JHS1",
        )
        db_session.add(teacher)
        await db_session.commit()

        # Create unlinked students (from teacher)
        student1 = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            school_id=school.id,
            teacher_id=teacher.id,
            primary_parent_id=None,  # Unlinked
        )
        student2 = Student(
            full_name="Ama Osei",
            first_name="Ama",
            current_grade="JHS1",
            school_id=school.id,
            teacher_id=teacher.id,
            primary_parent_id=None,  # Unlinked
        )
        db_session.add_all([student1, student2])
        await db_session.commit()

        # Create parent
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
            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={"id": "yes_start", "title": "Yes, let's start!"},
                message_id="wamid.optin1",
            )

            # Should set opted_in = True and show student list
            await db_session.refresh(parent)
            assert parent.opted_in is True
            assert parent.opted_in_at is not None
            assert parent.conversation_state["step"] == "AWAITING_STUDENT_SELECTION"

            # Should have sent student list
            assert result.message_sent is True
            assert mock_client.send_text_message.called

            # Should have stored student_ids_map in conversation state
            assert "student_ids_map" in parent.conversation_state["data"]

    @pytest.mark.asyncio
    async def test_step3_parent_selects_student(self, db_session: AsyncSession) -> None:
        """Step 3: Parent selects child from list by number."""
        # Create school and student
        school = School(name="Test School", district_id=1, school_type="jhs")
        db_session.add(school)
        await db_session.commit()

        student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            school_id=school.id,
            primary_parent_id=None,  # Unlinked
        )
        db_session.add(student)
        await db_session.commit()
        student_id = student.id

        # Create parent with student selection state
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"student_ids_map": {"1": str(student_id)}},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_button_message.return_value = "wamid.consent_buttons"

            # Parent selects student 1
            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="1",
                message_id="wamid.selection1",
            )

            # Should move to diagnostic consent and save selected student ID
            await db_session.refresh(parent)
            assert parent.conversation_state["step"] == "AWAITING_DIAGNOSTIC_CONSENT"
            assert parent.conversation_state["data"]["selected_student_id"] == str(student_id)

            # Should ask for diagnostic consent
            assert result.message_sent is True
            assert mock_client.send_button_message.called

    @pytest.mark.asyncio
    async def test_step4_diagnostic_consent(self, db_session: AsyncSession) -> None:
        """Step 4: Should collect diagnostic consent."""
        student_id = uuid4()

        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_DIAGNOSTIC_CONSENT",
                "data": {"selected_student_id": str(student_id)},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_button_message.return_value = "wamid.language_buttons"

            # Parent consents
            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={"id": "consent_yes", "title": "Yes, proceed"},
                message_id="wamid.consent1",
            )

            # Should save consent and move to language
            await db_session.refresh(parent)
            assert parent.diagnostic_consent is True
            assert parent.diagnostic_consent_at is not None
            assert parent.conversation_state["step"] == "AWAITING_LANGUAGE"

            # Should ask for language
            assert result.message_sent is True
            assert mock_client.send_button_message.called

    @pytest.mark.asyncio
    async def test_step5_language_links_to_student(self, db_session: AsyncSession) -> None:
        """Step 5: Language selection should LINK parent to existing student (not create)."""
        # Create school and student
        school = School(name="Test School", district_id=1, school_type="jhs")
        db_session.add(school)
        await db_session.commit()

        student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            school_id=school.id,
            primary_parent_id=None,  # Unlinked
        )
        db_session.add(student)
        await db_session.commit()
        student_id = student.id

        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            diagnostic_consent=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {"selected_student_id": str(student_id)},
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

            # Parent selects language
            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={"id": "lang_tw", "title": "Twi"},
                message_id="wamid.lang1",
            )

            # Should complete onboarding
            assert result.completed is True

            # CRITICAL: Should LINK to existing student (not create new one)
            await db_session.refresh(parent)
            await db_session.refresh(student)

            assert parent.preferred_language == "tw"
            assert parent.onboarded_at is not None
            assert parent.conversation_state is None

            # Student should now be linked to parent
            assert student.primary_parent_id == parent_id
            assert student.home_language == "tw"

    @pytest.mark.asyncio
    async def test_student_linking_not_creation(self, db_session: AsyncSession) -> None:
        """CRITICAL: Onboarding should LINK to student, NOT create new student."""
        # Create school and student
        school = School(name="Test School", district_id=1, school_type="jhs")
        db_session.add(school)
        await db_session.commit()

        existing_student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            school_id=school.id,
            primary_parent_id=None,
        )
        db_session.add(existing_student)
        await db_session.commit()
        student_id = existing_student.id

        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            diagnostic_consent=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {"selected_student_id": str(student_id)},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        # Count students before onboarding
        stmt = select(Student)
        result_before = await db_session.execute(stmt)
        students_before = result_before.scalars().all()
        count_before = len(students_before)

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.completion"

            # Complete onboarding
            await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={"id": "lang_en", "title": "English"},
                message_id="wamid.complete1",
            )

            # Count students after onboarding
            result_after = await db_session.execute(stmt)
            students_after = result_after.scalars().all()
            count_after = len(students_after)

            # CRITICAL: Should NOT create new student
            assert (
                count_after == count_before
            ), "Should link to existing student, not create new one"

            # Should link to the existing student
            await db_session.refresh(existing_student)
            assert existing_student.primary_parent_id == parent.id

    @pytest.mark.asyncio
    async def test_no_students_available_error(self, db_session: AsyncSession) -> None:
        """Should handle case where no unlinked students exist."""
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
            mock_client.send_text_message.return_value = "wamid.error"

            # Parent opts in
            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={"id": "yes_start", "title": "Yes!"},
                message_id="wamid.optin1",
            )

            # Should send error message
            assert result.message_sent is True
            assert result.error == "No unlinked students available"

            # Should clear conversation state
            await db_session.refresh(parent)
            assert parent.conversation_state is None

    @pytest.mark.asyncio
    async def test_race_condition_student_already_linked(self, db_session: AsyncSession) -> None:
        """Should handle race condition where student gets linked by another parent."""
        # Create school and student
        school = School(name="Test School", district_id=1, school_type="jhs")
        db_session.add(school)
        await db_session.commit()

        # Create real parent (student already linked to them)
        other_parent = Parent(phone="+233999999999")
        db_session.add(other_parent)
        await db_session.commit()

        student = Student(
            full_name="Kwame Mensah",
            first_name="Kwame",
            current_grade="JHS1",
            school_id=school.id,
            primary_parent_id=other_parent.id,  # Already linked!
        )
        db_session.add(student)
        await db_session.commit()
        student_id = student.id

        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_STUDENT_SELECTION",
                "data": {"student_ids_map": {"1": str(student_id)}},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.error"

            # Parent tries to select already-linked student
            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="1",
                message_id="wamid.selection1",
            )

            # Should detect race condition and show error
            assert result.error == "Student already linked to another parent"
            assert result.message_sent is True

            # Should clear conversation state
            await db_session.refresh(parent)
            assert parent.conversation_state is None
