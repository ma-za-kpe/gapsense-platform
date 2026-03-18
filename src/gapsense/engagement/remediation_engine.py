"""
RemediationEngine — Teacher-facing remediation exercise generator

Generates 3-5 classroom-ready practice questions per gap node using
the REMEDIATION-001 prompt. Questions target specific misconceptions
identified in exercise book analysis and are validated through GUARD-001.

Design: Inline generation (not async queue). Fail-open for exercises,
fail-closed for guard violations.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from gapsense.ai.async_client import AsyncAIClient
    from gapsense.ai.prompt_service import PromptService
    from gapsense.services.guard_service import GuardService

logger = structlog.get_logger(__name__)


@dataclass
class RemediationExercise:
    """A single remediation practice question with teacher guidance."""

    question: str
    expected_answer: str
    teacher_note: str
    gap_node_code: str


class RemediationEngine:
    """Generates teacher-facing remediation exercises for identified gap nodes."""

    PROMPT_ID = "REMEDIATION-001"

    def __init__(
        self,
        *,
        ai_client: AsyncAIClient,
        prompt_service: PromptService,
        guard_service: GuardService,
    ) -> None:
        self._ai_client = ai_client
        self._prompt_service = prompt_service
        self._guard_service = guard_service

    async def generate_exercises(
        self,
        *,
        gap_nodes: list[dict[str, Any]],
        student_grade: str,
        country: str,
        language: str = "en",
    ) -> list[dict[str, Any]]:
        """Generate remediation exercises for gap nodes.

        Args:
            gap_nodes: List of dicts with keys: code, title, error_patterns, misconception
            student_grade: Student's current grade (e.g., "B6", "JHS1")
            country: Country code for cultural context (e.g., "ghana")
            language: Language code (default "en")

        Returns:
            List of exercise dicts with schema:
            [{"question": str, "expected_answer": str, "teacher_note": str, "gap_node_code": str}]

            Returns empty list [] on any failure (fail-open for exercises).
        """
        try:
            # Handle empty gap nodes gracefully
            if not gap_nodes:
                logger.info(
                    "remediation_skipped",
                    reason="no_gap_nodes",
                    student_grade=student_grade,
                    country=country,
                )
                return []

            # Format gap nodes for the prompt template
            gap_nodes_section = self._format_gap_nodes_for_prompt(gap_nodes)

            # Render REMEDIATION-001 prompt with gap node details, grade, country
            rendered = self._prompt_service.render_prompt(
                self.PROMPT_ID,
                country=country,
                language=language,
                extra_context={
                    "student_grade": student_grade,
                    "gap_nodes_section": gap_nodes_section,
                    "home_language": language,
                    "school_language": "en",  # Default to English for now
                },
            )

            # Build user message content
            user_content = rendered.user_template if rendered.user_template else gap_nodes_section

            # Call AI client with json_mode=True for structured output
            response = await self._ai_client.generate(
                prompt_id=self.PROMPT_ID,
                system=rendered.system_prompt,
                messages=[{"role": "user", "content": user_content}],
                model=rendered.model,
                max_tokens=rendered.max_tokens,
                temperature=rendered.temperature,
                json_mode=True,
            )

            # If AI client returns None, fail-open (return empty list)
            if response is None:
                logger.warning(
                    "remediation_failed",
                    reason="ai_unavailable",
                    prompt_id=self.PROMPT_ID,
                    gap_node_count=len(gap_nodes),
                )
                return []

            # Parse JSON response into exercise list
            exercises_raw = json.loads(response.text)

            # Validate that we got a list
            if not isinstance(exercises_raw, list):
                logger.warning(
                    "remediation_failed",
                    reason="invalid_response_not_list",
                    prompt_id=self.PROMPT_ID,
                    response_type=type(exercises_raw).__name__,
                )
                return []

            # Filter out malformed exercises (missing required fields)
            exercises_valid = []
            for exercise in exercises_raw:
                if self._validate_exercise_schema(exercise):
                    exercises_valid.append(exercise)
                else:
                    logger.debug(
                        "remediation_exercise_filtered",
                        reason="missing_required_fields",
                        exercise=exercise,
                    )

            # If no valid exercises, fail-open
            if not exercises_valid:
                logger.warning(
                    "remediation_failed",
                    reason="no_valid_exercises",
                    prompt_id=self.PROMPT_ID,
                    total_generated=len(exercises_raw),
                )
                return []

            # Concatenate all exercise text for guard check
            combined_text = self._concatenate_exercises_for_guard(exercises_valid)

            # Pass through GuardService.check()
            guard_result = await self._guard_service.check(
                combined_text,
                student_context={"grade": student_grade, "gap_node_count": len(gap_nodes)},
                country=country,
                language=language,
            )

            # If guard fails, fail-closed (return empty list, log violations)
            if not guard_result.passed:
                logger.warning(
                    "remediation_rejected_by_guard",
                    prompt_id=self.PROMPT_ID,
                    violations=guard_result.violations,
                    exercise_count=len(exercises_valid),
                )
                return []

            # Guard passed — return exercises
            logger.info(
                "remediation_success",
                prompt_id=self.PROMPT_ID,
                exercise_count=len(exercises_valid),
                gap_node_count=len(gap_nodes),
                guard_latency_ms=round(guard_result.latency_ms, 2),
            )
            return exercises_valid

        except json.JSONDecodeError as e:
            logger.error(
                "remediation_failed",
                reason="json_parse_error",
                prompt_id=self.PROMPT_ID,
                error=str(e),
            )
            return []

        except Exception as e:
            # Catch-all: fail-open for any unexpected errors
            logger.error(
                "remediation_failed",
                reason="unexpected_error",
                prompt_id=self.PROMPT_ID,
                error=str(e),
                error_type=type(e).__name__,
            )
            return []

    def _format_gap_nodes_for_prompt(self, gap_nodes: list[dict[str, Any]]) -> str:
        """Format gap nodes into a structured string for the prompt.

        Args:
            gap_nodes: List of gap node dicts

        Returns:
            Formatted string with gap node details
        """
        sections = []
        for idx, node in enumerate(gap_nodes, start=1):
            code = node.get("code", "UNKNOWN")
            title = node.get("title", "Unknown concept")
            error_patterns = node.get("error_patterns", "Not specified")
            misconception = node.get("misconception", "Not specified")

            section = (
                f"Gap Node {idx}:\n"
                f"  Code: {code}\n"
                f"  Title: {title}\n"
                f"  Error Patterns: {error_patterns}\n"
                f"  Misconception: {misconception}\n"
            )
            sections.append(section)

        return "\n".join(sections)

    def _validate_exercise_schema(self, exercise: Any) -> bool:
        """Validate that an exercise has all required fields with non-empty string values.

        Args:
            exercise: Exercise object to validate

        Returns:
            True if exercise has valid schema, False otherwise
        """
        if not isinstance(exercise, dict):
            return False

        required_fields = ["question", "expected_answer", "teacher_note", "gap_node_code"]

        for field in required_fields:
            if field not in exercise:
                return False
            if not isinstance(exercise[field], str):
                return False
            if not exercise[field].strip():
                return False

        return True

    def _concatenate_exercises_for_guard(self, exercises: list[dict[str, Any]]) -> str:
        """Concatenate all exercise text for guard validation.

        Args:
            exercises: List of exercise dicts

        Returns:
            Combined text string
        """
        parts = []
        for exercise in exercises:
            question = exercise.get("question", "")
            answer = exercise.get("expected_answer", "")
            note = exercise.get("teacher_note", "")

            if question:
                parts.append(question)
            if answer:
                parts.append(answer)
            if note:
                parts.append(note)

        return " ".join(parts)
