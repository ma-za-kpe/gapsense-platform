"""
Preservation property tests for WhatsApp E2E flow bugfix.

**Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6, 3.7**

These tests capture EXISTING correct behavior on UNFIXED code.
They MUST PASS before and after the fix, confirming no regressions.

Property 2: Preservation — Unchanged Text Routing, Meta Media ID,
and Non-Image Worker Tasks.
"""

from __future__ import annotations

import asyncio
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
    parent.id = 2
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
# Hypothesis strategies
# ---------------------------------------------------------------------------

# Text message bodies — non-empty strings that a user might send
text_message_bodies = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    min_size=1,
    max_size=200,
)

# Meta media IDs — alphanumeric strings typical of Meta's media identifiers
meta_media_ids = st.from_regex(r"[0-9]{10,20}", fullmatch=True)

# Non-image_analyze task types
non_image_task_types = st.sampled_from(["tts_generate", "voice_transcribe"])


# ---------------------------------------------------------------------------
# Property: Text message routing — teacher text → TeacherConversationPartner
# No MediaService/WorkerService/GuardService/AsyncAIClient/PromptService
# constructors from the image/voice handlers are called.
#
# **Validates: Requirements 3.1, 3.2**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@hyp_settings(max_examples=20, deadline=None)
@given(message_body=text_message_bodies)
async def test_teacher_text_routes_to_conversation_handler(message_body: str):
    """Preservation: Teacher text messages route to _handle_teacher_conversation.

    **Validates: Requirements 3.1**

    For all text message webhooks from teachers, _handle_message routes to
    _handle_teacher_conversation (not to image/voice handlers). No
    MediaService/WorkerService from the image/voice path are instantiated.
    """
    from gapsense.webhooks.whatsapp import _handle_message

    teacher = _make_mock_teacher()
    mock_db = AsyncMock()

    # Build a text message dict as the webhook would deliver
    message = {
        "type": "text",
        "from": teacher.phone,
        "id": "wamid_test_teacher_text",
        "text": {"body": message_body},
    }
    value = {}

    # Mock _detect_user_type to return teacher
    mock_teacher_conv = AsyncMock()

    with patch(
        "gapsense.webhooks.whatsapp._detect_user_type",
        new_callable=AsyncMock,
        return_value=("teacher", teacher),
    ), patch(
        "gapsense.webhooks.whatsapp._handle_teacher_conversation",
        mock_teacher_conv,
    ) as patched_conv, patch(
        "gapsense.webhooks.whatsapp._handle_teacher_image",
        new_callable=AsyncMock,
        side_effect=AssertionError("_handle_teacher_image should not be called for text"),
    ), patch(
        "gapsense.services.media_service.MediaService.__init__",
        side_effect=AssertionError("MediaService should not be instantiated for text messages"),
    ), patch(
        "gapsense.services.worker_service.WorkerService.__init__",
        side_effect=AssertionError("WorkerService should not be instantiated for text messages"),
    ):
        await _handle_message(message, value, mock_db)

    # Verify _handle_teacher_conversation was called with the teacher and message
    assert patched_conv.call_count == 1, (
        "_handle_teacher_conversation should be called exactly once for teacher text"
    )
    call_args = patched_conv.call_args[0]
    assert call_args[0] is teacher  # first positional arg is teacher
    assert call_args[1] == message_body  # second positional arg is message content


@pytest.mark.asyncio
@hyp_settings(max_examples=20, deadline=None)
@given(message_body=text_message_bodies)
async def test_parent_text_routes_to_flow_executor(message_body: str):
    """Preservation: Parent text messages route to FlowExecutor.

    **Validates: Requirements 3.2**

    For all text message webhooks from parents, the _handle_message function
    routes to FlowExecutor.process_message. No MediaService/WorkerService/
    GuardService constructors from image/voice handlers are called.
    """
    from gapsense.webhooks.whatsapp import _handle_message

    parent = _make_mock_parent()
    mock_db = AsyncMock()

    # Build a text message dict as the webhook would deliver
    message = {
        "type": "text",
        "from": parent.phone,
        "id": "wamid_test_123",
        "text": {"body": message_body},
    }
    value = {}

    # Mock _detect_user_type to return parent
    mock_flow_result = MagicMock()
    mock_flow_result.error = None
    mock_flow_result.flow_name = "parent_onboarding"
    mock_flow_result.completed = False
    mock_flow_result.next_step = "step_2"
    mock_flow_result.message_sent = True

    mock_process_message = AsyncMock(return_value=mock_flow_result)

    with patch(
        "gapsense.webhooks.whatsapp._detect_user_type",
        new_callable=AsyncMock,
        return_value=("parent", parent),
    ), patch(
        "gapsense.engagement.flow_executor.FlowExecutor.process_message",
        mock_process_message,
    ), patch(
        "gapsense.services.media_service.MediaService.__init__",
        side_effect=AssertionError("MediaService should not be instantiated for text messages"),
    ), patch(
        "gapsense.services.worker_service.WorkerService.__init__",
        side_effect=AssertionError("WorkerService should not be instantiated for text messages"),
    ):
        await _handle_message(message, value, mock_db)

    # Verify FlowExecutor.process_message was called
    assert mock_process_message.call_count == 1, (
        "FlowExecutor.process_message should be called exactly once for parent text"
    )
    call_kwargs = mock_process_message.call_args[1]
    assert call_kwargs["parent"] is parent
    assert call_kwargs["message_type"] == "text"
    assert call_kwargs["message_content"] == message_body


