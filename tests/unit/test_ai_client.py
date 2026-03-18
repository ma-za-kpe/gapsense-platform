"""
Unit tests for AsyncAIClient.

Tests instantiation, retry logic, fallback, concurrency, and logging.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gapsense.ai.async_client import AIResponse, AsyncAIClient, ImageContent

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_anthropic_response(text: str = "hello", input_tokens: int = 10, output_tokens: int = 5):
    """Build a mock Anthropic Messages response."""
    content_block = MagicMock()
    content_block.text = text
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    resp = MagicMock()
    resp.content = [content_block]
    resp.usage = usage
    return resp


def _make_grok_response(
    text: str = "grok-hello", prompt_tokens: int = 8, completion_tokens: int = 4
):
    """Build a mock OpenAI-compatible chat completion response."""
    message = MagicMock()
    message.content = text
    choice = MagicMock()
    choice.message = message
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


def _make_transient_error(status_code: int = 429):
    """Create an anthropic.APIStatusError with the given status code."""
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
# Instantiation
# ---------------------------------------------------------------------------


class TestAsyncAIClientInstantiation:
    """Test that AsyncAIClient can be created with various configurations."""

    def test_instantiation_with_anthropic_key_only(self):
        client = AsyncAIClient(anthropic_api_key="test-key")
        assert client._anthropic is not None
        assert client._grok_api_key is None

    def test_instantiation_with_both_keys(self):
        client = AsyncAIClient(anthropic_api_key="test-key", grok_api_key="grok-key")
        assert client._anthropic is not None
        assert client._grok_api_key == "grok-key"

    def test_default_parameters(self):
        client = AsyncAIClient(anthropic_api_key="test-key")
        assert client._timeout_seconds == 30.0
        assert client._max_retries == 3
        # Semaphore internal value
        assert client._semaphore._value == 10

    def test_custom_parameters(self):
        client = AsyncAIClient(
            anthropic_api_key="test-key",
            max_concurrent=5,
            timeout_seconds=15.0,
            max_retries=2,
        )
        assert client._timeout_seconds == 15.0
        assert client._max_retries == 2
        assert client._semaphore._value == 5


# ---------------------------------------------------------------------------
# Retry logic
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """Test exponential backoff retry on transient errors."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_error_then_succeeds(self):
        """Transient 429 on first two attempts, success on third."""
        client = AsyncAIClient(anthropic_api_key="test-key", max_retries=3)

        error_429 = _make_transient_error(429)
        success_resp = _make_anthropic_response("ok")

        client._anthropic.messages.create = AsyncMock(
            side_effect=[error_429, error_429, success_resp]
        )

        with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate(
                prompt_id="TEST-001",
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result is not None
        assert result.text == "ok"
        assert result.provider == "anthropic"
        assert client._anthropic.messages.create.call_count == 3

    @pytest.mark.asyncio
    async def test_exhausts_all_retries(self):
        """All 4 attempts (1 initial + 3 retries) fail with transient errors."""
        client = AsyncAIClient(anthropic_api_key="test-key", max_retries=3)

        error_500 = _make_transient_error(500)
        client._anthropic.messages.create = AsyncMock(
            side_effect=[error_500, error_500, error_500, error_500]
        )

        with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate(
                prompt_id="TEST-001",
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )

        # Anthropic exhausted → no grok key → None
        assert result is None
        assert client._anthropic.messages.create.call_count == 4

    @pytest.mark.asyncio
    async def test_no_retry_on_non_transient_error(self):
        """Non-transient errors (e.g. 401) should not be retried."""
        client = AsyncAIClient(anthropic_api_key="test-key", max_retries=3)

        error_401 = _make_transient_error(401)
        client._anthropic.messages.create = AsyncMock(side_effect=error_401)

        with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.generate(
                prompt_id="TEST-001",
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result is None
        # Only 1 attempt — no retries for non-transient
        assert client._anthropic.messages.create.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_various_transient_codes(self):
        """All transient codes (429, 500, 502, 503, 529) trigger retry."""
        for code in [429, 500, 502, 503, 529]:
            client = AsyncAIClient(anthropic_api_key="test-key", max_retries=1)
            error = _make_transient_error(code)
            success = _make_anthropic_response("ok")
            client._anthropic.messages.create = AsyncMock(side_effect=[error, success])

            with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
                result = await client.generate(
                    prompt_id="TEST-001",
                    system="test",
                    messages=[{"role": "user", "content": "hi"}],
                )

            assert result is not None, f"Expected success after retry on {code}"
            assert client._anthropic.messages.create.call_count == 2


# ---------------------------------------------------------------------------
# Fallback to Grok
# ---------------------------------------------------------------------------


class TestFallbackToGrok:
    """Test that Grok is attempted when Anthropic fails."""

    @pytest.mark.asyncio
    async def test_falls_back_to_grok_on_anthropic_failure(self):
        """When Anthropic exhausts retries, Grok should be tried."""
        client = AsyncAIClient(
            anthropic_api_key="test-key",
            grok_api_key="grok-key",
            max_retries=0,  # No retries — fail immediately
        )

        error = _make_transient_error(500)
        client._anthropic.messages.create = AsyncMock(side_effect=error)

        # Pre-set the Grok client mock so the lazy import is bypassed
        grok_resp = _make_grok_response("grok-answer")
        mock_grok = AsyncMock()
        mock_grok.chat.completions.create = AsyncMock(return_value=grok_resp)
        mock_grok.close = AsyncMock()
        client._grok_client = mock_grok

        result = await client.generate(
            prompt_id="TEST-001",
            system="test",
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result is not None
        assert result.provider == "grok"
        assert result.text == "grok-answer"

    @pytest.mark.asyncio
    async def test_no_grok_fallback_without_key(self):
        """Without a Grok key, fallback is skipped."""
        client = AsyncAIClient(anthropic_api_key="test-key", max_retries=0)

        error = _make_transient_error(500)
        client._anthropic.messages.create = AsyncMock(side_effect=error)

        result = await client.generate(
            prompt_id="TEST-001",
            system="test",
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result is None


# ---------------------------------------------------------------------------
# All providers fail → None
# ---------------------------------------------------------------------------


class TestAllProvidersFail:
    """Test that None is returned when all providers fail."""

    @pytest.mark.asyncio
    async def test_returns_none_when_both_fail(self):
        client = AsyncAIClient(
            anthropic_api_key="test-key",
            grok_api_key="grok-key",
            max_retries=0,
        )

        error = _make_transient_error(500)
        client._anthropic.messages.create = AsyncMock(side_effect=error)

        # Pre-set the Grok client mock
        mock_grok = AsyncMock()
        mock_grok.chat.completions.create = AsyncMock(side_effect=Exception("grok down"))
        mock_grok.close = AsyncMock()
        client._grok_client = mock_grok

        result = await client.generate(
            prompt_id="TEST-001",
            system="test",
            messages=[{"role": "user", "content": "hi"}],
        )

        assert result is None


# ---------------------------------------------------------------------------
# Concurrency limit (semaphore)
# ---------------------------------------------------------------------------


class TestConcurrencyLimit:
    """Test that the semaphore enforces the concurrency limit."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrent_requests(self):
        """With max_concurrent=2, at most 2 requests should be in-flight."""
        max_concurrent = 2
        client = AsyncAIClient(
            anthropic_api_key="test-key",
            max_concurrent=max_concurrent,
            max_retries=0,
        )

        in_flight = 0
        max_in_flight = 0
        lock = asyncio.Lock()

        original_create = AsyncMock(return_value=_make_anthropic_response("ok"))

        async def tracked_create(**kwargs):
            nonlocal in_flight, max_in_flight
            async with lock:
                in_flight += 1
                max_in_flight = max(in_flight, max_in_flight)
            await asyncio.sleep(0.05)  # Simulate work
            result = await original_create(**kwargs)
            async with lock:
                in_flight -= 1
            return result

        client._anthropic.messages.create = tracked_create

        # Fire 6 concurrent requests
        tasks = [
            client.generate(
                prompt_id=f"TEST-{i}",
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )
            for i in range(6)
        ]
        results = await asyncio.gather(*tasks)

        assert all(r is not None for r in results)
        assert max_in_flight <= max_concurrent


# ---------------------------------------------------------------------------
# Logging completeness
# ---------------------------------------------------------------------------


class TestLoggingCompleteness:
    """Test that every AI call logs the required fields."""

    @pytest.mark.asyncio
    async def test_success_log_contains_required_fields(self):
        client = AsyncAIClient(anthropic_api_key="test-key", max_retries=0)
        client._anthropic.messages.create = AsyncMock(
            return_value=_make_anthropic_response("ok", input_tokens=15, output_tokens=7)
        )

        with patch("gapsense.ai.async_client.logger") as mock_logger:
            await client.generate(
                prompt_id="LOG-001",
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )

            # Find the success log call
            info_calls = mock_logger.info.call_args_list
            assert len(info_calls) >= 1
            call_kwargs = info_calls[0][1]
            assert call_kwargs["provider"] == "anthropic"
            assert call_kwargs["prompt_id"] == "LOG-001"
            assert "latency_ms" in call_kwargs
            assert call_kwargs["input_tokens"] == 15
            assert call_kwargs["output_tokens"] == 7
            assert call_kwargs["success"] is True

    @pytest.mark.asyncio
    async def test_failure_log_contains_required_fields(self):
        client = AsyncAIClient(anthropic_api_key="test-key", max_retries=0)
        error = _make_transient_error(500)
        client._anthropic.messages.create = AsyncMock(side_effect=error)

        with patch("gapsense.ai.async_client.logger") as mock_logger:
            await client.generate(
                prompt_id="LOG-002",
                system="test",
                messages=[{"role": "user", "content": "hi"}],
            )

            # Find the transient error warning log
            warn_calls = mock_logger.warning.call_args_list
            transient_call = None
            for call in warn_calls:
                if call[0] and call[0][0] == "ai_call_transient_error":
                    transient_call = call
                    break

            assert transient_call is not None
            kw = transient_call[1]
            assert kw["provider"] == "anthropic"
            assert kw["prompt_id"] == "LOG-002"
            assert "latency_ms" in kw
            assert kw["success"] is False


# ---------------------------------------------------------------------------
# Dataclass tests
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Test ImageContent and AIResponse dataclasses."""

    def test_image_content_creation(self):
        img = ImageContent(data="base64data", media_type="image/jpeg", source_type="base64")
        assert img.data == "base64data"
        assert img.media_type == "image/jpeg"
        assert img.source_type == "base64"

    def test_ai_response_creation(self):
        resp = AIResponse(
            text="hello",
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            prompt_id="TEST-001",
            latency_ms=123.4,
            input_tokens=10,
            output_tokens=5,
        )
        assert resp.text == "hello"
        assert resp.json_parsed is None

    def test_ai_response_with_json_parsed(self):
        resp = AIResponse(
            text='{"key": "value"}',
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            prompt_id="TEST-001",
            latency_ms=100.0,
            input_tokens=10,
            output_tokens=5,
            json_parsed={"key": "value"},
        )
        assert resp.json_parsed == {"key": "value"}
