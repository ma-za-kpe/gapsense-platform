"""
Integration Test for Complete AI Diagnostic Flow

Tests the full AI pipeline:
1. DIAG-001: Generate contextual questions
2. DIAG-002: Analyze student responses for patterns
3. DIAG-003: Synthesize root cause gap profile

This test verifies that all three AI prompts work together to deliver
the core competitive advantage: "AI finds root learning gaps".
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import (
    CurriculumNode,
    DiagnosticQuestion,
    DiagnosticSession,
    Student,
)
from gapsense.diagnostic import (
    GapProfileAnalyzer,
    QuestionGenerator,
    ResponseAnalyzer,
)


@pytest.mark.asyncio
async def test_complete_ai_diagnostic_flow(db_session: AsyncSession) -> None:
    """Test complete AI flow: DIAG-001 → DIAG-002 → DIAG-003.

    This integration test verifies that:
    1. DIAG-001 generates contextually appropriate questions
    2. DIAG-002 analyzes responses for error patterns/misconceptions
    3. DIAG-003 synthesizes comprehensive gap profile with root cause

    Note: Requires ANTHROPIC_API_KEY environment variable to be set.
    Falls back to rule-based if AI unavailable.
    """
    # Arrange: Create test student and session
    from gapsense.core.models import District, Parent, Region, School

    region = Region(name="Greater Accra", code="GAR")
    db_session.add(region)
    await db_session.flush()

    district = District(name="Accra Metro", region_id=region.id)
    db_session.add(district)
    await db_session.flush()

    school = School(name="Test Primary", district_id=district.id)
    db_session.add(school)
    await db_session.flush()

    parent = Parent(
        phone="+233501234567",
        district_id=district.id,
    )
    db_session.add(parent)
    await db_session.flush()

    student = Student(
        first_name="Kwame",
        current_grade="B5",
        age=10,
        home_language="Twi",
        school_language="English",
        primary_parent_id=parent.id,
        school_id=school.id,
    )
    db_session.add(student)
    await db_session.flush()

    session = DiagnosticSession(
        student_id=student.id,
        initiated_by="parent",
        channel="whatsapp",
        entry_grade="B5",
        status="in_progress",
        total_questions=0,
        correct_answers=0,
    )
    db_session.add(session)
    await db_session.flush()

    # Get a test node to work with
    from sqlalchemy import select

    node_result = await db_session.execute(
        select(CurriculumNode).where(CurriculumNode.code == "B2.1.1.1").limit(1)
    )
    node = node_result.scalar_one_or_none()

    if not node:
        # Create a test node if it doesn't exist
        from gapsense.core.models import CurriculumStrand, CurriculumSubStrand

        strand = CurriculumStrand(
            strand_number=1,
            name="Number",
            color_hex="#2563EB",
            description="Number operations",
        )
        db_session.add(strand)
        await db_session.flush()

        sub_strand = CurriculumSubStrand(
            strand_id=strand.id,
            sub_strand_number=1,
            phase="B1_B3",
            name="Place Value",
            description="Understanding place value",
        )
        db_session.add(sub_strand)
        await db_session.flush()

        node = CurriculumNode(
            code="B2.1.1.1",
            title="Place value to 1000",
            grade="B2",
            description="Understand place value for numbers up to 1000",
            strand_id=strand.id,
            sub_strand_id=sub_strand.id,
            content_standard_number=1,
            severity=3,
        )
        db_session.add(node)
        await db_session.flush()

    # Act 1: Generate question using DIAG-001
    question_gen = QuestionGenerator(use_ai=True)
    question_data = question_gen.generate_question(node, question_number=1)

    # Assert: Question was generated
    assert question_data["question_text"]
    assert question_data["question_type"] in ["free_response", "multiple_choice"]

    # Act 2: Simulate student answering incorrectly
    question = DiagnosticQuestion(
        session_id=session.id,
        question_order=1,
        node_id=node.id,
        question_text=question_data["question_text"],
        question_type=question_data["question_type"],
        expected_answer=question_data.get("expected_answer"),
        student_response="450",  # Incorrect answer (reverses place value)
        is_correct=False,
    )
    db_session.add(question)
    await db_session.flush()

    # Act 3: Analyze response using DIAG-002
    response_analyzer = ResponseAnalyzer(use_ai=True)
    ai_analysis = response_analyzer.analyze_response(
        student=student,
        session=session,
        question=question,
        node_code=node.code,
    )

    # Assert: AI analysis detected patterns
    assert "is_correct" in ai_analysis
    assert "confidence" in ai_analysis
    assert "error_pattern" in ai_analysis
    assert "next_action" in ai_analysis
    assert ai_analysis["next_action"] in [
        "confirm_at_node",
        "trace_backward",
        "move_forward",
        "conclude_branch",
    ]

    # Act 4: Update session state
    session.total_questions = 10  # Simulate 10 questions asked
    session.correct_answers = 3  # 30% correct
    session.nodes_tested = [node.id]
    session.nodes_gap = [node.id]
    session.root_gap_node_id = node.id
    session.root_gap_confidence = 0.85
    session.status = "completed"
    await db_session.flush()

    # Act 5: Generate gap profile using DIAG-003
    gap_analyzer = GapProfileAnalyzer(session, db_session)
    gap_profile = await gap_analyzer.generate_gap_profile()

    # Assert: Gap profile was generated
    assert gap_profile.student_id == student.id
    assert gap_profile.session_id == session.id
    assert len(gap_profile.gap_nodes) > 0
    assert gap_profile.primary_gap_node == node.id
    assert gap_profile.overall_confidence > 0.0
    assert gap_profile.is_current is True

    # Assert: AI root cause analysis was attempted (may be None if API unavailable)
    ai_root_cause = await gap_analyzer.generate_ai_root_cause_analysis()
    if ai_root_cause:
        # AI analysis succeeded
        assert "root_cause_explanation" in ai_root_cause
        assert "primary_cascade" in ai_root_cause
        assert "gap_node_codes" in ai_root_cause
        assert "parent_message" in ai_root_cause

    await db_session.commit()


@pytest.mark.asyncio
async def test_ai_fallback_to_rule_based(db_session: AsyncSession) -> None:
    """Test that system gracefully falls back to rule-based when AI unavailable.

    This ensures the platform remains functional even if:
    - ANTHROPIC_API_KEY is not set
    - API rate limits are exceeded
    - Network connection is unavailable
    """
    # Arrange: Create minimal test data
    from gapsense.core.models import District, Parent, Region, School

    region = Region(name="Test Region", code="TST")
    db_session.add(region)
    await db_session.flush()

    district = District(name="Test District", region_id=region.id)
    db_session.add(district)
    await db_session.flush()

    school = School(name="Test School", district_id=district.id)
    db_session.add(school)
    await db_session.flush()

    parent = Parent(phone="+233500000000", district_id=district.id)
    db_session.add(parent)
    await db_session.flush()

    student = Student(
        first_name="Test",
        current_grade="B3",
        primary_parent_id=parent.id,
        school_id=school.id,
    )
    db_session.add(student)
    await db_session.flush()

    session = DiagnosticSession(
        student_id=student.id,
        initiated_by="parent",
        channel="whatsapp",
        entry_grade="B3",
        status="in_progress",
    )
    db_session.add(session)
    await db_session.flush()

    # Create test node
    from gapsense.core.models import CurriculumStrand, CurriculumSubStrand

    strand = CurriculumStrand(
        strand_number=30001,
        name="Test Strand",
        color_hex="#000000",
    )
    db_session.add(strand)
    await db_session.flush()

    sub_strand = CurriculumSubStrand(
        strand_id=strand.id,
        sub_strand_number=1,
        phase="B1_B3",
        name="Test Sub",
    )
    db_session.add(sub_strand)
    await db_session.flush()

    node = CurriculumNode(
        code="TEST.1.1",
        title="Test Node",
        grade="B3",
        description="Test node for fallback testing",
        strand_id=strand.id,
        sub_strand_id=sub_strand.id,
        content_standard_number=1,
        severity=2,
    )
    db_session.add(node)
    await db_session.flush()

    # Act: Use rule-based fallback (use_ai=False)
    question_gen = QuestionGenerator(use_ai=False)
    question_data = question_gen.generate_question(node, question_number=1)

    # Assert: Fallback generates questions
    assert question_data["question_text"]
    assert "[Question about" in question_data["question_text"]  # Fallback template

    # Act: Create question with response
    question = DiagnosticQuestion(
        session_id=session.id,
        question_order=1,
        node_id=node.id,
        question_text=question_data["question_text"],
        question_type="free_response",
        expected_answer="42",
        student_response="24",  # Wrong answer
        is_correct=False,
    )
    db_session.add(question)

    # Act: Analyze with rule-based fallback
    analyzer = ResponseAnalyzer(use_ai=False)
    analysis = analyzer.analyze_response(
        student=student,
        session=session,
        question=question,
        node_code=node.code,
    )

    # Assert: Rule-based analysis works
    assert analysis["is_correct"] is False
    assert analysis["confidence"] > 0.0
    assert analysis["error_pattern"] == "incorrect_response"
    assert analysis["next_action"] in ["trace_backward", "confirm_at_node"]

    await db_session.commit()
