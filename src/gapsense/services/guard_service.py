"""
GUARD-001 Compliance Gate for Parent-Facing Messages

Validates all outbound parent-facing messages against Wolf/Aurino
dignity-first principles using the GUARD-001 prompt. Implements
fail-closed semantics: if AI is unavailable, messages are blocked.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from gapsense.ai.async_client import AsyncAIClient
from gapsense.ai.prompt_service import PromptService

logger = structlog.get_logger(__name__)


@dataclass
class GuardResult:
    """Result of a GUARD-001 compliance check."""

    passed: bool
    original_message: str
    violations: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    ai_available: bool = True


class GuardService:
    """GUARD-001 compliance gate for parent-facing messages."""

    PROMPT_ID = "GUARD-001"

    def __init__(
        self,
        ai_client: AsyncAIClient,
        prompt_service: PromptService,
    ) -> None:
        self._ai_client = ai_client
        self._prompt_service = prompt_service

    async def check(
        self,
        message: str,
        *,
        student_context: dict[str, Any],
        country: str,
        language: str,
    ) -> GuardResult:
        """Validate message against Wolf/Aurino dignity-first principles.

        Blocks message if AI client unavailable (fail-closed).
        """
        start = time.perf_counter()

        # Render the GUARD-001 prompt with country/language context
        rendered = self._prompt_service.render_prompt(
            self.PROMPT_ID,
            country=country,
            language=language,
            extra_context={
                "message": message,
                "student_context": str(student_context),
            },
        )

        # Build user message content
        user_content = message
        if rendered.user_template:
            user_content = rendered.user_template

        # Send to AI client with json_mode for structured response
        response = await self._ai_client.generate(
            prompt_id=self.PROMPT_ID,
            system=rendered.system_prompt,
            messages=[{"role": "user", "content": user_content}],
            model=rendered.model,
            max_tokens=rendered.max_tokens,
            temperature=rendered.temperature,
            json_mode=True,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        # Fail-closed: if AI client returns None, block the message
        if response is None:
            logger.warning(
                "compliance-check-unavailable",
                prompt_id=self.PROMPT_ID,
                passed=False,
                latency_ms=round(latency_ms, 2),
                violations=["ai_unavailable"],
            )
            return GuardResult(
                passed=False,
                original_message=message,
                violations=["ai_unavailable"],
                latency_ms=latency_ms,
                ai_available=False,
            )

        # Parse structured JSON response
        passed, violations = self._parse_response(response.json_parsed, response.text)

        # Log every check
        logger.info(
            "guard_check_complete",
            prompt_id=self.PROMPT_ID,
            passed=passed,
            latency_ms=round(latency_ms, 2),
            violations=violations,
        )

        return GuardResult(
            passed=passed,
            original_message=message,
            violations=violations,
            latency_ms=latency_ms,
            ai_available=True,
        )

    @staticmethod
    def _parse_response(
        json_parsed: dict[str, Any] | None,
        raw_text: str,
    ) -> tuple[bool, list[str]]:
        """Parse AI response for pass/fail and violations.

        Expected JSON format:
            {"passed": true/false, "violations": [...]}

        Returns (passed, violations) tuple.
        """
        if json_parsed is not None:
            passed = bool(json_parsed.get("passed", False))
            violations = json_parsed.get("violations", [])
            if not isinstance(violations, list):
                violations = [str(violations)]
            # Ensure all violations are strings
            violations = [str(v) for v in violations]
            return passed, violations if not passed else []

        # Fallback: if JSON parsing failed, treat as a failure (fail-closed)
        logger.warning(
            "guard_response_parse_failed",
            raw_text=raw_text[:200],
        )
        return False, ["response_parse_error"]
