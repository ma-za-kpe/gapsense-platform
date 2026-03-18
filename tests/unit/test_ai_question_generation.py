"""
Unit Tests for AI Question Generation

Tests AI-powered question generation using DIAG-001 prompt.
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


class TestAIQuestionGeneration:
    """Unit tests for AI-powered question generation."""

    def test_ai_generation_fallback_on_error(self, test_node):
        """Test that AI generation falls back to templates on error."""
        # use_ai=True but will fail (no API key or network error)
        generator = QuestionGenerator(use_ai=True)

        question = generator.generate_question(test_node, question_number=1)

        # Should fallback to template
        assert question["question_text"] is not None
        assert len(question["question_text"]) > 0
        assert question["question_type"] in ["free_response", "multiple_choice"]

    def test_ai_flag_disabled_uses_templates(self, test_node):
        """Test that AI is not used when use_ai=False."""
        generator = QuestionGenerator(use_ai=False)

        question = generator.generate_question(test_node, question_number=1)

        # Should use template
        assert question["question_text"] is not None
        assert "459" in question["question_text"] or "hundred" in question["question_text"].lower()
