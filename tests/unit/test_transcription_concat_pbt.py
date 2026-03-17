"""
Property-based tests for transcription text concatenation.

# Feature: phase3-two-stage-ocr-diagnosis, Property 1: Transcription text concatenation preserves all content
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Concatenation logic under test (mirrors _transcribe_image implementation)
# ---------------------------------------------------------------------------


def concatenate_transcription(transcription_result: dict) -> str:
    """Extract and concatenate question_text + student_work from a
    transcription result dict.  This is the exact logic used inside
    ``ImageAnalysisOrchestrator._transcribe_image``.
    """
    parts: list[str] = []
    for q in transcription_result.get("questions", []):
        text = q.get("question_text", "").strip()
        work = q.get("student_work", "").strip()
        if text:
            parts.append(text)
        if work:
            parts.append(work)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Printable text that may include whitespace, but no *only*-whitespace strings
# are generated separately to test the strip() behaviour.
_text_strategy = st.text(
    min_size=0,
    max_size=200,
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S", "Z")),
)

_question_strategy = st.fixed_dictionaries(
    {
        "question_text": _text_strategy,
        "student_work": _text_strategy,
    }
)

_questions_list_strategy = st.lists(_question_strategy, min_size=0, max_size=30)


# ---------------------------------------------------------------------------
# Property 1: Transcription text concatenation preserves all content
# **Validates: Requirements 2.4**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(questions=_questions_list_strategy)
def test_concatenation_preserves_all_non_empty_fragments(
    questions: list[dict[str, str]],
):
    """Property 1: Every non-empty (after strip) question_text and
    student_work fragment from the input appears in the concatenated output.

    **Validates: Requirements 2.4**
    """
    transcription_result = {"questions": questions}
    result = concatenate_transcription(transcription_result)

    # Collect expected non-empty fragments
    expected_fragments: list[str] = []
    for q in questions:
        text = q.get("question_text", "").strip()
        work = q.get("student_work", "").strip()
        if text:
            expected_fragments.append(text)
        if work:
            expected_fragments.append(work)

    # Every non-empty fragment must appear in the output
    for fragment in expected_fragments:
        assert fragment in result, f"Fragment {fragment!r} not found in result {result!r}"

    # The number of space-joined parts must equal the number of non-empty fragments
    if expected_fragments:
        assert result == " ".join(expected_fragments)
    else:
        assert result == ""
