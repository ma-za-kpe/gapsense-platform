"""
Property-based tests for AsyncAIClient provider cascade and logging.

# Feature: mvp-core-services, Property 2: Provider Cascade Fallback
# Feature: mvp-core-services, Property 3: AI Concurrency Limit
# Feature: mvp-core-services, Property 4: AI Call Logging Completeness
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.ai.async_client import AsyncAIClient


def _make_anthropic_response(text: str = "ok"):
    content_block = MagicMock()
    content_block.text = text
    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    resp = MagicMock()
    resp.content = [content_block]
    resp.usage = usage
    return resp


def _make_grok_response(text: str = "grok-ok"):
    choice = MagicMock()
    choice.message.content = text
    usage = MagicMock()
    usage.prompt_tokens = 8
    usage.completion_tokens = 4
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def _make_transient_error(status_code: int):
    import anthropic

    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.headers = {}
    return anthropic.APIStatusError(
        message=f"Error {status_code}",
        response=mock_response,
        body=None,
    )


# ---------------------------------------------------------------------------
# Property 2: Provider Cascade Fallback
# **Validates: Requirements 1.7, 1.8**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    anthropic_succeeds=st.booleans(),
    grok_succeeds=st.booleans(),
    has_grok_key=st.booleans(),
)
async def test_provider_cascade_fallback(
    anthropic_succeeds: bool,
    grok_succeeds: bool,
    has_grok_key: bool,
):
    """Property 2: Provider Cascade Fallback

    When Anthropic fails after retries, Grok is attempted.
    When both fail, None is returned.
    Result is non-None iff at least one provider succeeded.
    """
    client = AsyncAIClient(
        anthropic_api_key="test-key",
        grok_api_key="grok-key" if has_grok_key else None,
        max_retries=0,  # No retries — test cascade only
    )

    # Configure Anthropic mock
    if anthropic_succeeds:
        client._anthropic.messages.create = AsyncMock(return_value=_make_anthropic_response())
    else:
        client._anthropic.messages.create = AsyncMock(side_effect=_make_transient_error(500))

    # Configure Grok mock
    if has_grok_key:
        from openai import AsyncOpenAI

        mock_grok = MagicMock(spec=AsyncOpenAI)
        mock_grok.close = AsyncMock()
        if grok_succeeds:
            mock_grok.chat.completions.create = AsyncMock(return_value=_make_grok_response())
        else:
            mock_grok.chat.completions.create = AsyncMock(side_effect=Exception("Grok failed"))
        client._grok_client = mock_grok

    with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.generate(
            prompt_id="PBT-002",
            system="test",
            messages=[{"role": "user", "content": "hi"}],
        )

    if anthropic_succeeds:
        # Anthropic succeeded — should return Anthropic response
        assert result is not None
        assert result.provider == "anthropic"
    elif has_grok_key and grok_succeeds:
        # Anthropic failed, Grok succeeded
        assert result is not None
        assert result.provider == "grok"
    else:
        # Both failed or no Grok key
        assert result is None


# ---------------------------------------------------------------------------
# Property 3: AI Concurrency Limit
# **Validates: Requirements 1.9**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    num_requests=st.integers(min_value=2, max_value=30),
    concurrency_limit=st.integers(min_value=1, max_value=5),
)
async def test_ai_concurrency_limit(num_requests: int, concurrency_limit: int):
    """Property 3: AI Concurrency Limit

    For any batch of N simultaneous requests exceeding the concurrency limit,
    in-flight count never exceeds semaphore limit.
    """
    max_in_flight = 0
    current_in_flight = 0
    lock = asyncio.Lock()

    async def slow_create(**kwargs):
        nonlocal max_in_flight, current_in_flight
        async with lock:
            current_in_flight += 1
            max_in_flight = max(current_in_flight, max_in_flight)
        await asyncio.sleep(0.01)
        async with lock:
            current_in_flight -= 1
        return _make_anthropic_response()

    client = AsyncAIClient(
        anthropic_api_key="test-key",
        max_concurrent=concurrency_limit,
    )
    client._anthropic.messages.create = AsyncMock(side_effect=slow_create)

    tasks = [
        client.generate(
            prompt_id=f"PBT-003-{i}",
            system="test",
            messages=[{"role": "user", "content": "hi"}],
        )
        for i in range(num_requests)
    ]
    await asyncio.gather(*tasks)

    assert (
        max_in_flight <= concurrency_limit
    ), f"Max in-flight {max_in_flight} exceeded concurrency limit {concurrency_limit}"


# ---------------------------------------------------------------------------
# Property 4: AI Call Logging Completeness
# **Validates: Requirements 1.10**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    succeeds=st.booleans(),
    prompt_id=st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
        min_size=1,
        max_size=20,
    ),
)
async def test_ai_call_logging_completeness(succeeds: bool, prompt_id: str):
    """Property 4: AI Call Logging Completeness

    For any AI call (success or failure), verify log record contains
    provider, prompt_id, latency_ms, token usage, success/failure.
    """
    client = AsyncAIClient(
        anthropic_api_key="test-key",
        max_retries=0,
    )

    if succeeds:
        client._anthropic.messages.create = AsyncMock(return_value=_make_anthropic_response())
    else:
        client._anthropic.messages.create = AsyncMock(side_effect=_make_transient_error(500))

    log_records = []

    def capture_log(logger, method_name, event_dict):
        log_records.append(event_dict)
        return event_dict

    with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
        import structlog

        with structlog.testing.capture_logs() as captured:
            await client.generate(
                prompt_id=prompt_id,
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )

    # Find the relevant log entries (success or failure)
    ai_logs = [
        log
        for log in captured
        if log.get("event")
        in (
            "ai_call_success",
            "ai_call_failed",
            "ai_call_transient_error",
            "ai_call_timeout",
        )
    ]

    assert len(ai_logs) > 0, "Expected at least one AI call log entry"

    for log in ai_logs:
        assert "provider" in log, f"Log missing 'provider': {log}"
        assert "prompt_id" in log, f"Log missing 'prompt_id': {log}"
        assert "latency_ms" in log, f"Log missing 'latency_ms': {log}"
        assert "success" in log, f"Log missing 'success': {log}"
        assert log["prompt_id"] == prompt_id

        if log.get("success"):
            assert "input_tokens" in log, f"Success log missing 'input_tokens': {log}"
            assert "output_tokens" in log, f"Success log missing 'output_tokens': {log}"
