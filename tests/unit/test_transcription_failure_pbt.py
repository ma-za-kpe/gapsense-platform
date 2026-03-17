"""
Property-based tests for Stage 1 failure graceful degradation.

# Feature: phase3-two-stage-ocr-diagnosis, Property 2: Stage 1 failure never crashes the pipeline
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.services.image_analysis_context import ImageAnalysisContext
from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

# ---------------------------------------------------------------------------
# Helpers (same pattern as test_cost_logging_pbt.py)
# ---------------------------------------------------------------------------


def _make_orchestrator(
    mock_db: AsyncMock,
    ai_client: AsyncMock | Mock | None = None,
    prompt_service: Mock | None = None,
) -> ImageAnalysisOrchestrator:
    return ImageAnalysisOrchestrator(
        db=mock_db,
        ai_client=ai_client or AsyncMock(),
        media_service=Mock(),
        guard_service=Mock(),
        prompt_service=prompt_service or Mock(),
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
    # _transcribe_image needs image_bytes and media_type
    ctx.image_bytes = b"\x89PNG\r\n\x1a\nfake-image-data"
    ctx.media_type = "image/png"
    return ctx


# ---------------------------------------------------------------------------
# Strategies — failure scenarios
# ---------------------------------------------------------------------------

# Random exception types and messages
_exception_strategy = st.one_of(
    st.just(RuntimeError("AI client connection failed")),
    st.just(ValueError("Invalid response format")),
    st.just(TimeoutError("Request timed out")),
    st.just(TypeError("Unexpected type")),
    st.just(KeyError("missing_key")),
    st.just(Exception("Generic failure")),
    st.builds(
        RuntimeError,
        st.text(
            min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P"))
        ),
    ),
)

# Random malformed JSON dicts (missing "questions" key)
_malformed_json_strategy = st.fixed_dictionaries(
    {},
    optional={
        "layout": st.text(min_size=0, max_size=50),
        "subject_detected": st.text(min_size=0, max_size=50),
        "not_questions": st.lists(
            st.dictionaries(st.text(max_size=10), st.text(max_size=10)), max_size=5
        ),
    },
)

# Combine all failure scenario types into a tagged union
_failure_scenario = st.one_of(
    st.just(("ai_raises", None)),
    st.just(("ai_returns_none", None)),
    st.just(("json_parsed_none", None)),
    _malformed_json_strategy.map(lambda d: ("malformed_json", d)),
    st.just(("prompt_service_raises", None)),
)


# ---------------------------------------------------------------------------
# Property 2: Stage 1 failure never crashes the pipeline
# **Validates: Requirements 2.5, 2.6**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    failure=_failure_scenario,
    exception=_exception_strategy,
)
async def test_stage1_failure_never_crashes_pipeline(
    failure: tuple[str, object],
    exception: Exception,
):
    """Property 2: For any failure mode during _transcribe_image, the method
    sets ctx.transcription_result to {} and ctx.transcription_text to "",
    and does not raise an exception.

    **Validates: Requirements 2.5, 2.6**
    """
    scenario, data = failure
    mock_db = AsyncMock()
    ai_client = AsyncMock()
    prompt_service = Mock()

    # Configure a valid render_prompt return by default
    rendered = Mock()
    rendered.system_prompt = "Transcribe this."
    rendered.model = "claude-sonnet-4-6"
    rendered.max_tokens = 2048
    rendered.temperature = 0.1
    prompt_service.render_prompt.return_value = rendered

    if scenario == "ai_raises":
        # AI client raises an exception
        ai_client.generate = AsyncMock(side_effect=exception)

    elif scenario == "ai_returns_none":
        # AI client returns None
        ai_client.generate = AsyncMock(return_value=None)

    elif scenario == "json_parsed_none":
        # AI client returns a response with json_parsed=None
        response = Mock()
        response.json_parsed = None
        ai_client.generate = AsyncMock(return_value=response)

    elif scenario == "malformed_json":
        # AI client returns a response with malformed JSON (missing "questions" key)
        # This won't crash but will produce empty transcription_text
        response = Mock()
        response.json_parsed = data  # dict without "questions"
        response.prompt_id = "TRANSCRIPTION-001"
        response.model = "claude-sonnet-4-6"
        response.input_tokens = 100
        response.output_tokens = 50
        response.latency_ms = 500.0
        response.provider = "anthropic"
        ai_client.generate = AsyncMock(return_value=response)

    elif scenario == "prompt_service_raises":
        # prompt_service.render_prompt raises an exception
        prompt_service.render_prompt.side_effect = exception

    orchestrator = _make_orchestrator(mock_db, ai_client=ai_client, prompt_service=prompt_service)
    ctx = _make_context()

    # Act — must not raise
    await orchestrator._transcribe_image(ctx)

    # Assert — for all failure scenarios except malformed_json (which is a
    # partial success), the context should have safe defaults.
    if scenario == "malformed_json":
        # malformed_json is actually parsed successfully — json_parsed is a
        # valid dict, just missing "questions". The method stores it in
        # transcription_result and produces empty transcription_text.
        assert ctx.transcription_result == data
        assert ctx.transcription_text == ""
    else:
        assert (
            ctx.transcription_result == {}
        ), f"Expected empty dict for scenario {scenario!r}, got {ctx.transcription_result!r}"
        assert (
            ctx.transcription_text == ""
        ), f"Expected empty string for scenario {scenario!r}, got {ctx.transcription_text!r}"
