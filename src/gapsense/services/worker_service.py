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
from typing import Any

import structlog
from aiobotocore.session import get_session

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
        db: Any = None,
        max_concurrent: int = 5,
    ) -> None:
        self._ai_client = ai_client
        self._media_service = media_service
        self._guard_service = guard_service
        self._prompt_service = prompt_service
        self._settings = settings
        self._db = db
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
        return msg_id

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
        """Process a single SQS message with concurrency control."""
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

            start = time.perf_counter()
            try:
                logger.info(
                    "task_started",
                    task_type=task.task_type,
                    message_id=task.message_id,
                )
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

    async def _route_task(self, task: WorkerTask) -> None:
        """Route task to appropriate handler."""
        handlers = {
            "tts_generate": self._handle_tts_generate,
            "image_analyze": self._handle_image_analyze,
            "scheduled_message": self._handle_scheduled_message,
            "voice_transcribe": self._handle_voice_transcribe,
        }
        handler = handlers.get(task.task_type)
        if handler is None:
            raise ValueError(f"Unknown task type: {task.task_type}")
        await handler(task)

    # ------------------------------------------------------------------
    # Task handlers
    # ------------------------------------------------------------------

    async def _handle_tts_generate(self, task: WorkerTask) -> None:
        """TTS generation: invoke TTS, upload to S3 via MediaService."""
        payload = task.payload
        text_content = payload.get("text", "")
        language = payload.get("language", "en")
        country = payload.get("country", "GH")
        student_id = payload.get("student_id", "")

        logger.info(
            "tts_generate_start",
            language=language,
            country=country,
            student_id=student_id,
        )
        # TTS_Service integration point — placeholder for actual TTS call
        # audio_bytes = await tts_service.synthesize(text_content, language)
        # s3_key = await self._media_service.upload(
        #     audio_bytes, country=country, student_id=student_id,
        #     media_type="audio", filename=f"tts_{language}.ogg",
        #     content_type="audio/ogg",
        # )
        logger.info("tts_generate_complete", student_id=student_id)

    async def _handle_image_analyze(self, task: WorkerTask) -> None:
        """Delegate entirely to ImageAnalysisOrchestrator with its own DB session."""
        from gapsense.core.database import AsyncSessionLocal
        from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

        # Log handler entry
        logger.info(
            "image_analyze_handler_start",
            student_id=task.payload.get("student_id"),
            s3_key=task.payload.get("s3_key"),
            country=task.payload.get("country"),
            language=task.payload.get("language"),
        )

        # Create a fresh DB session for this task (no shared session)
        async with AsyncSessionLocal() as db_session:
            orchestrator = ImageAnalysisOrchestrator(
                db=db_session,
                ai_client=self._ai_client,
                media_service=self._media_service,
                guard_service=self._guard_service,
                prompt_service=self._prompt_service,
                worker_service=self,
            )
            await orchestrator.run(task.payload)

        logger.info(
            "image_analyze_handler_complete",
            student_id=task.payload.get("student_id"),
        )

    async def _handle_scheduled_message(self, task: WorkerTask) -> None:
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

    async def _handle_voice_transcribe(self, task: WorkerTask) -> None:
        """Voice transcription: download audio, transcribe via STT."""
        payload = task.payload
        s3_key = payload.get("s3_key", "")
        parent_id = payload.get("parent_id", "")

        logger.info("voice_transcribe_start", s3_key=s3_key, parent_id=parent_id)

        # Download audio from S3
        audio_bytes = await self._media_service.download(s3_key)

        # STT_Service integration point — placeholder for actual STT call
        # transcript = await stt_service.transcribe(audio_bytes, language)
        logger.info("voice_transcribe_complete", parent_id=parent_id)

    # ------------------------------------------------------------------
    # Failure handling
    # ------------------------------------------------------------------

    async def _handle_failure(self, task: WorkerTask, error: Exception) -> None:
        """Handle task failure: re-enqueue or move to DLQ."""
        # Delete the original message first
        if task.receipt_handle:
            await self._delete_message(task.receipt_handle)

        if task.retry_count < task.max_retries:
            # Re-enqueue with incremented retry count and backoff
            new_task = WorkerTask(
                task_type=task.task_type,
                payload=task.payload,
                retry_count=task.retry_count + 1,
                max_retries=task.max_retries,
            )
            visibility_timeout = 2**task.retry_count * 30  # 30s, 60s, 120s
            await self._requeue_with_backoff(new_task, visibility_timeout)
            logger.info(
                "task_requeued",
                task_type=task.task_type,
                retry_count=new_task.retry_count,
                visibility_timeout=visibility_timeout,
            )
        else:
            # Move to DLQ
            await self._move_to_dlq(task, error)
            logger.error(
                "task_moved_to_dlq",
                task_type=task.task_type,
                retry_count=task.retry_count,
                error=str(error),
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
        async with self._session.create_client(**self._client_kwargs()) as client:
            await client.send_message(
                QueueUrl=self._queue_url,
                MessageBody=body,
                DelaySeconds=min(visibility_timeout, 900),  # SQS max is 900s
            )

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
        async with self._session.create_client(**self._client_kwargs()) as client:
            await client.send_message(
                QueueUrl=self._dlq_url,
                MessageBody=body,
            )

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
