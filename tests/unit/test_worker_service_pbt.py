"""
Property-based tests for WorkerService.

# Feature: mvp-core-services, Property 16: Worker Task Retry Lifecycle
# Feature: mvp-core-services, Property 17: Worker Concurrency Limit
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.services.worker_service import WorkerService, WorkerTask

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_worker_service(max_concurrent: int = 5) -> WorkerService:
    mock_settings = MagicMock()
    mock_settings.SQS_QUEUE_URL = "http://localhost:4566/000000000000/test-queue"
    mock_settings.SQS_DLQ_URL = "http://localhost:4566/000000000000/test-dlq"
    mock_settings.AWS_REGION = "af-south-1"
    mock_settings.AWS_ACCESS_KEY_ID = "test"
    mock_settings.AWS_SECRET_ACCESS_KEY = "test"

    return WorkerService(
        ai_client=MagicMock(),
        media_service=MagicMock(),
        guard_service=MagicMock(),
        prompt_service=MagicMock(),
        settings=mock_settings,
        max_concurrent=max_concurrent,
    )


# ---------------------------------------------------------------------------
# Property 16: Worker Task Retry Lifecycle
# **Validates: Requirements 8.7, 8.8**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    retry_count=st.integers(min_value=0, max_value=10),
    max_retries=st.integers(min_value=1, max_value=5),
)
async def test_worker_task_retry_lifecycle(retry_count: int, max_retries: int):
    """Property 16: Worker Task Retry Lifecycle

    For failed task with retry_count < max_retries: re-enqueue with retry_count + 1.
    For retry_count >= max_retries: move to DLQ.
    """
    svc = _make_worker_service()

    task = WorkerTask(
        task_type="tts_generate",
        payload={"text": "hello"},
        retry_count=retry_count,
        max_retries=max_retries,
        receipt_handle="test-receipt",
    )

    requeue_called = False
    dlq_called = False
    requeued_retry_count = None

    async def mock_requeue(t, visibility_timeout):
        nonlocal requeue_called, requeued_retry_count
        requeue_called = True
        requeued_retry_count = t.retry_count

    async def mock_dlq(t, error):
        nonlocal dlq_called
        dlq_called = True

    svc._requeue_with_backoff = mock_requeue
    svc._move_to_dlq = mock_dlq
    svc._delete_message = AsyncMock()

    error = Exception("test failure")
    await svc._handle_failure(task, error)

    if retry_count < max_retries:
        assert requeue_called, "Expected task to be re-enqueued"
        assert not dlq_called, "Task should not go to DLQ when retries remain"
        assert (
            requeued_retry_count == retry_count + 1
        ), f"Expected retry_count={retry_count + 1}, got {requeued_retry_count}"
    else:
        assert dlq_called, "Expected task to be moved to DLQ"
        assert not requeue_called, "Task should not be re-enqueued when max retries exceeded"


# ---------------------------------------------------------------------------
# Property 17: Worker Concurrency Limit
# **Validates: Requirements 8.9**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    num_tasks=st.integers(min_value=2, max_value=20),
    concurrency_limit=st.integers(min_value=1, max_value=5),
)
async def test_worker_concurrency_limit(num_tasks: int, concurrency_limit: int):
    """Property 17: Worker Concurrency Limit

    For any batch exceeding concurrency limit, concurrent processing count
    never exceeds the limit.
    """
    svc = _make_worker_service(max_concurrent=concurrency_limit)

    max_in_flight = 0
    current_in_flight = 0
    lock = asyncio.Lock()

    original_route = svc._route_task

    async def tracking_route(task):
        nonlocal max_in_flight, current_in_flight
        async with lock:
            current_in_flight += 1
            max_in_flight = max(current_in_flight, max_in_flight)
        await asyncio.sleep(0.01)
        async with lock:
            current_in_flight -= 1

    svc._route_task = tracking_route
    svc._delete_message = AsyncMock()

    # Build mock SQS messages
    messages = []
    for i in range(num_tasks):
        messages.append(
            {
                "MessageId": f"msg-{i}",
                "ReceiptHandle": f"receipt-{i}",
                "Body": json.dumps(
                    {
                        "task_type": "tts_generate",
                        "payload": {"text": f"task {i}"},
                        "retry_count": 0,
                        "max_retries": 3,
                    }
                ),
            }
        )

    # Process all messages concurrently
    tasks = [svc._process_message(msg) for msg in messages]
    await asyncio.gather(*tasks)

    assert (
        max_in_flight <= concurrency_limit
    ), f"Max in-flight {max_in_flight} exceeded concurrency limit {concurrency_limit}"
