"""
Unit Tests for Question Generator

Tests question generation and answer checking functionality.
"""

import pytest

from gapsense.core.models import CurriculumNode, CurriculumStrand, CurriculumSubStrand
from gapsense.diagnostic import QuestionGenerator


@pytest.fixture
async def test_node(db_session):
    """Create a test curriculum node."""
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

    node = CurriculumNode(
        code="B2.1.1.1",
        grade="B2",
        strand_id=strand.id,
        sub_strand_id=sub_strand.id,
        content_standard_number=1,
        title="Place value to 1000",
        description="Place value assessment",
        severity=5,
        questions_required=2,
    )
    db_session.add(node)
    await db_session.commit()

    return node


@pytest.mark.asyncio
class TestQuestionGenerator:
    """Unit tests for QuestionGenerator class."""

    def test_generate_question_from_template(self, test_node):
        """Test generating question from predefined template."""
        generator = QuestionGenerator(use_ai=False)

        # Generate first question
        q1 = generator.generate_question(test_node, question_number=1)

        assert q1["question_text"] is not None
        assert len(q1["question_text"]) > 0
        assert q1["question_type"] == "free_response"
        assert q1["expected_answer"] is not None
        assert q1["question_media_url"] is None

    def test_generate_multiple_questions_varies_content(self, test_node):
        """Test that multiple questions vary in content."""
        generator = QuestionGenerator(use_ai=False)

        q1 = generator.generate_question(test_node, question_number=1)
        q2 = generator.generate_question(test_node, question_number=2)
        q3 = generator.generate_question(test_node, question_number=3)

        # Questions should be different
        assert q1["question_text"] != q2["question_text"]
        assert q2["question_text"] != q3["question_text"]

    def test_generate_question_for_node_without_template(self, db_session):
        """Test fallback for node without predefined templates."""
        # Create node with code not in templates
        generator = QuestionGenerator(use_ai=False)

        # Mock node without template
        class MockNode:
            code = "UNKNOWN.CODE"
            title = "Unknown Topic"

        node = MockNode()

        question = generator.generate_question(node, question_number=1)

        assert "[Question about Unknown Topic]" in question["question_text"]
        assert question["expected_answer"] is None
        assert question["question_type"] == "free_response"

    def test_check_answer_correct(self):
        """Test answer checking with correct response."""
        generator = QuestionGenerator()

        is_correct, error_pattern = generator.check_answer("460", "460")

        assert is_correct is True
        assert error_pattern is None

    def test_check_answer_incorrect(self):
        """Test answer checking with incorrect response."""
        generator = QuestionGenerator()

        is_correct, error_pattern = generator.check_answer("460", "461")

        assert is_correct is False
        assert error_pattern is not None

    def test_check_answer_case_insensitive(self):
        """Test answer checking is case insensitive."""
        generator = QuestionGenerator()

        is_correct1, _ = generator.check_answer("Yes", "yes")
        is_correct2, _ = generator.check_answer("YES", "yes")

        assert is_correct1 is True
        assert is_correct2 is True

    def test_check_answer_whitespace_handling(self):
        """Test answer checking handles whitespace."""
        generator = QuestionGenerator()

        is_correct1, _ = generator.check_answer(" 460 ", "460")
        is_correct2, _ = generator.check_answer("1/2", "1 / 2")

        assert is_correct1 is True
        assert is_correct2 is True

    def test_check_answer_no_expected_answer(self):
        """Test checking answer when no expected answer provided."""
        generator = QuestionGenerator()

        is_correct, error_pattern = generator.check_answer(None, "some answer")

        assert is_correct is False
        assert error_pattern == "manual_grading_required"

    def test_normalize_answer(self):
        """Test answer normalization."""
        generator = QuestionGenerator()

        normalized1 = generator._normalize_answer("  HELLO World  ")
        normalized2 = generator._normalize_answer("1 / 2")
        normalized3 = generator._normalize_answer("Yes")

        assert normalized1 == "helloworld"
        assert normalized2 == "1/2"
        assert normalized3 == "yes"

    def test_detect_error_pattern(self):
        """Test error pattern detection."""
        generator = QuestionGenerator()

        error = generator._detect_error_pattern("460", "461")

        assert error is not None
        assert error == "incorrect_response"

    def test_ai_generation_fallback(self, test_node):
        """Test that AI generation falls back to templates."""
        generator = QuestionGenerator(use_ai=True)

        question = generator.generate_question(test_node, question_number=1)

        # Should fallback to template since AI not implemented yet
        assert question["question_text"] is not None
        assert len(question["question_text"]) > 0

    def test_all_screening_nodes_have_templates(self):
        """Test that all screening nodes have question templates."""
        from gapsense.diagnostic.adaptive import AdaptiveDiagnosticEngine

        generator = QuestionGenerator()

        for node_code in AdaptiveDiagnosticEngine.SCREENING_NODES:
            assert node_code in generator.TEMPLATES
            assert len(generator.TEMPLATES[node_code]) >= 2  # At least 2 questions per node
