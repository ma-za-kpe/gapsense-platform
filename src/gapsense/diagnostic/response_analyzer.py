"""
Response Analysis Service

Uses AI (DIAG-002 prompt) to analyze student responses and detect
error patterns, misconceptions, and determine next diagnostic action.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gapsense.core.models import DiagnosticQuestion, DiagnosticSession, Student


class ResponseAnalyzer:
    """Analyzes student responses using AI to detect patterns and guide diagnosis.

    Uses DIAG-002 prompt to:
    - Determine correctness (beyond string matching)
    - Identify error patterns and misconceptions
    - Recommend next diagnostic action (trace backward, confirm, etc.)
    """

    def __init__(self, use_ai: bool = True):
        """Initialize response analyzer.

        Args:
            use_ai: Whether to use AI analysis (default: True)
        """
        self.use_ai = use_ai

    def analyze_response(
        self,
        *,
        student: Student,
        session: DiagnosticSession,
        question: DiagnosticQuestion,
        node_code: str,
    ) -> dict[str, Any]:
        """Analyze student response to determine correctness and next action.

        Args:
            student: Student who answered
            session: Current diagnostic session
            question: Question with student_response filled in
            node_code: Code of curriculum node being tested

        Returns:
            Dict with:
                - is_correct: bool
                - confidence: float (0.0-1.0)
                - error_pattern: str | None
                - misconception: str | None
                - next_action: Literal["confirm_at_node", "trace_backward", "move_forward", "conclude_branch"]
                - reasoning: str (AI explanation)
        """
        if self.use_ai:
            return self._analyze_with_ai(
                student=student,
                session=session,
                question=question,
                node_code=node_code,
            )
        else:
            return self._analyze_rule_based(question)

    def _analyze_with_ai(
        self,
        *,
        student: Student,
        session: DiagnosticSession,
        question: DiagnosticQuestion,
        node_code: str,
    ) -> dict[str, Any]:
        """Analyze response using DIAG-002 AI prompt.

        Args:
            student: Student who answered
            session: Current diagnostic session
            question: Question with student_response
            node_code: Curriculum node code

        Returns:
            Analysis dict with is_correct, error_pattern, next_action, etc.
        """
        try:
            from anthropic import Anthropic

            from gapsense.ai import get_prompt_library
            from gapsense.config import settings

            # Get DIAG-002 prompt
            lib = get_prompt_library()
            prompt = lib.get_prompt("DIAG-002")

            # Build session history
            session_history = self._build_session_history(session)

            # Build context for AI
            context = {
                "student_first_name": student.first_name or "Student",
                "current_grade": student.current_grade,
                "age": str(student.age) if student.age else "unknown",
                "home_language": student.home_language or "English",
                "current_node_code": node_code,
                "question_text": question.question_text,
                "question_type": question.question_type,
                "expected_answer": question.expected_answer or "No expected answer provided",
                "student_response": question.student_response or "",
                "response_time_seconds": str(question.response_time_seconds or 0),
                "session_history_json": json.dumps(session_history, indent=2),
            }

            # Format user message from template
            user_message = prompt["user_template"]
            for key, value in context.items():
                user_message = user_message.replace(f"{{{{{key}}}}}", str(value))

            # Call Claude API
            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

            response = client.messages.create(
                model=prompt["model"],
                max_tokens=prompt["max_tokens"],
                temperature=prompt["temperature"],
                system=prompt["system_prompt"],
                messages=[{"role": "user", "content": user_message}],
            )

            # Parse response
            content_block = response.content[0]
            if not hasattr(content_block, "text"):
                # Fallback to rule-based
                return self._analyze_rule_based(question)

            response_data = json.loads(content_block.text)

            # Extract fields from AI response
            return {
                "is_correct": response_data.get("is_correct", False),
                "confidence": response_data.get("confidence", 0.5),
                "error_pattern": response_data.get("error_pattern"),
                "misconception": response_data.get("misconception_match"),
                "next_action": response_data.get("next_action", "confirm_at_node"),
                "reasoning": response_data.get("reasoning", ""),
            }

        except Exception:
            # Fallback to rule-based on any error
            return self._analyze_rule_based(question)

    def _analyze_rule_based(self, question: DiagnosticQuestion) -> dict[str, Any]:
        """Simple rule-based analysis as fallback.

        Args:
            question: Question with student_response

        Returns:
            Basic analysis dict
        """
        expected = question.expected_answer
        student_response = question.student_response

        if not expected or not student_response:
            # No expected answer or no response, can't determine correctness
            return {
                "is_correct": False,
                "confidence": 0.0,
                "error_pattern": "manual_grading_required",
                "misconception": None,
                "next_action": "confirm_at_node",
                "reasoning": "No expected answer or student response available",
            }

        # Normalize for comparison
        expected_norm = self._normalize_answer(expected)
        response_norm = self._normalize_answer(student_response)

        is_correct = expected_norm == response_norm

        return {
            "is_correct": is_correct,
            "confidence": 0.9 if is_correct else 0.7,
            "error_pattern": None if is_correct else "incorrect_response",
            "misconception": None,
            "next_action": "move_forward" if is_correct else "trace_backward",
            "reasoning": "Rule-based string matching",
        }

    def _normalize_answer(self, answer: str) -> str:
        """Normalize answer for comparison.

        Args:
            answer: Raw answer string

        Returns:
            Normalized answer (lowercase, no spaces, trimmed)
        """
        return answer.lower().strip().replace(" ", "")

    def _build_session_history(self, session: DiagnosticSession) -> list[dict[str, Any]]:
        """Build session Q&A history for AI context.

        Args:
            session: Diagnostic session

        Returns:
            List of Q&A dicts with question, response, correctness
        """
        # TODO: Query actual session questions and answers from database
        # For now, return empty list as placeholder

        return []
