"""
Unit tests for GuardService.

Tests pass-through, fail-closed, violation parsing, and logging completeness.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gapsense.ai.async_client import AIResponse
from gapsense.ai.prompt_service import RenderedPrompt
from gapsense.services.guard_service import GuardResult, GuardService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rendered_prompt(
    prompt_id: str = "GUARD-001",
    system_prompt: str = "You are a compliance checker.",
    user_template: str | None = None,
) -> RenderedPrompt:
    return RenderedPrompt(
        prompt_id=prompt_id,
        system_prompt=system_prompt,
        user_template=user_template,
        model="claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_tokens=2048,
        country="GH",
        language="en",
    )


def _make_ai_response(
    *,
    passed: bool = True,
    violations: list[str] | None = None,
    text: str | None = None,
    json_parsed: dict | None = None,
    latency_ms: float = 150.0,
) -> AIResponse:
    if json_parsed is None:
        json_parsed = {
            "passed": passed,
            "violations": violations or [],
        }
    if text is None:
        import json

        text = json.dumps(json_parsed)
    return AIResponse(
        text=text,
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        prompt_id="GUARD-001",
        latency_ms=latency_ms,
        input_tokens=100,
        output_tokens=50,
        json_parsed=json_parsed,
    )


def _make_guard_service(
    ai_response: AIResponse | None = None,
    rendered_prompt: RenderedPrompt | None = None,
) -> tuple[GuardService, AsyncMock, MagicMock]:
    """Create a GuardService with mocked dependencies.

    Returns (service, mock_ai_client, mock_prompt_service).
    """
    mock_ai_client = AsyncMock()
    mock_ai_client.generate = AsyncMock(return_value=ai_response)

    mock_prompt_service = MagicMock()
    mock_prompt_service.render_prompt = MagicMock(
        return_value=rendered_prompt or _make_rendered_prompt()
    )

    service = GuardService(
        ai_client=mock_ai_client,
        prompt_service=mock_prompt_service,
    )
    return service, mock_ai_client, mock_prompt_service


# ---------------------------------------------------------------------------
# GuardResult dataclass
# ---------------------------------------------------------------------------


class TestGuardResultDataclass:
    def test_default_values(self):
        result = GuardResult(passed=True, original_message="hello")
        assert result.passed is True
        assert result.original_message == "hello"
        assert result.violations == []
        assert result.latency_ms == 0.0
        assert result.ai_available is True

    def test_failed_result(self):
        result = GuardResult(
            passed=False,
            original_message="bad msg",
            violations=["deficit_language"],
            latency_ms=200.0,
            ai_available=True,
        )
        assert result.passed is False
        assert result.violations == ["deficit_language"]


# ---------------------------------------------------------------------------
# Pass-through: message passes GUARD-001
# ---------------------------------------------------------------------------


class TestPassThrough:
    """Req 6.3: When GUARD-001 returns pass, return original message unchanged."""

    @pytest.mark.asyncio
    async def test_pass_returns_original_message(self):
        ai_resp = _make_ai_response(passed=True, violations=[])
        service, mock_ai, mock_ps = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Great job on your homework!",
            student_context={"name": "Kofi", "grade": "B2"},
            country="GH",
            language="en",
        )

        assert result.passed is True
        assert result.original_message == "Great job on your homework!"
        assert result.violations == []
        assert result.ai_available is True

    @pytest.mark.asyncio
    async def test_pass_with_empty_violations(self):
        ai_resp = _make_ai_response(passed=True, violations=[])
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Let's practice counting together.",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.passed is True
        assert result.violations == []


# ---------------------------------------------------------------------------
# Fail: message fails GUARD-001
# ---------------------------------------------------------------------------


class TestFailBlocking:
    """Req 6.4: When GUARD-001 returns fail, return violations and block."""

    @pytest.mark.asyncio
    async def test_fail_returns_violations(self):
        ai_resp = _make_ai_response(
            passed=False,
            violations=["deficit_language", "labeling"],
        )
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Your child is struggling badly.",
            student_context={"name": "Ama"},
            country="GH",
            language="en",
        )

        assert result.passed is False
        assert result.violations == ["deficit_language", "labeling"]
        assert result.ai_available is True
        assert result.original_message == "Your child is struggling badly."

    @pytest.mark.asyncio
    async def test_fail_with_single_violation(self):
        ai_resp = _make_ai_response(
            passed=False,
            violations=["inappropriate_content"],
        )
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Bad message",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.passed is False
        assert len(result.violations) == 1


# ---------------------------------------------------------------------------
# Fail-closed: AI client returns None
# ---------------------------------------------------------------------------


class TestFailClosed:
    """Req 6.5: When AI client returns None, block message."""

    @pytest.mark.asyncio
    async def test_none_response_blocks_message(self):
        service, _, _ = _make_guard_service(ai_response=None)

        result = await service.check(
            "Hello parent!",
            student_context={"name": "Kofi"},
            country="GH",
            language="en",
        )

        assert result.passed is False
        assert result.ai_available is False
        assert "ai_unavailable" in result.violations
        assert result.original_message == "Hello parent!"

    @pytest.mark.asyncio
    async def test_none_response_logs_compliance_check_unavailable(self):
        service, _, _ = _make_guard_service(ai_response=None)

        with patch("gapsense.services.guard_service.logger") as mock_logger:
            await service.check(
                "Hello parent!",
                student_context={},
                country="GH",
                language="en",
            )

            # Verify the compliance-check-unavailable log
            warn_calls = mock_logger.warning.call_args_list
            assert len(warn_calls) >= 1
            found = False
            for call in warn_calls:
                if call[0] and call[0][0] == "compliance-check-unavailable":
                    found = True
                    kw = call[1]
                    assert kw["prompt_id"] == "GUARD-001"
                    assert kw["passed"] is False
                    break
            assert found, "Expected 'compliance-check-unavailable' log not found"


# ---------------------------------------------------------------------------
# Response parsing edge cases
# ---------------------------------------------------------------------------


class TestResponseParsing:
    """Test parsing of various AI response formats."""

    @pytest.mark.asyncio
    async def test_json_parse_failure_blocks_message(self):
        """When json_parsed is None (parse failed), fail-closed."""
        ai_resp = AIResponse(
            text="not valid json",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            prompt_id="GUARD-001",
            latency_ms=100.0,
            input_tokens=50,
            output_tokens=20,
            json_parsed=None,
        )
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Test message",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.passed is False
        assert "response_parse_error" in result.violations
        assert result.ai_available is True

    @pytest.mark.asyncio
    async def test_violations_as_non_list_converted(self):
        """When violations is not a list, it should be converted."""
        ai_resp = _make_ai_response(
            passed=False,
            json_parsed={"passed": False, "violations": "single_violation"},
        )
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Test",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.passed is False
        assert result.violations == ["single_violation"]

    @pytest.mark.asyncio
    async def test_missing_passed_field_defaults_to_false(self):
        """When 'passed' field is missing from JSON, default to False."""
        ai_resp = _make_ai_response(
            json_parsed={"violations": ["something"]},
        )
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Test",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.passed is False


# ---------------------------------------------------------------------------
# AI client interaction
# ---------------------------------------------------------------------------


class TestAIClientInteraction:
    """Test that GuardService correctly calls the AI client."""

    @pytest.mark.asyncio
    async def test_calls_ai_client_with_json_mode(self):
        ai_resp = _make_ai_response(passed=True)
        service, mock_ai, _ = _make_guard_service(ai_response=ai_resp)

        await service.check(
            "Hello",
            student_context={"grade": "B2"},
            country="GH",
            language="en",
        )

        mock_ai.generate.assert_called_once()
        call_kwargs = mock_ai.generate.call_args[1]
        assert call_kwargs["json_mode"] is True
        assert call_kwargs["prompt_id"] == "GUARD-001"

    @pytest.mark.asyncio
    async def test_calls_prompt_service_with_correct_params(self):
        ai_resp = _make_ai_response(passed=True)
        service, _, mock_ps = _make_guard_service(ai_response=ai_resp)

        await service.check(
            "Hello",
            student_context={"name": "Kofi"},
            country="GH",
            language="tw",
        )

        mock_ps.render_prompt.assert_called_once_with(
            "GUARD-001",
            country="GH",
            language="tw",
            extra_context={
                "message": "Hello",
                "student_context": "{'name': 'Kofi'}",
            },
        )

    @pytest.mark.asyncio
    async def test_uses_user_template_when_available(self):
        rendered = _make_rendered_prompt(user_template="Check this message: {{message}}")
        ai_resp = _make_ai_response(passed=True)
        service, mock_ai, _ = _make_guard_service(
            ai_response=ai_resp,
            rendered_prompt=rendered,
        )

        await service.check(
            "Hello",
            student_context={},
            country="GH",
            language="en",
        )

        call_kwargs = mock_ai.generate.call_args[1]
        assert call_kwargs["messages"][0]["content"] == "Check this message: {{message}}"


# ---------------------------------------------------------------------------
# Logging completeness
# ---------------------------------------------------------------------------


class TestLoggingCompleteness:
    """Req 6.7: Log prompt_id, pass/fail, latency_ms, violations for every check."""

    @pytest.mark.asyncio
    async def test_pass_log_contains_required_fields(self):
        ai_resp = _make_ai_response(passed=True)
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        with patch("gapsense.services.guard_service.logger") as mock_logger:
            await service.check(
                "Good message",
                student_context={},
                country="GH",
                language="en",
            )

            info_calls = mock_logger.info.call_args_list
            guard_call = None
            for call in info_calls:
                if call[0] and call[0][0] == "guard_check_complete":
                    guard_call = call
                    break

            assert guard_call is not None, "Expected 'guard_check_complete' log"
            kw = guard_call[1]
            assert kw["prompt_id"] == "GUARD-001"
            assert kw["passed"] is True
            assert "latency_ms" in kw
            assert kw["violations"] == []

    @pytest.mark.asyncio
    async def test_fail_log_contains_violations(self):
        ai_resp = _make_ai_response(
            passed=False,
            violations=["deficit_language", "labeling"],
        )
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        with patch("gapsense.services.guard_service.logger") as mock_logger:
            await service.check(
                "Bad message",
                student_context={},
                country="GH",
                language="en",
            )

            info_calls = mock_logger.info.call_args_list
            guard_call = None
            for call in info_calls:
                if call[0] and call[0][0] == "guard_check_complete":
                    guard_call = call
                    break

            assert guard_call is not None
            kw = guard_call[1]
            assert kw["prompt_id"] == "GUARD-001"
            assert kw["passed"] is False
            assert kw["violations"] == ["deficit_language", "labeling"]

    @pytest.mark.asyncio
    async def test_fail_closed_log_contains_required_fields(self):
        service, _, _ = _make_guard_service(ai_response=None)

        with patch("gapsense.services.guard_service.logger") as mock_logger:
            await service.check(
                "Message",
                student_context={},
                country="GH",
                language="en",
            )

            warn_calls = mock_logger.warning.call_args_list
            unavailable_call = None
            for call in warn_calls:
                if call[0] and call[0][0] == "compliance-check-unavailable":
                    unavailable_call = call
                    break

            assert unavailable_call is not None
            kw = unavailable_call[1]
            assert kw["prompt_id"] == "GUARD-001"
            assert kw["passed"] is False
            assert "latency_ms" in kw
            assert "violations" in kw


# ---------------------------------------------------------------------------
# Latency tracking
# ---------------------------------------------------------------------------


class TestLatencyTracking:
    """Test that latency_ms is tracked for all check outcomes."""

    @pytest.mark.asyncio
    async def test_latency_is_positive_on_pass(self):
        ai_resp = _make_ai_response(passed=True)
        service, _, _ = _make_guard_service(ai_response=ai_resp)

        result = await service.check(
            "Hello",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_latency_is_positive_on_fail_closed(self):
        service, _, _ = _make_guard_service(ai_response=None)

        result = await service.check(
            "Hello",
            student_context={},
            country="GH",
            language="en",
        )

        assert result.latency_ms >= 0
