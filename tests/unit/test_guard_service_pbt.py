"""
Property-based tests for GuardService.

# Feature: mvp-core-services, Property 10: Guard Service Pass-Through Invariant
# Feature: mvp-core-services, Property 11: Guard Service Fail-Closed
# Feature: mvp-core-services, Property 12: Guard Service Logging Completeness
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import structlog.testing
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.ai.async_client import AIResponse
from gapsense.ai.prompt_service import PromptService, RenderedPrompt
from gapsense.services.guard_service import GuardService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_prompt_service() -> PromptService:
    svc = MagicMock(spec=PromptService)
    svc.render_prompt.return_value = RenderedPrompt(
        prompt_id="GUARD-001",
        system_prompt="You are a compliance checker.",
        user_template=None,
        model="claude-sonnet-4-5",
        temperature=0.3,
        max_tokens=2048,
        country="GH",
        language="en",
    )
    return svc


def _make_pass_response(prompt_id: str = "GUARD-001") -> AIResponse:
    return AIResponse(
        text='{"passed": true, "violations": []}',
        provider="anthropic",
        model="claude-sonnet-4-5",
        prompt_id=prompt_id,
        latency_ms=100.0,
        input_tokens=50,
        output_tokens=20,
        json_parsed={"passed": True, "violations": []},
    )


def _make_fail_response(violations: list[str], prompt_id: str = "GUARD-001") -> AIResponse:
    return AIResponse(
        text=f'{{"passed": false, "violations": {violations}}}',
        provider="anthropic",
        model="claude-sonnet-4-5",
        prompt_id=prompt_id,
        latency_ms=100.0,
        input_tokens=50,
        output_tokens=20,
        json_parsed={"passed": False, "violations": violations},
    )


# ---------------------------------------------------------------------------
# Property 10: Guard Service Pass-Through Invariant
# **Validates: Requirements 6.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    message=st.text(min_size=1, max_size=200),
)
async def test_guard_pass_through_invariant(message: str):
    """Property 10: Guard Service Pass-Through Invariant

    For any message that passes GUARD-001, original_message equals input,
    passed=True, and violations is empty.
    """
    ai_client = MagicMock()
    ai_client.generate = AsyncMock(return_value=_make_pass_response())
    prompt_svc = _mock_prompt_service()

    guard = GuardService(ai_client, prompt_svc)
    result = await guard.check(
        message,
        student_context={"name": "Test"},
        country="GH",
        language="en",
    )

    assert result.passed is True
    assert result.original_message == message
    assert result.violations == []
    assert result.ai_available is True


# ---------------------------------------------------------------------------
# Property 11: Guard Service Fail-Closed
# **Validates: Requirements 6.5**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    message=st.text(min_size=1, max_size=200),
)
async def test_guard_fail_closed(message: str):
    """Property 11: Guard Service Fail-Closed

    When AI client returns None, passed=False and ai_available=False.
    """
    ai_client = MagicMock()
    ai_client.generate = AsyncMock(return_value=None)
    prompt_svc = _mock_prompt_service()

    guard = GuardService(ai_client, prompt_svc)
    result = await guard.check(
        message,
        student_context={"name": "Test"},
        country="GH",
        language="en",
    )

    assert result.passed is False
    assert result.ai_available is False
    assert result.original_message == message


# ---------------------------------------------------------------------------
# Property 12: Guard Service Logging Completeness
# **Validates: Requirements 6.7**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    message=st.text(min_size=1, max_size=100),
    passes=st.booleans(),
)
async def test_guard_logging_completeness(message: str, passes: bool):
    """Property 12: Guard Service Logging Completeness

    For any guard check (pass or fail), log contains prompt_id,
    pass/fail, latency_ms, violation categories.
    """
    ai_client = MagicMock()
    if passes:
        ai_client.generate = AsyncMock(return_value=_make_pass_response())
    else:
        ai_client.generate = AsyncMock(return_value=_make_fail_response(["dignity_violation"]))
    prompt_svc = _mock_prompt_service()

    guard = GuardService(ai_client, prompt_svc)

    with structlog.testing.capture_logs() as captured:
        await guard.check(
            message,
            student_context={"name": "Test"},
            country="GH",
            language="en",
        )

    # Find the guard_check_complete log entry
    guard_logs = [log for log in captured if log.get("event") == "guard_check_complete"]

    assert len(guard_logs) >= 1, f"Expected guard_check_complete log, got: {captured}"

    log = guard_logs[0]
    assert "prompt_id" in log, f"Log missing 'prompt_id': {log}"
    assert "passed" in log, f"Log missing 'passed': {log}"
    assert "latency_ms" in log, f"Log missing 'latency_ms': {log}"
    assert "violations" in log, f"Log missing 'violations': {log}"
    assert log["prompt_id"] == "GUARD-001"
    assert log["passed"] == passes
