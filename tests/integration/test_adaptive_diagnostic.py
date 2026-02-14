"""
Integration Tests for Adaptive Diagnostic Flow

Tests the complete adaptive diagnostic assessment flow from session creation
through answer submission, adaptive question selection, to gap profile generation.
"""

import pytest

from gapsense.core.models import (
    CurriculumNode,
    CurriculumStrand,
    CurriculumSubStrand,
    DiagnosticSession,
    Parent,
    Student,
)
from gapsense.diagnostic import (
    AdaptiveDiagnosticEngine,
    GapProfileAnalyzer,
    QuestionGenerator,
)


@pytest.fixture
async def diagnostic_setup(db_session):
    """Create parent, student, and curriculum nodes for diagnostic testing."""
    # Create parent
    parent = Parent(
        phone="+233244987654",
        preferred_name="Yaa Asantewaa",
        preferred_language="en",
    )
    db_session.add(parent)
    await db_session.flush()

    # Create student
    student = Student(
        first_name="Kwabena",
        current_grade="B3",
        primary_parent_id=parent.id,
    )
    db_session.add(student)
    await db_session.flush()

    # Create curriculum structure
    strand = CurriculumStrand(
        strand_number=1,
        name="Number",
        color_hex="#2563EB",
    )
    db_session.add(strand)
    await db_session.flush()

    sub_strand = CurriculumSubStrand(
        strand_id=strand.id,
        sub_strand_number=1,
        phase="B1_B3",
        name="Whole Numbers",
    )
    db_session.add(sub_strand)
    await db_session.flush()

    # Create screening nodes
    nodes = []
    node_configs = [
        ("B2.1.1.1", "B2", "Place value to 1000", 5),
        ("B1.1.2.2", "B1", "Subtraction within 100", 5),
        ("B2.1.2.2", "B2", "Multiplication concept", 4),
        ("B2.1.3.1", "B2", "Fraction concept", 4),
        ("B3.1.3.1", "B3", "Fraction equivalence", 3),
        ("B4.1.3.1", "B4", "Fraction operations", 3),
    ]

    for code, grade, title, severity in node_configs:
        node = CurriculumNode(
            code=code,
            grade=grade,
            strand_id=strand.id,
            sub_strand_id=sub_strand.id,
            content_standard_number=1,
            title=title,
            description=f"{title} assessment",
            severity=severity,
            questions_required=2,
        )
        nodes.append(node)
        db_session.add(node)

    await db_session.commit()

    return {
        "parent": parent,
        "student": student,
        "nodes": {node.code: node for node in nodes},
    }


