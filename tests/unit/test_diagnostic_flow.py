"""
TDD Tests for FLOW-DIAGNOSTIC State Machine

Tests the diagnostic flow:
1. Deliver questions one-by-one via WhatsApp
2. Collect parent's answers
3. Use AdaptiveDiagnosticEngine to select next question
4. Complete session and generate gap profile
5. Send results to parent
"""

import pytest
from sqlalchemy import select

from gapsense.core.models import DiagnosticQuestion, DiagnosticSession, Parent, Student
from gapsense.engagement.flow_executor import FlowExecutor


@pytest.mark.asyncio
class TestDiagnosticFlowInitiation:
    """Tests for initiating diagnostic flow when parent has pending session."""

    async def test_start_diagnostic_when_parent_sends_message(self, db_session):
        """Start diagnostic flow when parent sends any message and has pending session."""
        # Setup: Parent with pending diagnostic session
        from gapsense.core.models import District, Region, School

        region = Region(name="Test Region", code="TST")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Test District")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        parent = Parent(
            phone="+233244123456",
            preferred_language="en",
            diagnostic_consent=True,
            onboarded_at="2026-02-16T20:00:00+00:00",
            conversation_state=None,  # No active conversation
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Kwame",
            current_grade="B5",
            school_id=school.id,
            primary_parent_id=parent.id,
        )
        db_session.add(student)
        await db_session.flush()

        # Create pending diagnostic session
        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B5",
            initiated_by="parent",
            channel="whatsapp",
            status="pending",
            total_questions=0,
            correct_answers=0,
        )
        db_session.add(session)
        await db_session.commit()

        # Act: Parent sends message (should trigger diagnostic start)
        executor = FlowExecutor(db=db_session)
        result = await executor.process_parent_message(
            parent=parent,
            message_type="text",
            message_content="hello",  # Any message triggers diagnostic
            message_id="test_msg_1",
        )

        # Assert: Diagnostic flow started
        await db_session.refresh(parent)
        await db_session.refresh(session)

        assert result.flow_name == "FLOW-DIAGNOSTIC"
        assert result.message_sent is True
        assert session.status == "in_progress"  # Session activated
        assert parent.conversation_state is not None
        assert parent.conversation_state["flow"] == "FLOW-DIAGNOSTIC"
        assert parent.conversation_state["step"] == "AWAITING_ANSWER"
        assert "session_id" in parent.conversation_state["data"]


@pytest.mark.asyncio
class TestDiagnosticQuestionDelivery:
    """Tests for delivering diagnostic questions to parent."""

    async def test_send_first_question_when_diagnostic_starts(self, db_session):
        """Send first question when diagnostic session starts."""
        # Setup: Create diagnostic session with curriculum node
        from gapsense.core.models import (
            CurriculumNode,
            CurriculumStrand,
            CurriculumSubStrand,
            District,
            Region,
            School,
        )

        region = Region(name="Test Region", code="TST")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Test District")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        strand = CurriculumStrand(strand_number=1, name="Number", color_hex="#000000")
        db_session.add(strand)
        await db_session.flush()

        sub_strand = CurriculumSubStrand(
            strand_id=strand.id, sub_strand_number=1, phase="B1_B3", name="Test"
        )
        db_session.add(sub_strand)
        await db_session.flush()

        node = CurriculumNode(
            code="B2.1.1.1",
            title="Place value to 1000",
            grade="B2",
            strand_id=strand.id,
            sub_strand_id=sub_strand.id,
            content_standard_number=1,
            severity=5,
            description="Test node",
        )
        db_session.add(node)
        await db_session.flush()

        parent = Parent(
            phone="+233244999999",
            preferred_language="en",
            onboarded_at="2026-02-16T20:00:00+00:00",
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Ama",
            current_grade="B5",
            school_id=school.id,
            primary_parent_id=parent.id,
        )
        db_session.add(student)
        await db_session.flush()

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B5",
            initiated_by="parent",
            channel="whatsapp",
            status="pending",
        )
        db_session.add(session)
        await db_session.commit()

        # Act: Start diagnostic flow
        executor = FlowExecutor(db=db_session)
        result = await executor._diagnostic_start_session(parent, session)

        # Assert: Question delivered
        assert result.message_sent is True
        assert result.next_step == "AWAITING_ANSWER"

        # Check question was recorded in database
        stmt = select(DiagnosticQuestion).where(DiagnosticQuestion.session_id == session.id)
        db_result = await db_session.execute(stmt)
        questions = db_result.scalars().all()

        assert len(questions) == 1
        assert questions[0].question_text is not None
        assert questions[0].question_type in ["free_response", "multiple_choice"]


