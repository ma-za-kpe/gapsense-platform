"""
Bug condition exploration tests for WhatsApp E2E flow.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10**

These tests encode the EXPECTED (correct) behavior. On unfixed code they MUST FAIL,
confirming the bugs exist. After the fix is applied they should PASS.

Bug 1 — Constructor crashes: _handle_teacher_image / _handle_parent_voice
         instantiate services with zero args → TypeError
Bug 2 — Twilio media ID extraction: `id or url` picks message SID over URL
Bug 3 — Missing process_analysis_result call in _handle_image_analyze
Bug 4 — WorkerService missing `db` parameter
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings as hyp_settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_settings() -> MagicMock:
    """Create a mock Settings object with all required fields."""
    s = MagicMock()
    s.ANTHROPIC_API_KEY = "sk-test-key"
    s.GROK_API_KEY = None
    s.AWS_REGION = "af-south-1"
    s.AWS_ACCESS_KEY_ID = "test"
    s.AWS_SECRET_ACCESS_KEY = "test"
    s.S3_MEDIA_BUCKET = "test-bucket"
    s.SQS_QUEUE_URL = "http://localhost:4566/000000000000/test-queue"
    s.SQS_DLQ_URL = "http://localhost:4566/000000000000/test-dlq"
    s.WHATSAPP_PROVIDER = "twilio"
    return s


def _make_mock_teacher() -> MagicMock:
    """Create a mock Teacher with required attributes."""
    teacher = MagicMock()
    teacher.id = 1
    teacher.phone = "+233501234567"
    teacher.school = MagicMock()
    teacher.school.district = MagicMock()
    teacher.school.district.region = MagicMock()
    teacher.school.district.region.country_code = "GH"
    return teacher


def _make_mock_parent() -> MagicMock:
    """Create a mock Parent with required attributes."""
    parent = MagicMock()
    parent.id = 1
    parent.phone = "+233509876543"
    parent.preferred_language = "en"
    return parent


def _make_mock_student() -> MagicMock:
    """Create a mock Student."""
    student = MagicMock()
    student.id = "student-uuid-123"
    student.created_at = MagicMock()
    return student


# ---------------------------------------------------------------------------
# Bug 1 — Constructor Crashes (Requirements 1.1-1.6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_teacher_image_no_constructor_crash():
    """Bug 1: _handle_teacher_image should instantiate services without TypeError.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**

    On unfixed code, MediaService(), WorkerService(), GuardService(),
    AsyncAIClient(), and PromptService() are called with zero args,
    causing TypeError because each requires specific constructor arguments.
    The function has a broad except that swallows the error, so we verify
    that ExerciseBookScanner.handle_image_message is actually called
    (it won't be if constructors crash).
    """
    from gapsense.webhooks.whatsapp import _handle_teacher_image

    teacher = _make_mock_teacher()
    image_content = {"id": "meta-media-id-123", "mime_type": "image/jpeg"}
    db = AsyncMock()

    # Mock the DB query to return a student
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_mock_student()
    db.execute = AsyncMock(return_value=mock_result)

    # Mock the WhatsApp client
    mock_client = AsyncMock()
    mock_client.download_media = AsyncMock(return_value=b"fake-image-bytes")
    mock_client.send_text_message = AsyncMock()

    # Track whether ExerciseBookScanner.handle_image_message is called
    mock_handle_image = AsyncMock(return_value=MagicMock(success=True, s3_key="test/key.jpg", error=None))

    with patch(
        "gapsense.engagement.whatsapp.get_whatsapp_client", return_value=mock_client
    ), patch(
        "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner.handle_image_message",
        mock_handle_image,
    ):
        await _handle_teacher_image(teacher, image_content, db)

    # On unfixed code, constructors crash with TypeError before reaching
    # handle_image_message. The broad except catches it and sends an error
    # message to the teacher instead.
    assert mock_handle_image.call_count > 0, (
        "ExerciseBookScanner.handle_image_message was never called. "
        "Constructor crash (TypeError) prevented the image processing pipeline "
        "from executing. Services are instantiated without required arguments."
    )


@pytest.mark.asyncio
async def test_handle_parent_voice_no_constructor_crash():
    """Bug 1: _handle_parent_voice should instantiate services without TypeError.

    **Validates: Requirements 1.6**

    Same constructor crash as _handle_teacher_image but in the parent voice path.
    The function has a broad except that swallows the error, so we verify
    that VoiceMicroCoaching.handle_voice_message is actually called.
    """
    from gapsense.webhooks.whatsapp import _handle_parent_voice

    parent = _make_mock_parent()
    voice_content = {"id": "meta-media-id-456", "mime_type": "audio/ogg"}
    db = AsyncMock()

    # Mock the DB query to return a student
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_mock_student()
    db.execute = AsyncMock(return_value=mock_result)

    # Mock the WhatsApp client
    mock_client = AsyncMock()
    mock_client.download_media = AsyncMock(return_value=b"fake-audio-bytes")
    mock_client.send_text_message = AsyncMock()

    # Track whether VoiceMicroCoaching.handle_voice_message is called
    mock_handle_voice = AsyncMock(return_value=MagicMock(success=True, error=None))

    with patch(
        "gapsense.engagement.whatsapp.get_whatsapp_client", return_value=mock_client
    ), patch(
        "gapsense.engagement.voice_micro_coaching.VoiceMicroCoaching.handle_voice_message",
        mock_handle_voice,
    ):
        await _handle_parent_voice(parent, voice_content, db)

    # On unfixed code, constructors crash with TypeError before reaching
    # handle_voice_message. The broad except catches it and sends an error
    # message to the parent instead.
    assert mock_handle_voice.call_count > 0, (
        "VoiceMicroCoaching.handle_voice_message was never called. "
        "Constructor crash (TypeError) prevented the voice processing pipeline "
        "from executing. Services are instantiated without required arguments."
    )


# ---------------------------------------------------------------------------
# Bug 2 — Twilio Media ID Extraction (Requirements 1.7, 1.8)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@hyp_settings(max_examples=20, deadline=None)
@given(
    message_sid=st.from_regex(r"SM[a-f0-9]{32}", fullmatch=True),
    media_url=st.from_regex(
        r"https://api\.twilio\.com/2010-04-01/Accounts/AC[a-f0-9]{32}/Messages/SM[a-f0-9]{32}/Media/ME[a-f0-9]{32}",
        fullmatch=True,
    ),
)
async def test_twilio_media_id_extraction_uses_url(message_sid: str, media_url: str):
    """Bug 2: Media ID extraction should prefer URL over message SID for Twilio.

    **Validates: Requirements 1.7, 1.8**

    On unfixed code, `image_content.get("id") or image_content.get("url")`
    returns the message SID because it's truthy, preventing fallback to the
    actual media URL. The correct behavior is to use the URL when present.

    We test this by calling _handle_teacher_image with Twilio-style content
    (both "id" and "url" present) and checking which value is passed to
    download_media. download_media is called before the constructor crash,
    so this test isolates Bug 2 from Bug 1.
    """
    from gapsense.webhooks.whatsapp import _handle_teacher_image

    teacher = _make_mock_teacher()
    image_content = {"id": message_sid, "url": media_url, "mime_type": "image/jpeg"}
    db = AsyncMock()

    # Mock the DB query to return a student
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_mock_student()
    db.execute = AsyncMock(return_value=mock_result)

    # Mock the WhatsApp client — capture what download_media is called with
    mock_client = AsyncMock()
    mock_client.download_media = AsyncMock(return_value=b"fake-image-bytes")
    mock_client.send_text_message = AsyncMock()

    with patch(
        "gapsense.engagement.whatsapp.get_whatsapp_client", return_value=mock_client
    ):
        await _handle_teacher_image(teacher, image_content, db)

    # download_media is called before the constructor crash (Bug 1),
    # so we can isolate the media ID extraction bug
    assert mock_client.download_media.call_count > 0, (
        "download_media was never called — unexpected test setup issue"
    )
    actual_media_id = mock_client.download_media.call_args[1].get("media_id")
    assert actual_media_id == media_url, (
        f"download_media called with message SID '{actual_media_id}' "
        f"instead of media URL '{media_url}'. "
        f"The `id or url` pattern picks the truthy SID over the actual URL."
    )


# ---------------------------------------------------------------------------
# Bug 3 — Missing process_analysis_result (Requirements 1.9)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_image_analyze_calls_process_analysis_result():
    """Bug 3: _handle_image_analyze should call process_analysis_result after AI analysis.

    **Validates: Requirements 1.9**

    On unfixed code, _handle_image_analyze receives AI analysis JSON but
    only logs it — it never calls ExerciseBookScanner.process_analysis_result(),
    so GapProfiles are never updated and teachers never receive results.
    """
    from gapsense.services.worker_service import WorkerService, WorkerTask

    mock_settings = _make_mock_settings()

    # Create mock dependencies
    mock_ai_client = MagicMock()
    mock_media_service = MagicMock()
    mock_media_service.download = AsyncMock(return_value=b"fake-image-bytes")
    mock_guard_service = MagicMock()
    mock_prompt_service = MagicMock()

    # Mock the prompt rendering
    mock_rendered = MagicMock()
    mock_rendered.system_prompt = "Analyze this."
    mock_rendered.model = "claude-sonnet-4-5"
    mock_prompt_service.render_prompt = MagicMock(return_value=mock_rendered)

    # Mock AI response with valid JSON
    mock_response = MagicMock()
    mock_response.json_parsed = {
        "gap_nodes": ["node-1", "node-2"],
        "errors": [{"description": "Addition error"}],
        "patterns": ["counting mistakes"],
        "focus_areas": ["basic addition"],
    }
    mock_response.text = json.dumps(mock_response.json_parsed)
    mock_ai_client.generate = AsyncMock(return_value=mock_response)

    # Try to instantiate WorkerService with db param
    # On unfixed code, WorkerService doesn't accept db → we pass it anyway
    # and check if process_analysis_result is called
    try:
        svc = WorkerService(
            ai_client=mock_ai_client,
            media_service=mock_media_service,
            guard_service=mock_guard_service,
            prompt_service=mock_prompt_service,
            settings=mock_settings,
            db=AsyncMock(),  # Bug 4: unfixed code doesn't accept this
        )
    except TypeError:
        pytest.fail(
            "WorkerService does not accept 'db' parameter. "
            "Cannot test process_analysis_result without db."
        )

    task = WorkerTask(
        task_type="image_analyze",
        payload={
            "s3_key": "GH/student-1/image/123_test.jpg",
            "student_id": "student-uuid-123",
            "teacher_phone": "+233501234567",
            "country": "GH",
            "language": "en",
        },
    )

    # Patch ExerciseBookScanner.process_analysis_result to track calls
    with patch(
        "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner.process_analysis_result",
        new_callable=AsyncMock,
    ) as mock_process:
        await svc._handle_image_analyze(task)

        # On unfixed code, process_analysis_result is never called
        assert mock_process.call_count > 0, (
            "process_analysis_result was never called after successful AI analysis. "
            "The analysis pipeline is severed — GapProfiles are never updated "
            "and teachers never receive results."
        )

        # Verify it was called with correct arguments
        mock_process.assert_called_once_with(
            student_id="student-uuid-123",
            teacher_phone="+233501234567",
            analysis=mock_response.json_parsed,
            country="GH",
            language="en",
        )


# ---------------------------------------------------------------------------
# Bug 4 — Missing db parameter (Requirements 1.10)
# ---------------------------------------------------------------------------


def test_worker_service_has_db_attribute():
    """Bug 4: WorkerService should accept and store a db parameter.

    **Validates: Requirements 1.10**

    On unfixed code, WorkerService.__init__ does not accept a `db` parameter,
    so even if _handle_image_analyze called process_analysis_result(), it would
    fail because ExerciseBookScanner requires a database session.
    """
    from gapsense.services.worker_service import WorkerService

    mock_settings = _make_mock_settings()
    mock_db = MagicMock()

    try:
        svc = WorkerService(
            ai_client=MagicMock(),
            media_service=MagicMock(),
            guard_service=MagicMock(),
            prompt_service=MagicMock(),
            settings=mock_settings,
            db=mock_db,
        )
    except TypeError as e:
        pytest.fail(
            f"WorkerService does not accept 'db' parameter: {e}. "
            "Cannot pass database session to ExerciseBookScanner."
        )

    # Verify db is stored as instance attribute
    assert hasattr(svc, "_db"), (
        "WorkerService does not have '_db' attribute. "
        "Cannot access database session for ExerciseBookScanner."
    )
    assert svc._db is mock_db, (
        "WorkerService._db does not reference the provided db session."
    )
