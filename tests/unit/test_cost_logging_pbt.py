"""
Property-based tests for _log_ai_cost prompt_id override.

# Feature: phase3-two-stage-ocr-diagnosis, Property 5: Cost logging respects prompt_id override
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.ai.async_client import AIResponse
from gapsense.ai.cost_calculator import ANTHROPIC_PRICING, calculate_cost
from gapsense.services.image_analysis_context import ImageAnalysisContext
from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Only generate models that exist in the pricing dict so costs are non-zero
_known_models = list(ANTHROPIC_PRICING.keys())

prompt_id_strategy = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
)

token_strategy = st.integers(min_value=1, max_value=500_000)

model_strategy = st.sampled_from(_known_models)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orchestrator(mock_db: AsyncMock) -> ImageAnalysisOrchestrator:
    return ImageAnalysisOrchestrator(
        db=mock_db,
        ai_client=Mock(),
        media_service=Mock(),
        guard_service=Mock(),
        prompt_service=Mock(),
        worker_service=Mock(),
    )


def _make_context() -> ImageAnalysisContext:
    ctx = ImageAnalysisContext(
        s3_key="test/image.jpg",
        student_id="123e4567-e89b-12d3-a456-426614174000",
        country_code="GH",
        language="en",
        teacher_phone="+233501234567",
    )
    student = Mock()
    student.id = UUID("123e4567-e89b-12d3-a456-426614174000")
    student.teacher_id = UUID("223e4567-e89b-12d3-a456-426614174000")
    ctx.student = student
    return ctx


# ---------------------------------------------------------------------------
# Property 5: Cost logging respects prompt_id override
# **Validates: Requirements 7.3, 7.4, 7.5**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    override_prompt_id=prompt_id_strategy,
    response_prompt_id=prompt_id_strategy,
    model=model_strategy,
    input_tokens=token_strategy,
    output_tokens=token_strategy,
)
async def test_cost_logging_uses_override_prompt_id(
    override_prompt_id: str,
    response_prompt_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
):
    """Property 5: When prompt_id override is provided, the AIUsageLog record
    uses the override value, not the response's default prompt_id.

    **Validates: Requirements 7.3, 7.4, 7.5**
    """
    # Arrange
    mock_db = AsyncMock()
    orchestrator = _make_orchestrator(mock_db)
    ctx = _make_context()

    response = AIResponse(
        provider="anthropic",
        model=model,
        prompt_id=response_prompt_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=1500.0,
        text="result",
        json_parsed={"some": "data"},
    )

    # Act
    await orchestrator._log_ai_cost(ctx, response, prompt_id=override_prompt_id)

    # Assert — the AIUsageLog was added with the override prompt_id
    mock_db.add.assert_called_once()
    usage_log = mock_db.add.call_args[0][0]

    assert usage_log.prompt_id == override_prompt_id

    # Assert — total_cost_usd == input_cost_usd + output_cost_usd
    expected_input, expected_output, expected_total = calculate_cost(
        provider="anthropic",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )
    assert usage_log.input_cost_usd == expected_input
    assert usage_log.output_cost_usd == expected_output
    assert usage_log.total_cost_usd == expected_total
    assert usage_log.total_cost_usd == usage_log.input_cost_usd + usage_log.output_cost_usd
