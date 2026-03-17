"""
Property-based tests for query text preference logic.

# Feature: phase3-two-stage-ocr-diagnosis, Property 3: Query text prefers transcription over image description
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
# Strategies
# ---------------------------------------------------------------------------

# Non-empty transcription text — printable strings with at least 1 char
transcription_text_strategy = st.text(
    min_size=1,
    max_size=500,
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
).filter(lambda s: s.strip())


# ---------------------------------------------------------------------------
# Helpers (same pattern as other PBT tests)
# ---------------------------------------------------------------------------


def _make_orchestrator(
    mock_db: AsyncMock,
    ai_client: AsyncMock | None = None,
) -> ImageAnalysisOrchestrator:
    return ImageAnalysisOrchestrator(
        db=mock_db,
        ai_client=ai_client or AsyncMock(),
        media_service=Mock(),
        guard_service=Mock(),
        prompt_service=Mock(),
        worker_service=Mock(),
    )


def _make_context(transcription_text: str) -> ImageAnalysisContext:
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
    ctx.image_bytes = b"\x89PNG\r\n\x1a\nfake-image-data"
    ctx.media_type = "image/png"
    ctx.transcription_text = transcription_text
    return ctx


# ---------------------------------------------------------------------------
# Property 3: Query text prefers transcription over image description
# **Validates: Requirements 4.1, 4.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(transcription_text=transcription_text_strategy)
async def test_query_text_prefers_transcription_over_image_description(
    transcription_text: str,
):
    """Property 3: For any non-empty transcription_text, _build_query_text
    returns the transcription text and does NOT invoke the Haiku image
    description call.

    **Validates: Requirements 4.1, 4.3**
    """
    # Arrange
    mock_db = AsyncMock()
    ai_client = AsyncMock()
    orchestrator = _make_orchestrator(mock_db, ai_client=ai_client)
    ctx = _make_context(transcription_text)

    # Act
    result = await orchestrator._build_query_text(ctx)

    # Assert — return value is the transcription text
    assert result == transcription_text

    # Assert — Haiku image description was NOT called (Requirement 4.3)
    ai_client.generate.assert_not_called()
