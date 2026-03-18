"""
Property-based tests for AsyncAIClient retry logic.

# Feature: mvp-core-services, Property 1: AI Client Retry Count

Uses Hypothesis to verify that for any sequence of transient errors,
the total number of Anthropic API attempts matches the expected count.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.ai.async_client import AsyncAIClient

# Transient HTTP status codes that trigger retry (must match client.py)
TRANSIENT_CODES = [429, 500, 502, 503, 529]


def _make_anthropic_response(text: str = "ok"):
    """Build a mock Anthropic Messages response."""
    content_block = MagicMock()
    content_block.text = text
    usage = MagicMock()
    usage.input_tokens = 10
    usage.output_tokens = 5
    resp = MagicMock()
    resp.content = [content_block]
    resp.usage = usage
    return resp


def _make_transient_error(status_code: int):
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


# **Validates: Requirements 1.3**
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_errors=st.integers(min_value=0, max_value=20),
    error_codes=st.lists(
        st.sampled_from(TRANSIENT_CODES),
        min_size=1,
        max_size=20,
    ),
)
async def test_retry_count_property(num_errors: int, error_codes: list[int]):
    """Property 1: AI Client Retry Count

    For any sequence of transient errors, verify total attempts =
    min(N+1, 4) when N < 4, exactly 4 when N >= 4.

    Where N is the number of consecutive transient errors before a
    potential success, and max_retries=3 (so max total attempts = 4).
    """
    max_retries = 3
    max_total_attempts = max_retries + 1  # 4

    # Build the side_effect sequence: num_errors transient errors,
    # then a success response (if we get that far)
    side_effects: list = []
    for i in range(num_errors):
        code = error_codes[i % len(error_codes)]
        side_effects.append(_make_transient_error(code))
    # Append a success at the end so the client can succeed if it reaches it
    side_effects.append(_make_anthropic_response("success"))

    client = AsyncAIClient(
        anthropic_api_key="test-key",
        max_retries=max_retries,
    )
    client._anthropic.messages.create = AsyncMock(side_effect=side_effects)

    with patch("gapsense.ai.async_client.asyncio.sleep", new_callable=AsyncMock):
        result = await client.generate(
            prompt_id="PBT-001",
            system="test",
            messages=[{"role": "user", "content": "hi"}],
        )

    actual_attempts = client._anthropic.messages.create.call_count

    if num_errors < max_total_attempts:
        # Client should have made num_errors failed attempts + 1 success
        expected_attempts = num_errors + 1
        assert actual_attempts == expected_attempts, (
            f"With {num_errors} transient errors (< {max_total_attempts}), "
            f"expected {expected_attempts} attempts but got {actual_attempts}"
        )
        # Should have succeeded
        assert result is not None, (
            f"With {num_errors} transient errors (< {max_total_attempts}), "
            f"expected a successful response but got None"
        )
    else:
        # Client should have exhausted all attempts
        expected_attempts = max_total_attempts
        assert actual_attempts == expected_attempts, (
            f"With {num_errors} transient errors (>= {max_total_attempts}), "
            f"expected exactly {expected_attempts} attempts but got {actual_attempts}"
        )
        # Anthropic exhausted; no grok key → None
        assert result is None, (
            f"With {num_errors} transient errors (>= {max_total_attempts}), "
            f"expected None (all retries exhausted) but got a response"
        )