@pytest.mark.asyncio
class TestDiagnosticAnswerCollection:
    """Tests for collecting parent's answers to diagnostic questions."""

    async def test_collect_answer_and_send_next_question(self, db_session):
        """Collect answer, analyze it, and send next question."""
        # Setup: Parent in middle of diagnostic with question asked
        from gapsense.core.models import (
            CurriculumNode,
            CurriculumStrand,
            CurriculumSubStrand,
            District,
            Region,
            School,
        )

        region = Region(name="Test Region", code="TST")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Test District")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        strand = CurriculumStrand(strand_number=1, name="Number", color_hex="#000000")
        db_session.add(strand)
        await db_session.flush()

        sub_strand = CurriculumSubStrand(
            strand_id=strand.id, sub_strand_number=1, phase="B1_B3", name="Test"
        )
        db_session.add(sub_strand)
        await db_session.flush()

        node = CurriculumNode(
            code="B2.1.1.1",
            title="Place value",
            grade="B2",
            strand_id=strand.id,
            sub_strand_id=sub_strand.id,
            content_standard_number=1,
            severity=5,
            description="Test",
        )
        db_session.add(node)
        await db_session.flush()

        parent = Parent(
            phone="+233244888888",
            preferred_language="en",
            onboarded_at="2026-02-16T20:00:00+00:00",
            conversation_state={
                "flow": "FLOW-DIAGNOSTIC",
                "step": "AWAITING_ANSWER",
                "data": {
                    "session_id": "placeholder",  # Will update
                    "current_question_id": "placeholder",
                },
            },
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Kofi",
            current_grade="B5",
            school_id=school.id,
            primary_parent_id=parent.id,
        )
        db_session.add(student)
        await db_session.flush()

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B5",
            initiated_by="parent",
            channel="whatsapp",
            status="in_progress",
            total_questions=1,
            correct_answers=0,
        )
        db_session.add(session)
        await db_session.flush()

        # Create current question
        question = DiagnosticQuestion(
            session_id=session.id,
            question_order=1,
            node_id=node.id,
            question_text="What number comes after 459?",
            question_type="free_response",
            expected_answer="460",
        )
        db_session.add(question)
        await db_session.flush()

        # Update parent's conversation state with actual IDs
        parent.conversation_state["data"]["session_id"] = str(session.id)
        parent.conversation_state["data"]["current_question_id"] = str(question.id)
        await db_session.commit()

        # Act: Parent answers question
        executor = FlowExecutor(db=db_session)
        result = await executor.process_parent_message(
            parent=parent,
            message_type="text",
            message_content="460",  # Correct answer
            message_id="test_msg_2",
        )

        # Assert: Answer recorded and next question sent
        await db_session.refresh(question)
        await db_session.refresh(session)

        assert question.student_response == "460"
        assert question.is_correct is True
        assert session.total_questions >= 1
        assert result.message_sent is True  # Next question sent


@pytest.mark.asyncio
class TestDiagnosticCompletion:
    """Tests for completing diagnostic session and sending results."""

    async def test_complete_session_after_max_questions(self, db_session):
        """Complete diagnostic session after reaching max questions."""
        # Setup: Session near completion
        from gapsense.core.models import District, Region, School

        region = Region(name="Test Region", code="TST")
        db_session.add(region)
        await db_session.flush()

        district = District(region_id=region.id, name="Test District")
        db_session.add(district)
        await db_session.flush()

        school = School(name="Test School", district_id=district.id)
        db_session.add(school)
        await db_session.flush()

        parent = Parent(
            phone="+233244777777",
            preferred_language="en",
            district_id=district.id,
        )
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            first_name="Abena",
            current_grade="B5",
            school_id=school.id,
            primary_parent_id=parent.id,
        )
        db_session.add(student)
        await db_session.flush()

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B5",
            initiated_by="parent",
            channel="whatsapp",
            status="in_progress",
            total_questions=15,  # At max
            correct_answers=5,
        )
        db_session.add(session)
        await db_session.commit()

        # Act: Complete diagnostic
        executor = FlowExecutor(db=db_session)
        result = await executor._diagnostic_complete_session(parent, session)

        # Assert: Session completed and gap profile created
        await db_session.refresh(session)

        assert session.status == "completed"
        assert result.completed is True
        assert result.flow_name == "FLOW-DIAGNOSTIC"

        # Check gap profile was generated
        from gapsense.core.models import GapProfile

        stmt = select(GapProfile).where(GapProfile.session_id == session.id)
        gap_result = await db_session.execute(stmt)
        gap_profile = gap_result.scalar_one_or_none()

        assert gap_profile is not None
        assert gap_profile.student_id == student.id
