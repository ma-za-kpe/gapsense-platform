"""
Property-based tests for transcript formatting completeness.

# Feature: phase3-two-stage-ocr-diagnosis, Property 4: Transcript formatting includes all required fields
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Non-empty printable text (after strip) for fields that must appear in output
_nonempty_text = st.text(
    min_size=1,
    max_size=200,
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
).filter(lambda s: s.strip())

# Possibly-empty text for optional fields
_maybe_text = st.text(
    min_size=0,
    max_size=200,
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
)

# A single question dict with all expected fields
_question_strategy = st.fixed_dictionaries(
    {
        "question_number": _maybe_text,
        "question_text": _maybe_text,
        "student_work": _maybe_text,
        "teacher_mark": _maybe_text,
        "illegible_regions": _maybe_text,
    }
)

# A transcription result with header fields and at least 1 question
_transcription_result_strategy = st.fixed_dictionaries(
    {
        "layout": _maybe_text,
        "topic_detected": _maybe_text,
        "overall_legibility": _maybe_text,
        "questions": st.lists(_question_strategy, min_size=1, max_size=15),
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_orchestrator() -> ImageAnalysisOrchestrator:
    return ImageAnalysisOrchestrator(
        db=AsyncMock(),
        ai_client=Mock(),
        media_service=Mock(),
        guard_service=Mock(),
        prompt_service=Mock(),
        worker_service=Mock(),
    )


# ---------------------------------------------------------------------------
# Property 4: Transcript formatting includes all required fields
# **Validates: Requirements 5.1, 5.2, 5.4**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(transcription_result=_transcription_result_strategy)
def test_transcript_formatting_includes_all_required_fields(
    transcription_result: dict,
):
    """Property 4: For any non-empty transcription result with at least one
    question, _format_transcript_for_prompt output contains every non-empty
    layout, topic_detected, overall_legibility value, and for each question
    the question_number, non-empty question_text, and non-empty student_work.

    **Validates: Requirements 5.1, 5.2, 5.4**
    """
    orchestrator = _make_orchestrator()
    result = orchestrator._format_transcript_for_prompt(transcription_result)

    # The result must be a non-empty string (we have >= 1 question)
    assert isinstance(result, str)
    assert len(result) > 0

    # Header fields: if non-empty, must appear in output
    layout = transcription_result.get("layout", "")
    if layout:
        assert layout in result, f"layout {layout!r} not found in output"

    topic = transcription_result.get("topic_detected", "")
    if topic:
        assert topic in result, f"topic_detected {topic!r} not found in output"

    legibility = transcription_result.get("overall_legibility", "")
    if legibility:
        assert legibility in result, f"overall_legibility {legibility!r} not found in output"

    # Per-question fields
    for q in transcription_result["questions"]:
        q_num = q.get("question_number", "")
        q_text = q.get("question_text", "")
        student_work = q.get("student_work", "")

        # question_number always appears (as "Q{num}" or "Q?" if empty)
        if q_num:
            assert f"Q{q_num}" in result, f"question_number Q{q_num!r} not found in output"
        else:
            assert "Q?" in result, "Missing Q? marker for empty question_number"

        # Non-empty question_text must appear in output
        if q_text:
            assert q_text in result, f"question_text {q_text!r} not found in output"

        # Non-empty student_work must appear in output
        if student_work:
            assert student_work in result, f"student_work {student_work!r} not found in output"
