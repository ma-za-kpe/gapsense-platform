"""
Worker Service for Background Processing

SQS-backed background task processor for TTS generation, image analysis,
scheduled message delivery, and voice transcription.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from aiobotocore.session import get_session  # type: ignore[import-untyped]
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from gapsense.core.exceptions import PermanentError
from gapsense.core.models.processing_ledger import ProcessingLedger
from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = structlog.get_logger(__name__)

# Supported task types
TASK_TYPES = frozenset({"tts_generate", "image_analyze", "scheduled_message", "voice_transcribe"})


@dataclass
class WorkerTask:
    """A background task to be processed."""

    task_type: str
    payload: dict[str, Any]
    retry_count: int = 0
    max_retries: int = 3
    message_id: str | None = None
    receipt_handle: str | None = None


class WorkerService:
    """SQS-backed background task processor."""

    def __init__(
        self,
        ai_client: Any,
        media_service: Any,
        guard_service: Any,
        prompt_service: Any,
        settings: Any,
        session_factory: Any = None,
        max_concurrent: int = 5,
    ) -> None:
        self._ai_client = ai_client
        self._media_service = media_service
        self._guard_service = guard_service
        self._prompt_service = prompt_service
        self._settings = settings
        self._session_factory = session_factory
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._session = get_session()
        self._queue_url = getattr(settings, "SQS_QUEUE_URL", "") or os.environ.get(
            "SQS_QUEUE_URL", ""
        )
        self._dlq_url = getattr(settings, "SQS_DLQ_URL", "") or os.environ.get("SQS_DLQ_URL", "")
        self._region = getattr(settings, "AWS_REGION", "af-south-1")
        self._endpoint_url: str | None = os.environ.get("SQS_ENDPOINT_URL") or os.environ.get(
            "S3_ENDPOINT_URL"
        )

    def _client_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "service_name": "sqs",
            "region_name": self._region,
        }
        access_key = getattr(self._settings, "AWS_ACCESS_KEY_ID", None)
        secret_key = getattr(self._settings, "AWS_SECRET_ACCESS_KEY", None)
        if access_key:
            kwargs["aws_access_key_id"] = access_key
        if secret_key:
            kwargs["aws_secret_access_key"] = secret_key
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start long-polling SQS consumer loop."""
        self._running = True
        logger.info("worker_started", queue_url=self._queue_url)
        while self._running:
            try:
                await self._poll_once()
            except Exception as exc:
                logger.error("worker_poll_error", error=str(exc))
                await asyncio.sleep(5)

    async def stop(self) -> None:
        """Graceful shutdown."""
        self._running = False
        logger.info("worker_stopped")

    async def enqueue(self, task: WorkerTask) -> str:
        """Send task to SQS queue. Returns message ID."""
        body = json.dumps(
            {
                "task_type": task.task_type,
                "payload": task.payload,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
            }
        )
        async with self._session.create_client(**self._client_kwargs()) as client:
            # If queue_url looks like just a name, resolve it
            queue_url = self._queue_url
            if not queue_url.startswith("http"):
                # It's a queue name, get the URL
                response = await client.get_queue_url(QueueName=queue_url)
                queue_url = response["QueueUrl"]
                logger.debug("resolved_queue_url", name=self._queue_url, url=queue_url)

            # Prepare send_message kwargs
            send_kwargs = {
                "QueueUrl": queue_url,
                "MessageBody": body,
            }

            # FIFO queues require MessageGroupId
            if queue_url.endswith(".fifo"):
                send_kwargs["MessageGroupId"] = task.task_type

            resp = await client.send_message(**send_kwargs)
        msg_id = resp.get("MessageId", "")
        logger.info("task_enqueued", task_type=task.task_type, message_id=msg_id)
        return msg_id  # type: ignore[no-any-return]

    # ------------------------------------------------------------------
    # Polling
    # ------------------------------------------------------------------

    async def _poll_once(self) -> None:
        """Poll SQS for messages and process them."""
        async with self._session.create_client(**self._client_kwargs()) as client:
            resp = await client.receive_message(
                QueueUrl=self._queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,
            )
        messages = resp.get("Messages", [])
        if not messages:
            return

        tasks = []
        for msg in messages:
            tasks.append(self._process_message(msg))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_message(self, msg: dict[str, Any]) -> None:
        """Process a single SQS message with concurrency control and heartbeat."""
        async with self._semaphore:
            body = json.loads(msg.get("Body", "{}"))
            task = WorkerTask(
                task_type=body.get("task_type", ""),
                payload=body.get("payload", {}),
                retry_count=body.get("retry_count", 0),
                max_retries=body.get("max_retries", 3),
                message_id=msg.get("MessageId"),
                receipt_handle=msg.get("ReceiptHandle"),
            )

            # Log task received with sanitized payload
            payload_summary = {
                k: v if k not in ["image_bytes", "image_bytes_b64"] else f"<{len(str(v))} bytes>"
                for k, v in task.payload.items()
            }
            logger.info(
                "task_received",
                task_type=task.task_type,
                message_id=task.message_id,
                retry_count=task.retry_count,
                payload_keys=list(task.payload.keys()),
                payload_summary=payload_summary,
            )

            # Start heartbeat to prevent SQS redelivery during long processing
            # Phase 4: Heartbeat every 45s, extending visibility by 90s
            heartbeat_task = None
            if task.receipt_handle:
                heartbeat_task = asyncio.create_task(
                    self._heartbeat_loop(
                        receipt_handle=task.receipt_handle,
                        interval=45,
                        extension=90,
                    )
                )
                logger.debug(
                    "heartbeat_started",
                    task_type=task.task_type,
                    message_id=task.message_id,
                )

            start = time.perf_counter()
            try:
                logger.info(
                    "task_started",
                    task_type=task.task_type,
                    message_id=task.message_id,
                )
                if self._session_factory:
                    async with self._session_factory() as db:
                        # Idempotency guard: INSERT ... ON CONFLICT DO NOTHING
                        stmt = (
                            pg_insert(ProcessingLedger)
                            .values(
                                sqs_message_id=task.message_id,
                                task_type=task.task_type,
                                student_id=task.payload.get("student_id"),
                            )
                            .on_conflict_do_nothing(constraint="uq_ledger_msg_task")
                        )
                        result = await db.execute(stmt)
                        await db.commit()

                        if result.rowcount == 0:
                            # Duplicate — skip processing
                            logger.warning(
                                "duplicate_message_skipped",
                                sqs_message_id=task.message_id,
                            )
                            await self._delete_message(task.receipt_handle)
                            return

                        await self._route_task(task, db=db)

                        # Update ledger status to completed
                        await db.execute(
                            update(ProcessingLedger)
                            .where(
                                ProcessingLedger.sqs_message_id == task.message_id,
                                ProcessingLedger.task_type == task.task_type,
                            )
                            .values(
                                status="completed",
                                completed_at=datetime.now(UTC),
                            )
                        )
                        await db.commit()
                else:
                    await self._route_task(task)
                # Delete message on success
                await self._delete_message(task.receipt_handle)
                latency_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "task_completed",
                    task_type=task.task_type,
                    message_id=task.message_id,
                    latency_ms=round(latency_ms, 2),
                )
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    "task_failed",
                    task_type=task.task_type,
                    message_id=task.message_id,
                    retry_count=task.retry_count,
                    error=str(exc),
                    error_type=type(exc).__name__,
                    latency_ms=round(latency_ms, 2),
                    exc_info=True,
                )
                await self._handle_failure(task, exc)
            finally:
                # Stop heartbeat when task completes (success or failure)
                if heartbeat_task:
                    heartbeat_task.cancel()
                    try:
                        await heartbeat_task
                    except asyncio.CancelledError:
                        pass
                    logger.debug(
                        "heartbeat_stopped",
                        task_type=task.task_type,
                        message_id=task.message_id,
                    )

    async def _route_task(self, task: WorkerTask, db: Any = None) -> None:
        """Route task to appropriate handler."""
        if task.task_type not in TASK_TYPES:
            raise ValueError(f"Unknown task type: {task.task_type}")

        handlers = {
            "tts_generate": self._handle_tts_generate,
            "image_analyze": self._handle_image_analyze,
            "scheduled_message": self._handle_scheduled_message,
            "voice_transcribe": self._handle_voice_transcribe,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            raise ValueError(f"Unknown task type: {task.task_type}")
        await handler(task, db=db)

    # ------------------------------------------------------------------
    # Task handlers
    # ------------------------------------------------------------------

    async def _handle_tts_generate(self, task: WorkerTask, db: Any = None) -> None:
        """TTS generation: not yet implemented."""
        raise NotImplementedError("TTS generation is not yet implemented")

    async def _handle_image_analyze(self, task: WorkerTask, db: Any = None) -> None:
        """Delegate entirely to ImageAnalysisOrchestrator with its own DB session."""
        from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

        # Log handler entry
        logger.info(
            "image_analyze_handler_start",
            student_id=task.payload.get("student_id"),
            s3_key=task.payload.get("s3_key"),
            country=task.payload.get("country"),
            language=task.payload.get("language"),
        )

        # Construct EmbeddingService (None if config missing / not available)
        embedding_service = None
        try:
            from gapsense.ai.embedding_service import EmbeddingService

            embedding_service = EmbeddingService(self._settings)
        except Exception:
            logger.warning("embedding_service_unavailable", exc_info=True)

        # Use the per-task session provided by _process_message via session_factory
        if db is not None:
            orchestrator = ImageAnalysisOrchestrator(
                db=db,
                ai_client=self._ai_client,
                media_service=self._media_service,
                guard_service=self._guard_service,
                prompt_service=self._prompt_service,
                worker_service=self,
                embedding_service=embedding_service,
            )
            await orchestrator.run(task.payload)
        elif self._session_factory:
            async with self._session_factory() as db_session:
                orchestrator = ImageAnalysisOrchestrator(
                    db=db_session,
                    ai_client=self._ai_client,
                    media_service=self._media_service,
                    guard_service=self._guard_service,
                    prompt_service=self._prompt_service,
                    worker_service=self,
                    embedding_service=embedding_service,
                )
                await orchestrator.run(task.payload)
        else:
            raise RuntimeError(
                "image_analyze requires a database session but no session_factory is configured"
            )

        logger.info(
            "image_analyze_handler_complete",
            student_id=task.payload.get("student_id"),
        )

    async def _handle_scheduled_message(self, task: WorkerTask, db: Any = None) -> None:
        """Scheduled message: pass through GuardService before delivery."""
        payload = task.payload
        message = payload.get("message", "")
        country = payload.get("country", "GH")
        language = payload.get("language", "en")
        student_context = payload.get("student_context", {})

        guard_result = await self._guard_service.check(
            message,
            student_context=student_context,
            country=country,
            language=language,
        )

        if guard_result.passed:
            logger.info("scheduled_message_delivered")
            client = WhatsAppClient.from_settings()
            await client.send_text_message(
                to=payload.get("recipient_phone", ""),
                text=message,
            )
        else:
            logger.warning(
                "scheduled_message_blocked",
                violations=guard_result.violations,
            )

    async def _handle_voice_transcribe(self, task: WorkerTask, db: Any = None) -> None:
        """Voice transcription: not yet implemented."""
        raise NotImplementedError("Voice transcription is not yet implemented")

    # ------------------------------------------------------------------
    # Failure handling
    # ------------------------------------------------------------------

    async def _handle_failure(self, task: WorkerTask, error: Exception) -> None:
        """Handle task failure: route PermanentError to DLQ immediately, retry others.

        IMPORTANT: Send to requeue/DLQ BEFORE deleting original message.
        If send fails, do NOT delete — let SQS redeliver after visibility timeout.
        """
        if isinstance(error, PermanentError):
            # PermanentError → DLQ immediately, regardless of retry_count
            try:
                await self._move_to_dlq(task, error)
                # Only delete after successful DLQ send
                if task.receipt_handle:
                    await self._delete_message(task.receipt_handle)
                # Update ledger status to failed
                if self._session_factory and task.message_id:
                    try:
                        async with self._session_factory() as db:
                            await db.execute(
                                update(ProcessingLedger)
                                .where(
                                    ProcessingLedger.sqs_message_id == task.message_id,
                                    ProcessingLedger.task_type == task.task_type,
                                )
                                .values(status="failed")
                            )
                            await db.commit()
                    except Exception as ledger_exc:
                        logger.warning(
                            "ledger_status_update_failed",
                            sqs_message_id=task.message_id,
                            error=str(ledger_exc),
                        )
                logger.error(
                    "task_moved_to_dlq",
                    task_type=task.task_type,
                    retry_count=task.retry_count,
                    error=str(error),
                    error_type="PermanentError",
                )
            except Exception as send_exc:
                # DLQ send failed — do NOT delete original message
                # SQS will redeliver after visibility timeout
                logger.error(
                    "dlq_send_failed_message_preserved",
                    task_type=task.task_type,
                    retry_count=task.retry_count,
                    original_error=str(error),
                    send_error=str(send_exc),
                )
        elif task.retry_count < task.max_retries:
            # RetryableError or other exception — retry with backoff
            new_task = WorkerTask(
                task_type=task.task_type,
                payload=task.payload,
                retry_count=task.retry_count + 1,
                max_retries=task.max_retries,
            )
            visibility_timeout = 2**task.retry_count * 30  # 30s, 60s, 120s
            try:
                await self._requeue_with_backoff(new_task, visibility_timeout)
                # Only delete after successful requeue
                if task.receipt_handle:
                    await self._delete_message(task.receipt_handle)
                logger.info(
                    "task_requeued",
                    task_type=task.task_type,
                    retry_count=new_task.retry_count,
                    visibility_timeout=visibility_timeout,
                )
            except Exception as send_exc:
                # Requeue failed — do NOT delete original message
                # SQS will redeliver after visibility timeout
                logger.error(
                    "requeue_failed_message_preserved",
                    task_type=task.task_type,
                    retry_count=task.retry_count,
                    original_error=str(error),
                    send_error=str(send_exc),
                )
        else:
            # RetryableError or other exception — max retries exhausted, move to DLQ
            try:
                await self._move_to_dlq(task, error)
                # Only delete after successful DLQ send
                if task.receipt_handle:
                    await self._delete_message(task.receipt_handle)
                # Update ledger status to failed
                if self._session_factory and task.message_id:
                    try:
                        async with self._session_factory() as db:
                            await db.execute(
                                update(ProcessingLedger)
                                .where(
                                    ProcessingLedger.sqs_message_id == task.message_id,
                                    ProcessingLedger.task_type == task.task_type,
                                )
                                .values(status="failed")
                            )
                            await db.commit()
                    except Exception as ledger_exc:
                        logger.warning(
                            "ledger_status_update_failed",
                            sqs_message_id=task.message_id,
                            error=str(ledger_exc),
                        )
                logger.error(
                    "task_moved_to_dlq",
                    task_type=task.task_type,
                    retry_count=task.retry_count,
                    error=str(error),
                )
            except Exception as send_exc:
                # DLQ send failed — do NOT delete original message
                # SQS will redeliver after visibility timeout
                logger.error(
                    "dlq_send_failed_message_preserved",
                    task_type=task.task_type,
                    retry_count=task.retry_count,
                    original_error=str(error),
                    send_error=str(send_exc),
                )

    async def _requeue_with_backoff(self, task: WorkerTask, visibility_timeout: int) -> None:
        """Re-enqueue task with visibility timeout for backoff."""
        body = json.dumps(
            {
                "task_type": task.task_type,
                "payload": task.payload,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
            }
        )
        send_kwargs: dict[str, Any] = {
            "QueueUrl": self._queue_url,
            "MessageBody": body,
            "DelaySeconds": min(visibility_timeout, 900),  # SQS max is 900s
        }
        if self._queue_url.endswith(".fifo"):
            send_kwargs["MessageGroupId"] = task.task_type
        async with self._session.create_client(**self._client_kwargs()) as client:
            await client.send_message(**send_kwargs)

    async def _move_to_dlq(self, task: WorkerTask, error: Exception) -> None:
        """Move failed task to dead-letter queue."""
        if not self._dlq_url:
            logger.warning("no_dlq_configured", task_type=task.task_type)
            return

        body = json.dumps(
            {
                "task_type": task.task_type,
                "payload": task.payload,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "error": str(error),
            }
        )
        send_kwargs: dict[str, Any] = {
            "QueueUrl": self._dlq_url,
            "MessageBody": body,
        }
        if self._dlq_url.endswith(".fifo"):
            send_kwargs["MessageGroupId"] = task.task_type
        async with self._session.create_client(**self._client_kwargs()) as client:
            await client.send_message(**send_kwargs)

    async def _delete_message(self, receipt_handle: str | None) -> None:
        """Delete a processed message from the queue."""
        if not receipt_handle:
            return
        try:
            async with self._session.create_client(**self._client_kwargs()) as client:
                await client.delete_message(
                    QueueUrl=self._queue_url,
                    ReceiptHandle=receipt_handle,
                )
        except Exception as exc:
            logger.warning("message_delete_failed", error=str(exc))

    # ------------------------------------------------------------------
    # SQS Visibility Timeout Heartbeat (Phase 4)
    # ------------------------------------------------------------------

    async def _extend_visibility_timeout(
        self,
        receipt_handle: str,
        extension_seconds: int = 90,
    ) -> None:
        """Extend SQS message visibility to prevent redelivery during long processing.

        Args:
            receipt_handle: SQS message receipt handle
            extension_seconds: How long to extend visibility (default 90s)
        """
        try:
            async with self._session.create_client(**self._client_kwargs()) as client:
                await client.change_message_visibility(
                    QueueUrl=self._queue_url,
                    ReceiptHandle=receipt_handle,
                    VisibilityTimeout=extension_seconds,
                )
            logger.debug(
                "visibility_timeout_extended",
                extension_seconds=extension_seconds,
            )
        except Exception as exc:
            logger.warning(
                "visibility_timeout_extension_failed",
                error=str(exc),
                exc_info=True,
            )

    async def _heartbeat_loop(
        self,
        receipt_handle: str,
        interval: int,
        extension: int,
    ) -> None:
        """Periodic visibility timeout extension heartbeat.

        Runs in background during long-running task processing. Cancelled when task completes.

        Args:
            receipt_handle: SQS message receipt handle
            interval: Seconds between heartbeat extensions
            extension: Visibility timeout extension amount in seconds
        """
        try:
            while True:
                await asyncio.sleep(interval)
                await self._extend_visibility_timeout(receipt_handle, extension)
        except asyncio.CancelledError:
            # Normal shutdown when task completes
            logger.debug("heartbeat_cancelled")
            raise