@pytest.mark.asyncio
class TestAdaptiveDiagnosticFlow:
    """Integration tests for complete adaptive diagnostic flow."""

    async def test_complete_diagnostic_session_with_gaps(self, db_session, diagnostic_setup):
        """Test complete diagnostic flow detecting a gap."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        # Create session
        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            channel="whatsapp",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        # Initialize engine
        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Simulate answering questions - student struggles with B2 content
        # Answer B2.1.1.1 incorrectly (place value gap)
        node_b2_place = nodes["B2.1.1.1"]
        await engine.update_session_state(node_b2_place.id, is_correct=False)
        session.total_questions += 1

        await engine.update_session_state(node_b2_place.id, is_correct=False)
        session.total_questions += 1

        # Should trace backward to B1 content
        next_node = await engine.get_next_node()
        assert next_node is not None
        assert next_node.code == "B1.1.2.2"  # Should test B1 subtraction

        # Answer B1 correctly (showing B1 mastery)
        await engine.update_session_state(next_node.id, is_correct=True)
        session.total_questions += 1

        await engine.update_session_state(next_node.id, is_correct=True)
        session.total_questions += 1

        # Verify session state
        assert node_b2_place.id in session.nodes_gap
        assert next_node.id in session.nodes_mastered
        assert session.root_gap_node_id == node_b2_place.id

    async def test_adaptive_engine_screening_phase(self, db_session, diagnostic_setup):
        """Test that adaptive engine screens priority nodes first."""
        student = diagnostic_setup["student"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # First node should be a screening node
        first_node = await engine.get_next_node()
        assert first_node is not None
        assert first_node.code in engine.SCREENING_NODES

        # After testing first node twice, should move to next screening node
        await engine.update_session_state(first_node.id, is_correct=True)
        session.total_questions += 1

        await engine.update_session_state(first_node.id, is_correct=True)
        session.total_questions += 1

        second_node = await engine.get_next_node()
        assert second_node is not None
        assert second_node.code != first_node.code
        assert second_node.code in engine.SCREENING_NODES

    async def test_session_completion_logic(self, db_session, diagnostic_setup):
        """Test that session completes after max questions or root gap found."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Simulate reaching max questions
        session.total_questions = engine.MAX_QUESTIONS
        should_complete = await engine.should_complete_session()
        assert should_complete is True

        # Reset and test root gap completion
        session.total_questions = 8
        session.root_gap_node_id = nodes["B2.1.1.1"].id
        session.root_gap_confidence = 0.85

        should_complete = await engine.should_complete_session()
        assert should_complete is True

    async def test_gap_profile_generation(self, db_session, diagnostic_setup):
        """Test gap profile generation from completed session."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        # Create completed session with identified gaps
        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="completed",
            total_questions=10,
            correct_answers=5,
            root_gap_node_id=nodes["B2.1.1.1"].id,
            root_gap_confidence=0.85,
        )
        session.nodes_mastered = [nodes["B1.1.2.2"].id]
        session.nodes_gap = [nodes["B2.1.1.1"].id, nodes["B2.1.2.2"].id]

        db_session.add(session)
        await db_session.commit()

        # Generate gap profile
        analyzer = GapProfileAnalyzer(session, db_session)
        gap_profile = await analyzer.generate_gap_profile()

        assert gap_profile is not None
        assert gap_profile.student_id == student.id
        assert gap_profile.session_id == session.id
        assert gap_profile.primary_gap_node == nodes["B2.1.1.1"].id
        assert gap_profile.estimated_grade_level == "B1"  # Highest mastered
        assert gap_profile.grade_gap == 2  # B3 - B1
        assert gap_profile.is_current is True
        assert len(gap_profile.mastered_nodes) > 0
        assert len(gap_profile.gap_nodes) > 0

    async def test_question_generator_produces_valid_questions(self, db_session, diagnostic_setup):
        """Test that question generator creates valid questions."""
        nodes = diagnostic_setup["nodes"]
        generator = QuestionGenerator()

        # Test question generation for each screening node
        for node_code in AdaptiveDiagnosticEngine.SCREENING_NODES:
            if node_code in nodes:
                node = nodes[node_code]

                # Generate first question
                q1 = generator.generate_question(node, question_number=1)
                assert q1["question_text"] is not None
                assert len(q1["question_text"]) > 0
                assert q1["question_type"] == "free_response"
                assert q1["expected_answer"] is not None

                # Generate second question (should be different)
                q2 = generator.generate_question(node, question_number=2)
                assert q2["question_text"] != q1["question_text"]

    async def test_gap_profile_deactivates_previous_profiles(self, db_session, diagnostic_setup):
        """Test that new gap profile deactivates previous ones."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        # Create first session and gap profile
        session1 = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="completed",
            total_questions=8,
        )
        session1.nodes_mastered = [nodes["B1.1.2.2"].id]
        db_session.add(session1)
        await db_session.flush()

        analyzer1 = GapProfileAnalyzer(session1, db_session)
        profile1 = await analyzer1.generate_gap_profile()
        db_session.add(profile1)
        await db_session.commit()

        assert profile1.is_current is True

        # Create second session and gap profile
        session2 = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="completed",
            total_questions=10,
        )
        session2.nodes_mastered = [nodes["B2.1.1.1"].id]
        db_session.add(session2)
        await db_session.flush()

        analyzer2 = GapProfileAnalyzer(session2, db_session)
        profile2 = await analyzer2.generate_gap_profile()
        db_session.add(profile2)
        await db_session.commit()

        # Refresh first profile to see changes
        await db_session.refresh(profile1)

        assert profile1.is_current is False
        assert profile2.is_current is True

    async def test_adaptive_backward_tracing(self, db_session, diagnostic_setup):
        """Test that engine traces backward through prerequisites when gap found."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Mark B2.1.1.1 as gap (place value)
        b2_node = nodes["B2.1.1.1"]
        await engine.update_session_state(b2_node.id, is_correct=False)
        session.total_questions += 1

        await engine.update_session_state(b2_node.id, is_correct=False)
        session.total_questions += 1

        # Verify it's marked as gap
        assert b2_node.id in session.nodes_gap

        # Get next node - should trace backward to prerequisites
        # (Note: This requires prerequisite relationships to be set up in curriculum)
        next_node = await engine.get_next_node()
        if next_node:
            # Next node should be different from the gap node
            assert next_node.id != b2_node.id

    async def test_max_questions_completion(self, db_session, diagnostic_setup):
        """Test that session stops after MAX_QUESTIONS."""
        student = diagnostic_setup["student"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
            total_questions=15,  # Already at MAX_QUESTIONS
        )
        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Should return None when at max questions
        next_node = await engine.get_next_node()
        assert next_node is None

    async def test_no_screening_node_found(self, db_session, diagnostic_setup):
        """Test behavior when screening node doesn't exist in database."""
        student = diagnostic_setup["student"]

        # Delete all nodes
        from sqlalchemy import delete

        from gapsense.core.models import CurriculumNode

        await db_session.execute(delete(CurriculumNode))
        await db_session.commit()

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Should return None when no screening nodes exist
        next_node = await engine.get_next_node()
        assert next_node is None

    async def test_all_screening_complete_no_gaps(self, db_session, diagnostic_setup):
        """Test completion when all screening nodes tested with no gaps."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
            total_questions=12,  # All screening complete (6 nodes * 2 questions)
        )
        # Mark all as mastered (use IDs, not objects)
        session.nodes_mastered = [node.id for node in nodes.values()]
        session.nodes_gap = []  # No gaps

        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Should complete since all screening done and no gaps
        should_complete = await engine.should_complete_session()
        assert should_complete is True

    async def test_count_questions_for_node(self, db_session, diagnostic_setup):
        """Test counting questions asked for specific node."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
        )
        session.nodes_tested = [
            nodes["B2.1.1.1"].id,
            nodes["B2.1.1.1"].id,
            nodes["B1.1.2.2"].id,
        ]

        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # Count for B2.1.1.1 should be 2
        count1 = engine._count_questions_for_node(nodes["B2.1.1.1"].id)
        assert count1 == 2

        # Count for B1.1.2.2 should be 1
        count2 = engine._count_questions_for_node(nodes["B1.1.2.2"].id)
        assert count2 == 1

        # Count for untested node should be 0
        count3 = engine._count_questions_for_node(nodes["B2.1.2.2"].id)
        assert count3 == 0

    async def test_update_session_state_uncertain(self, db_session, diagnostic_setup):
        """Test update_session_state with insufficient questions."""
        student = diagnostic_setup["student"]
        nodes = diagnostic_setup["nodes"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        engine = AdaptiveDiagnosticEngine(session, db_session)

        # First answer - should be uncertain
        result = await engine.update_session_state(nodes["B2.1.1.1"].id, is_correct=True)

        assert result["node_status"] == "uncertain"
        assert result["confidence"] == 0.5
