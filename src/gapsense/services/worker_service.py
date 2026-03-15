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

            start = time.perf_counter()
            try:
                await self._route_task(task)
                # Delete message on success
                await self._delete_message(task.receipt_handle)
                latency_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "task_completed",
                    task_type=task.task_type,
                    latency_ms=round(latency_ms, 2),
                )
            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                logger.error(
                    "task_failed",
                    task_type=task.task_type,
                    retry_count=task.retry_count,
                    error=str(exc),
                    latency_ms=round(latency_ms, 2),
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
        """Image analysis: download from S3, send to AI with ANALYSIS-001."""
        import base64
        import json
        from uuid import UUID

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from gapsense.ai.async_client import ImageContent
        from gapsense.core.models import Student
        from gapsense.core.models.curriculum import (
            CurriculumIndicator,
            CurriculumNode,
            IndicatorErrorPattern,
        )

        payload = task.payload
        s3_key = payload.get("s3_key", "")
        student_id = payload.get("student_id", "")
        country_code = payload.get("country", "GH")

        logger.info("image_analyze_start", s3_key=s3_key, student_id=student_id)

        # 1. Load student with school and teacher to get context
        result = await self._db.execute(
            select(Student)
            .where(Student.id == UUID(student_id))
            .options(
                selectinload(Student.school),
                selectinload(Student.teacher),
            )
        )
        student = result.scalar_one_or_none()
        if not student:
            raise ValueError(f"Student {student_id} not found")

        student_grade = student.current_grade  # e.g., "JHS1"

        # Derive country and subject from context
        from gapsense.core.country_utils import get_country_from_student, get_subject_from_teacher

        country_key = get_country_from_student(student)
        subject = get_subject_from_teacher(student.teacher, default="mathematics")

        # 2. Download image
        image_bytes = await self._media_service.download(s3_key)

        # 3. Load curriculum nodes for this grade/country/subject
        curriculum_result = await self._db.execute(
            select(CurriculumNode)
            .where(
                CurriculumNode.country == country_key,
                CurriculumNode.grade == student_grade,
                CurriculumNode.subject == subject,
            )
            .options(
                selectinload(CurriculumNode.indicators).selectinload(
                    CurriculumIndicator.error_patterns
                )
            )
            .limit(50)  # Limit to first 50 nodes to avoid token overflow
        )
        curriculum_nodes = curriculum_result.scalars().all()

        # 4. Build curriculum_graph JSON for prompt
        curriculum_graph = []
        for node in curriculum_nodes:
            node_data = {
                "node_id": str(node.id),
                "code": node.code,
                "title": node.title,
                "description": node.description,
                "indicators": [],
            }

            for indicator in node.indicators:
                indicator_data = {
                    "indicator_code": indicator.indicator_code,
                    "title": indicator.title,
                    "error_patterns": [
                        {
                            "error_description": ep.error_description,
                            "severity": ep.severity,
                        }
                        for ep in indicator.error_patterns
                    ],
                }
                node_data["indicators"].append(indicator_data)

            curriculum_graph.append(node_data)

        curriculum_graph_json = json.dumps(curriculum_graph, indent=2)

        # 5. Render ANALYSIS-001 prompt
        # PromptService will inject curriculum_authority, curriculum_name, grade_structure from country_config
        rendered = self._prompt_service.render_prompt(
            "ANALYSIS-001",
            country=country_key,
            extra_context={
                # Custom variables not in country_config
                "curriculum_nodes_json": curriculum_graph_json,
                "current_grade": student_grade,
                "student_name": student.first_name,
                "school_name": student.school.name if student.school else "Unknown School",
            },
        )

        # 6. Send to AI (detect image format from bytes)
        # Detect media type from image magic bytes
        media_type = "image/jpeg"  # default
        if image_bytes[:8] == b'\x89PNG\r\n\x1a\n':
            media_type = "image/png"
        elif image_bytes[:2] == b'\xff\xd8':
            media_type = "image/jpeg"
        elif image_bytes[:6] in (b'GIF87a', b'GIF89a'):
            media_type = "image/gif"
        elif image_bytes[:4] == b'RIFF' and image_bytes[8:12] == b'WEBP':
            media_type = "image/webp"

        image_b64 = base64.b64encode(image_bytes).decode()
        response = await self._ai_client.generate(
            prompt_id="ANALYSIS-001",
            system=rendered.system_prompt,
            messages=[{"role": "user", "content": rendered.user_template}],
            model=rendered.model,
            json_mode=True,
            images=[ImageContent(data=image_b64, media_type=media_type, source_type="base64")],
        )

        # 6b. Log AI usage and cost
        if response:
            from gapsense.ai.cost_calculator import calculate_cost
            from gapsense.core.models import AIUsageLog

            input_cost, output_cost, total_cost = calculate_cost(
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

            usage_log = AIUsageLog(
                student_id=student.id if student else None,
                teacher_id=student.teacher_id if student and student.teacher_id else None,
                provider=response.provider,
                model=response.model,
                prompt_id=response.prompt_id,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                input_cost_usd=input_cost,
                output_cost_usd=output_cost,
                total_cost_usd=total_cost,
                latency_ms=response.latency_ms,
                success=response.json_parsed is not None,
                error_message=None,
            )
            self._db.add(usage_log)
            await self._db.flush()

            logger.info(
                "ai_usage_logged",
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_cost_usd=float(total_cost),
            )

        # 7. Process results
        if response and response.json_parsed:
            # Log the full Grok response for debugging
            logger.info(
                "grok_analysis_response",
                student_id=student_id,
                response_keys=list(response.json_parsed.keys()),
                full_response=response.json_parsed,
            )
            logger.info(
                "image_analyze_complete",
                student_id=student_id,
                gaps_found=len(response.json_parsed.get("gap_node_ids", [])),
            )

            from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner

            scanner = ExerciseBookScanner(
                db=self._db,
                media_service=self._media_service,
                worker_service=self,
                guard_service=self._guard_service,
                ai_client=self._ai_client,
                prompt_service=self._prompt_service,
            )
            await scanner.process_analysis_result(
                student_id=student_id,
                teacher_phone=payload.get("teacher_phone", ""),
                analysis=response.json_parsed,
                country=country_code,
                language=payload.get("language", "en"),
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