# ---------------------------------------------------------------------------
# Property: Meta image webhooks use Meta media ID when no "url" field present.
#
# **Validates: Requirements 3.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@hyp_settings(max_examples=20, deadline=None)
@given(meta_id=meta_media_ids)
async def test_meta_image_uses_media_id_when_no_url(meta_id: str):
    """Preservation: Meta image messages use image_content.get("id") for download.

    **Validates: Requirements 3.3**

    For all Meta image webhooks where image_content has "id" but no "url",
    the media ID extraction returns the Meta media ID value. This is the
    correct behavior for Meta's two-step download process.

    On unfixed code: `image_content.get("id") or image_content.get("url")`
    returns `id` because `url` is absent → correct for Meta.
    After fix: `image_content.get("url") or image_content.get("id")`
    returns `id` because `url` is absent → still correct for Meta.
    """
    from gapsense.webhooks.whatsapp import _handle_teacher_image

    teacher = _make_mock_teacher()
    # Meta payloads have "id" but NO "url" field
    image_content = {"id": meta_id, "mime_type": "image/jpeg"}
    db = AsyncMock()

    # Mock the DB query to return a student
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_mock_student()
    db.execute = AsyncMock(return_value=mock_result)

    # Mock the WhatsApp client — capture what download_media receives
    mock_client = AsyncMock()
    mock_client.download_media = AsyncMock(return_value=b"fake-image-bytes")
    mock_client.send_text_message = AsyncMock()

    with patch(
        "gapsense.engagement.whatsapp.get_whatsapp_client", return_value=mock_client
    ):
        await _handle_teacher_image(teacher, image_content, db)

    # download_media is called before the constructor crash (Bug 1),
    # so we can verify the media ID extraction in isolation
    assert mock_client.download_media.call_count > 0, (
        "download_media was not called — unexpected test setup issue"
    )
    actual_media_id = mock_client.download_media.call_args[1].get("media_id")
    assert actual_media_id == meta_id, (
        f"Meta media ID extraction returned '{actual_media_id}' "
        f"instead of expected Meta media ID '{meta_id}'. "
        f"Meta payloads with only 'id' (no 'url') must use the 'id' value."
    )


# ---------------------------------------------------------------------------
# Property: Non-image_analyze worker tasks dispatch correctly without
# touching ExerciseBookScanner.
#
# **Validates: Requirements 3.5, 3.6, 3.7**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@hyp_settings(max_examples=20, deadline=None)
@given(task_type=non_image_task_types)
async def test_non_image_worker_tasks_dispatch_without_exercise_book_scanner(task_type: str):
    """Preservation: Non-image_analyze worker tasks dispatch to correct handler.

    **Validates: Requirements 3.5, 3.6, 3.7**

    For all non-image_analyze worker tasks (tts_generate, voice_transcribe),
    the task dispatches to the correct handler without touching
    ExerciseBookScanner. This ensures the fix to _handle_image_analyze
    doesn't affect other task types.
    """
    from gapsense.services.worker_service import WorkerService, WorkerTask

    mock_settings = _make_mock_settings()

    mock_ai_client = MagicMock()
    mock_media_service = MagicMock()
    mock_media_service.download = AsyncMock(return_value=b"fake-bytes")
    mock_guard_service = MagicMock()
    mock_prompt_service = MagicMock()

    svc = WorkerService(
        ai_client=mock_ai_client,
        media_service=mock_media_service,
        guard_service=mock_guard_service,
        prompt_service=mock_prompt_service,
        settings=mock_settings,
    )

    # Build a task payload appropriate for the task type
    if task_type == "tts_generate":
        payload = {
            "text": "Hello student",
            "language": "en",
            "country": "GH",
            "student_id": "student-1",
        }
    else:  # voice_transcribe
        payload = {
            "s3_key": "GH/parent-1/audio/voice_123.ogg",
            "parent_id": "parent-1",
        }

    task = WorkerTask(task_type=task_type, payload=payload)

    # Patch ExerciseBookScanner to detect if it's ever touched
    with patch(
        "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner.__init__",
        side_effect=AssertionError(
            "ExerciseBookScanner should not be instantiated for non-image tasks"
        ),
    ), patch(
        "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner.process_analysis_result",
        side_effect=AssertionError(
            "process_analysis_result should not be called for non-image tasks"
        ),
    ):
        # Should dispatch to the correct handler without error
        await svc._route_task(task)

    # Verify the task was routed (no ValueError for unknown task type)
    # The handlers themselves are stubs/placeholders, so they just log.
    # The key assertion is that ExerciseBookScanner was never touched.
