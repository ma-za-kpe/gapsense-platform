"""
Question Generation Service

Generates diagnostic questions for curriculum nodes.
Initially uses rule-based templates, will integrate AI (DIAG-001) later.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gapsense.core.models import CurriculumNode


class QuestionGenerator:
    """Generates questions for diagnostic assessment.

    Current implementation: Rule-based templates per node
    Future: AI-powered generation using DIAG-001 prompt
    """

    # Question templates by node code
    # Format: (question_text, expected_answer, question_type)
    TEMPLATES = {
        "B2.1.1.1": [
            ("What number comes after 459?", "460", "free_response"),
            ("Write the number: four hundred and twenty-three", "423", "free_response"),
            ("Which is bigger: 567 or 576?", "576", "free_response"),
        ],
        "B1.1.2.2": [
            ("What is 47 - 23?", "24", "free_response"),
            (
                "Kofi had 65 cedis. He spent 32 cedis. How much does he have left?",
                "33",
                "free_response",
            ),
            ("What is 80 - 45?", "35", "free_response"),
        ],
        "B2.1.2.2": [
            (
                "Ama has 4 baskets. Each basket has 5 mangoes. How many mangoes in total?",
                "20",
                "free_response",
            ),
            ("What is 3 × 6?", "18", "free_response"),
            (
                "A teacher has 7 boxes. Each box has 4 pencils. How many pencils total?",
                "28",
                "free_response",
            ),
        ],
        "B2.1.3.1": [
            ("What fraction of this circle is shaded? [Half shaded]", "1/2", "free_response"),
            (
                "Kwame ate 1/4 of a kenkey. How many parts was the kenkey divided into?",
                "4",
                "free_response",
            ),
            ("Which is larger: 1/2 or 1/4?", "1/2", "free_response"),
        ],
        "B3.1.3.1": [
            ("Are 1/2 and 2/4 the same amount?", "yes", "free_response"),
            ("What fraction is the same as 1/2? (Choose: 2/4, 1/4, 3/4)", "2/4", "free_response"),
            ("If you have 2/6 and 1/3, are they equal?", "yes", "free_response"),
        ],
        "B4.1.3.1": [
            ("What is 1/2 + 1/4?", "3/4", "free_response"),
            (
                "Akosua ate 1/3 of a pizza. Her brother ate 1/6. How much did they eat together?",
                "1/2",
                "free_response",
            ),
            ("What is 3/4 - 1/2?", "1/4", "free_response"),
        ],
    }

    def __init__(self, use_ai: bool = False):
        """Initialize question generator.

        Args:
            use_ai: Whether to use AI generation (not yet implemented)
        """
        self.use_ai = use_ai

    def generate_question(
        self, node: CurriculumNode, question_number: int
    ) -> dict[str, str | None]:
        """Generate a question for the given node.

        Args:
            node: Curriculum node to test
            question_number: Question sequence number (for variation)

        Returns:
            Dict with:
                - question_text: str
                - expected_answer: str | None
                - question_type: str
                - question_media_url: str | None
        """
        if self.use_ai:
            return self._generate_with_ai(node, question_number)
        else:
            return self._generate_from_template(node, question_number)

    def _generate_from_template(
        self, node: CurriculumNode, question_number: int
    ) -> dict[str, str | None]:
        """Generate question from predefined templates.

        Args:
            node: Curriculum node
            question_number: Question sequence number

        Returns:
            Question dict
        """
        templates = self.TEMPLATES.get(node.code, [])

        if not templates:
            # Fallback for nodes without templates
            return {
                "question_text": f"[Question about {node.title}]",
                "expected_answer": None,
                "question_type": "free_response",
                "question_media_url": None,
            }

        # Select template based on question number (cyclic)
        template_index = question_number % len(templates)
        question_text, expected_answer, question_type = templates[template_index]

        return {
            "question_text": question_text,
            "expected_answer": expected_answer,
            "question_type": question_type,
            "question_media_url": None,
        }

    def _generate_with_ai(
        self, node: CurriculumNode, question_number: int
    ) -> dict[str, str | None]:
        """Generate question using AI (DIAG-001 prompt).

        Args:
            node: Curriculum node
            question_number: Question sequence number

        Returns:
            Question dict
        """
        # TODO: Implement AI question generation
        # Will use DIAG-001 prompt from prompt library
        # For now, fallback to templates
        return self._generate_from_template(node, question_number)

    def check_answer(
        self, expected_answer: str | None, student_response: str
    ) -> tuple[bool, str | None]:
        """Check if student response matches expected answer.

        Args:
            expected_answer: Expected answer string
            student_response: Student's response

        Returns:
            Tuple of (is_correct, error_pattern)
        """
        if not expected_answer:
            # No expected answer means manual grading needed
            return (False, "manual_grading_required")

        # Normalize responses
        expected = self._normalize_answer(expected_answer)
        response = self._normalize_answer(student_response)

        is_correct = expected == response

        # Detect error patterns (simplified)
        error_pattern = None
        if not is_correct:
            error_pattern = self._detect_error_pattern(expected, response)

        return (is_correct, error_pattern)

    def _normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison.

        Args:
            answer: Raw answer string

        Returns:
            Normalized answer
        """
        return answer.lower().strip().replace(" ", "")

    def _detect_error_pattern(self, expected: str, response: str) -> str | None:
        """Detect common error patterns.

        Args:
            expected: Expected answer (normalized)
            response: Student response (normalized)

        Returns:
            Error pattern identifier or None
        """
        # TODO: Implement sophisticated error pattern detection
        # For now, return generic error
        return "incorrect_response"
