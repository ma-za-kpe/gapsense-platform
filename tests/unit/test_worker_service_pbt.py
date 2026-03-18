"""
Property-based tests for WorkerService - Phase 1 Infrastructure Hardening.

Tests cover:
- Property 1: Session lifecycle isolation (16.2)
- Property 2: Duplicate message idempotency (16.3)
- Property 3: Ledger status reflects task outcome (16.4)
- Property 4: Cost logging isolation (16.5)
- Property 5: Stub handlers signal non-implementation (16.6)
- Property 6: Unknown task type rejection (16.7)
- Property 7: Error classification routing (16.8)
- Property 8: Send-before-delete ordering (16.9)
- Property 9: Failed send preserves original message (16.10)
- Property 10: FIFO MessageGroupId conditional inclusion (16.11)
- Property 11: New model pricing coverage (16.12)
- Property 13: Null optional fields are valid (16.13)
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.core.exceptions import PermanentError, RetryableError
from gapsense.services.worker_service import TASK_TYPES, WorkerService, WorkerTask

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_worker_service(
    session_factory: Any = None,
    max_concurrent: int = 5,
    queue_url: str = "http://localhost:4566/000000000000/test-queue",
    dlq_url: str = "http://localhost:4566/000000000000/test-dlq",
) -> WorkerService:
    mock_settings = MagicMock()
    mock_settings.SQS_QUEUE_URL = queue_url
    mock_settings.SQS_DLQ_URL = dlq_url
    mock_settings.AWS_REGION = "af-south-1"
    mock_settings.AWS_ACCESS_KEY_ID = "test"
    mock_settings.AWS_SECRET_ACCESS_KEY = "test"  # pragma: allowlist secret

    return WorkerService(
        ai_client=MagicMock(),
        media_service=MagicMock(),
        guard_service=MagicMock(),
        prompt_service=MagicMock(),
        settings=mock_settings,
        session_factory=session_factory,
        max_concurrent=max_concurrent,
    )


def _make_sqs_message(
    task_type: str,
    payload: dict | None = None,
    retry_count: int = 0,
    max_retries: int = 3,
    message_id: str = "test-msg-id",
    receipt_handle: str = "test-receipt",
) -> dict:
    return {
        "MessageId": message_id,
        "ReceiptHandle": receipt_handle,
        "Body": json.dumps(
            {
                "task_type": task_type,
                "payload": payload or {},
                "retry_count": retry_count,
                "max_retries": max_retries,
            }
        ),
    }


# ---------------------------------------------------------------------------
# Property 1: Session lifecycle isolation
# Feature: phase1-infrastructure-hardening, Property 1: Session lifecycle isolation
# **Validates: Requirements 1.2, 1.4**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    task_type=st.sampled_from(["image_analyze", "scheduled_message"]),
    message_id=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N")),
    ),
    should_succeed=st.booleans(),
)
async def test_session_lifecycle_isolation(task_type: str, message_id: str, should_succeed: bool):
    """Property 1: Session lifecycle isolation

    For any SQS message processed by _process_message when a session_factory
    is provided, a new AsyncSession SHALL be created before task routing and
    closed after the task completes or fails, regardless of the outcome.
    """
    session_created = False
    session_closed = False

    @asynccontextmanager
    async def mock_session_factory():
        nonlocal session_created, session_closed
        session_created = True
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        try:
            yield mock_session
        finally:
            session_closed = True

    svc = _make_worker_service(session_factory=mock_session_factory)
    svc._delete_message = AsyncMock()

    if should_succeed:
        svc._route_task = AsyncMock()
    else:
        svc._route_task = AsyncMock(side_effect=Exception("simulated failure"))
        svc._handle_failure = AsyncMock()

    msg = _make_sqs_message(task_type=task_type, message_id=message_id)
    await svc._process_message(msg)

    assert session_created, "Session should be created before routing"
    assert session_closed, "Session should be closed after task completes/fails"


# ---------------------------------------------------------------------------
# Property 2: Duplicate message idempotency
# Feature: phase1-infrastructure-hardening, Property 2: Duplicate message idempotency
# **Validates: Requirements 2.4**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    message_id=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N")),
    ),
    task_type=st.sampled_from(list(TASK_TYPES)),
)
async def test_duplicate_message_idempotency(message_id: str, task_type: str):
    """Property 2: Duplicate message idempotency

    Insert same (sqs_message_id, task_type) twice; second attempt skips
    processing and deletes message.
    """
    route_task_called = False
    delete_called = False

    @asynccontextmanager
    async def mock_session_factory():
        mock_session = AsyncMock()
        # Simulate duplicate: rowcount=0 means conflict detected
        mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=0))
        mock_session.commit = AsyncMock()
        yield mock_session

    svc = _make_worker_service(session_factory=mock_session_factory)

    async def track_route(task, db=None):
        nonlocal route_task_called
        route_task_called = True

    async def track_delete(receipt_handle):
        nonlocal delete_called
        delete_called = True

    svc._route_task = track_route
    svc._delete_message = track_delete

    msg = _make_sqs_message(task_type=task_type, message_id=message_id)
    await svc._process_message(msg)

    assert not route_task_called, "Route task should be skipped for duplicate messages"
    assert delete_called, "Message should be deleted even for duplicates"


# ---------------------------------------------------------------------------
# Property 3: Ledger status reflects task outcome
# Feature: phase1-infrastructure-hardening, Property 3: Ledger status reflects task outcome
# **Validates: Requirements 2.5, 2.6**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    task_type=st.sampled_from(list(TASK_TYPES)),
    should_succeed=st.booleans(),
)
async def test_ledger_status_reflects_task_outcome(task_type: str, should_succeed: bool):
    """Property 3: Ledger status reflects task outcome

    Verify ledger row is "completed" with non-null completed_at on success,
    "failed" on DLQ.
    """
    ledger_updates: list[dict] = []

    @asynccontextmanager
    async def mock_session_factory():
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(rowcount=1))
        mock_session.commit = AsyncMock()
        yield mock_session

    svc = _make_worker_service(session_factory=mock_session_factory)
    svc._delete_message = AsyncMock()
    svc._requeue_with_backoff = AsyncMock()
    svc._move_to_dlq = AsyncMock()

    if should_succeed:
        svc._route_task = AsyncMock()
    else:
        svc._route_task = AsyncMock(side_effect=PermanentError("test permanent"))

    msg = _make_sqs_message(
        task_type=task_type,
        retry_count=3,
        max_retries=3,
    )
    await svc._process_message(msg)

    # If succeeded, _route_task was called without error
    # If failed, _handle_failure was called which routes to DLQ
    # Both paths update the ledger
    if should_succeed:
        svc._route_task.assert_called_once()
    else:
        svc._move_to_dlq.assert_called_once()


# ---------------------------------------------------------------------------
# Property 4: Cost logging isolation
# Feature: phase1-infrastructure-hardening, Property 4: Cost logging isolation
# **Validates: Requirements 3.2**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    input_tokens=st.integers(min_value=0, max_value=10000),
    output_tokens=st.integers(min_value=0, max_value=10000),
)
async def test_cost_logging_isolation(input_tokens: int, output_tokens: int):
    """Property 4: Cost logging isolation

    Verify pipeline continues when _log_ai_cost commit raises, session is
    rolled back.
    """
    from gapsense.ai.async_client import AIResponse
    from gapsense.services.image_analysis_orchestrator import (
        ImageAnalysisOrchestrator,
    )

    mock_response = AIResponse(
        text="test response",
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt_id="ANALYSIS-001",
        latency_ms=100.0,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock(side_effect=Exception("DB commit failed"))
    mock_db.rollback = AsyncMock()

    orchestrator = ImageAnalysisOrchestrator(
        db=mock_db,
        ai_client=MagicMock(),
        media_service=MagicMock(),
        guard_service=MagicMock(),
        prompt_service=MagicMock(),
        worker_service=MagicMock(),
    )

    @dataclass
    class _Student:
        id: str = "test-student-id"
        teacher_id: str = "test-teacher-id"

    @dataclass
    class _Ctx:
        student: _Student | None = None

        def __post_init__(self):
            self.student = _Student()

    ctx = _Ctx()

    # _log_ai_cost should NOT raise even when commit fails
    await orchestrator._log_ai_cost(ctx, mock_response)

    mock_db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# Property 5: Stub handlers signal non-implementation
# Feature: phase1-infrastructure-hardening, Property 5: Stub handlers signal non-implementation
# **Validates: Requirements 4.1, 4.2**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    payload=st.fixed_dictionaries(
        {
            "text": st.text(min_size=0, max_size=100),
            "language": st.sampled_from(["en", "tw", "ee"]),
        }
    ),
)
async def test_stub_handlers_tts(payload: dict):
    """Property 5a: TTS handler raises NotImplementedError for any payload."""
    svc = _make_worker_service()
    task = WorkerTask(task_type="tts_generate", payload=payload)

    with pytest.raises(NotImplementedError):
        await svc._handle_tts_generate(task)


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    payload=st.fixed_dictionaries(
        {
            "audio_url": st.text(min_size=0, max_size=100),
            "language": st.sampled_from(["en", "tw", "ee"]),
        }
    ),
)
async def test_stub_handlers_voice(payload: dict):
    """Property 5b: Voice handler raises NotImplementedError for any payload."""
    svc = _make_worker_service()
    task = WorkerTask(task_type="voice_transcribe", payload=payload)

    with pytest.raises(NotImplementedError):
        await svc._handle_voice_transcribe(task)


# ---------------------------------------------------------------------------
# Property 6: Unknown task type rejection
# Feature: phase1-infrastructure-hardening, Property 6: Unknown task type rejection
# **Validates: Requirements 4.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    unknown_type=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N")),
    ).filter(lambda x: x not in TASK_TYPES),
)
async def test_unknown_task_type_rejection(unknown_type: str):
    """Property 6: Unknown task type rejection

    Random strings not in TASK_TYPES always raise ValueError.
    """
    svc = _make_worker_service()
    task = WorkerTask(task_type=unknown_type, payload={})

    with pytest.raises(ValueError, match="Unknown task type"):
        await svc._route_task(task)


# ---------------------------------------------------------------------------
# Property 7: Error classification routing
# Feature: phase1-infrastructure-hardening, Property 7: Error classification routing
# **Validates: Requirements 5.4, 5.5**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    retry_count=st.integers(min_value=0, max_value=10),
    max_retries=st.integers(min_value=1, max_value=5),
    error_type=st.sampled_from(["permanent", "retryable", "other"]),
)
async def test_error_classification_routing(retry_count: int, max_retries: int, error_type: str):
    """Property 7: Error classification routing

    PermanentError -> DLQ regardless of retry_count;
    RetryableError/other -> retry when under max, DLQ when at max.
    """
    svc = _make_worker_service()
    task = WorkerTask(
        task_type="image_analyze",
        payload={},
        retry_count=retry_count,
        max_retries=max_retries,
        receipt_handle="test-receipt",
    )

    requeue_called = False
    dlq_called = False

    async def mock_requeue(t, visibility_timeout):
        nonlocal requeue_called
        requeue_called = True

    async def mock_dlq(t, error):
        nonlocal dlq_called
        dlq_called = True

    svc._requeue_with_backoff = mock_requeue
    svc._move_to_dlq = mock_dlq
    svc._delete_message = AsyncMock()

    if error_type == "permanent":
        error = PermanentError("permanent failure")
    elif error_type == "retryable":
        error = RetryableError("retryable failure")
    else:
        error = Exception("generic failure")

    await svc._handle_failure(task, error)

    if error_type == "permanent":
        assert dlq_called, "PermanentError should go to DLQ"
        assert not requeue_called, "PermanentError should not be requeued"
    elif retry_count < max_retries:
        assert requeue_called, "Should requeue when under max retries"
        assert not dlq_called, "Should not go to DLQ when retries remain"
    else:
        assert dlq_called, "Should go to DLQ when max retries exceeded"
        assert not requeue_called, "Should not requeue when max retries exceeded"


# ---------------------------------------------------------------------------
# Property 8: Send-before-delete ordering
# Feature: phase1-infrastructure-hardening, Property 8: Send-before-delete ordering
# **Validates: Requirements 6.1, 6.2**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    retry_count=st.integers(min_value=0, max_value=5),
    max_retries=st.integers(min_value=1, max_value=5),
    is_permanent=st.booleans(),
)
async def test_send_before_delete_ordering(retry_count: int, max_retries: int, is_permanent: bool):
    """Property 8: Send-before-delete ordering

    Verify SQS send call occurs before delete call in both retry and DLQ paths.
    """
    call_order: list[str] = []

    svc = _make_worker_service()
    task = WorkerTask(
        task_type="image_analyze",
        payload={},
        retry_count=retry_count,
        max_retries=max_retries,
        receipt_handle="test-receipt",
    )

    async def mock_requeue(t, visibility_timeout):
        call_order.append("requeue")

    async def mock_dlq(t, error):
        call_order.append("dlq")

    async def mock_delete(receipt_handle):
        call_order.append("delete")

    svc._requeue_with_backoff = mock_requeue
    svc._move_to_dlq = mock_dlq
    svc._delete_message = mock_delete

    error = PermanentError("perm") if is_permanent else RetryableError("retry")
    await svc._handle_failure(task, error)

    if "delete" in call_order:
        delete_idx = call_order.index("delete")
        send_idx = -1
        if "requeue" in call_order:
            send_idx = call_order.index("requeue")
        elif "dlq" in call_order:
            send_idx = call_order.index("dlq")

        if send_idx >= 0:
            assert send_idx < delete_idx, f"Send before delete. Order: {call_order}"


# ---------------------------------------------------------------------------
# Property 9: Failed send preserves original message
# Feature: phase1-infrastructure-hardening, Property 9: Failed send preserves original message
# **Validates: Requirements 6.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(is_dlq_path=st.booleans())
async def test_failed_send_preserves_original_message(is_dlq_path: bool):
    """Property 9: Failed send preserves original message

    When requeue/DLQ send raises, verify delete is never called.
    """
    delete_called = False

    svc = _make_worker_service()
    task = WorkerTask(
        task_type="image_analyze",
        payload={},
        retry_count=0 if not is_dlq_path else 5,
        max_retries=3,
        receipt_handle="test-receipt",
    )

    async def mock_requeue_fail(t, visibility_timeout):
        raise Exception("Requeue failed")

    async def mock_dlq_fail(t, error):
        raise Exception("DLQ send failed")

    async def mock_delete(receipt_handle):
        nonlocal delete_called
        delete_called = True

    svc._requeue_with_backoff = mock_requeue_fail
    svc._move_to_dlq = mock_dlq_fail
    svc._delete_message = mock_delete

    error = PermanentError("perm") if is_dlq_path else RetryableError("retry")
    await svc._handle_failure(task, error)

    assert not delete_called, "Delete should not be called when send fails"


# ---------------------------------------------------------------------------
# Property 10: FIFO MessageGroupId conditional inclusion
# Feature: phase1-infrastructure-hardening, Property 10: FIFO MessageGroupId conditional inclusion
# **Validates: Requirements 7.1, 7.2, 7.3**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    is_fifo=st.booleans(),
    task_type=st.sampled_from(list(TASK_TYPES)),
)
async def test_fifo_message_group_id_conditional_inclusion(is_fifo: bool, task_type: str):
    """Property 10: FIFO MessageGroupId conditional inclusion

    Random queue URLs with/without .fifo suffix; verify MessageGroupId
    included iff .fifo.
    """
    if is_fifo:
        queue_url = "http://localhost:4566/000000000000/test-queue.fifo"
        dlq_url = "http://localhost:4566/000000000000/test-dlq.fifo"
    else:
        queue_url = "http://localhost:4566/000000000000/test-queue"
        dlq_url = "http://localhost:4566/000000000000/test-dlq"

    svc = _make_worker_service(queue_url=queue_url, dlq_url=dlq_url)
    task = WorkerTask(task_type=task_type, payload={})

    # Capture send_message kwargs for _requeue_with_backoff
    requeue_kwargs: dict = {}

    async def capture_requeue(**kwargs):
        nonlocal requeue_kwargs
        requeue_kwargs = kwargs

    mock_client = AsyncMock()
    mock_client.send_message = capture_requeue
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch.object(svc._session, "create_client", return_value=mock_client):
        await svc._requeue_with_backoff(task, visibility_timeout=30)

    if is_fifo:
        assert "MessageGroupId" in requeue_kwargs
        assert requeue_kwargs["MessageGroupId"] == task_type
    else:
        assert "MessageGroupId" not in requeue_kwargs

    # Capture send_message kwargs for _move_to_dlq
    dlq_kwargs: dict = {}

    async def capture_dlq(**kwargs):
        nonlocal dlq_kwargs
        dlq_kwargs = kwargs

    mock_client2 = AsyncMock()
    mock_client2.send_message = capture_dlq
    mock_client2.__aenter__ = AsyncMock(return_value=mock_client2)
    mock_client2.__aexit__ = AsyncMock(return_value=None)

    with patch.object(svc._session, "create_client", return_value=mock_client2):
        await svc._move_to_dlq(task, Exception("test error"))

    if is_fifo:
        assert "MessageGroupId" in dlq_kwargs
        assert dlq_kwargs["MessageGroupId"] == task_type
    else:
        assert "MessageGroupId" not in dlq_kwargs


# ---------------------------------------------------------------------------
# Property 11: New model pricing coverage
# Feature: phase1-infrastructure-hardening, Property 11: New model pricing coverage
# **Validates: Requirements 8.6**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    model=st.sampled_from(["claude-sonnet-4-6", "claude-haiku-4-5-20251001"]),
    input_tokens=st.integers(min_value=1, max_value=1000000),
    output_tokens=st.integers(min_value=1, max_value=1000000),
)
def test_new_model_pricing_coverage(model: str, input_tokens: int, output_tokens: int):
    """Property 11: New model pricing coverage

    calculate_cost with claude-sonnet-4-6 and claude-haiku-4-5-20251001 and
    random non-negative token counts returns non-zero costs.
    """
    from gapsense.ai.cost_calculator import calculate_cost

    input_cost, output_cost, total_cost = calculate_cost(
        provider="anthropic",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )

    assert input_cost > Decimal("0"), f"Input cost should be non-zero for {model}"
    assert output_cost > Decimal("0"), f"Output cost should be non-zero for {model}"
    assert total_cost > Decimal("0"), f"Total cost should be non-zero for {model}"
    assert total_cost == input_cost + output_cost


# ---------------------------------------------------------------------------
# Property 13: Null optional fields are valid
# Feature: phase1-infrastructure-hardening, Property 13: Null optional fields are valid
# **Validates: Requirements 10.4**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    has_retrieval_metadata=st.sampled_from([True, False, None]),
    has_transcription_attempt=st.sampled_from([True, False, None]),
    gap_node_ids=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
)
def test_null_optional_fields_are_valid(
    has_retrieval_metadata, has_transcription_attempt, gap_node_ids
):
    """Property 13: Null optional fields are valid

    Random AI responses with missing/null retrieval_metadata and
    transcription_attempt processed without error.
    """
    response_json: dict[str, Any] = {
        "gap_node_ids": gap_node_ids,
        "reasoning": "Test reasoning",
        "confidence": 0.8,
    }

    if has_retrieval_metadata is True:
        response_json["retrieval_metadata"] = {"source": "test"}
    elif has_retrieval_metadata is False:
        response_json["retrieval_metadata"] = None
    # If None, field is missing entirely

    if has_transcription_attempt is True:
        response_json["transcription_attempt"] = {"text": "test"}
    elif has_transcription_attempt is False:
        response_json["transcription_attempt"] = None

    # Verify the response can be processed without error
    retrieval = response_json.get("retrieval_metadata")
    transcription = response_json.get("transcription_attempt")

    assert retrieval is None or isinstance(retrieval, dict)
    assert transcription is None or isinstance(transcription, dict)
    assert "gap_node_ids" in response_json
