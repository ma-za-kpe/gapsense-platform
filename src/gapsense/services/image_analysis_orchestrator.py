"""
ImageAnalysisOrchestrator

Owns the six-step pipeline for analysing a student's exercise book image.
WorkerService delegates entirely to this class — it knows nothing about
the pipeline's internals.

Steps:
    1. load_student_context   — DB: resolve student, country, subject, grade
    2. fetch_image            — S3: download bytes, detect media type
    3. build_curriculum_graph — DB: load nodes/indicators, serialise to JSON
    4. render_prompt          — PromptService: render ANALYSIS-001
    5. call_ai                — AI client: send image + prompt, log cost
    6. dispatch_results       — ExerciseBookScanner: process gap analysis
"""

from __future__ import annotations

import base64
import json
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from gapsense.ai.async_client import ImageContent
from gapsense.ai.cost_calculator import calculate_cost
from gapsense.core.country_utils import get_country_from_student, get_subject_from_teacher
from gapsense.core.models import AIUsageLog, Student
from gapsense.core.models.curriculum import CurriculumIndicator, CurriculumNode
from gapsense.services.image_analysis_context import ImageAnalysisContext

logger = structlog.get_logger(__name__)

# Curriculum node query limit.
# If your curriculum data grows past this, you will silently
# miss nodes. TODO: replace with paginated load or a filtered
# grade-range query once the grade normalisation issue is resolved.
_CURRICULUM_NODE_LIMIT = 100

# Magic bytes → MIME type mapping
_MEDIA_TYPE_MAP: list[tuple[bytes, int | None, bytes | None, str]] = [
    # (prefix, slice_end, slice_value, mime)
    (b"\x89PNG\r\n\x1a\n", None, None, "image/png"),
    (b"GIF87a", None, None, "image/gif"),
    (b"GIF89a", None, None, "image/gif"),
    (b"RIFF", 12, b"WEBP", "image/webp"),
]


def _detect_media_type(data: bytes) -> str:
    for prefix, extra_end, extra_val, mime in _MEDIA_TYPE_MAP:
        if data[: len(prefix)] == prefix:
            if extra_end is None or data[8:extra_end] == extra_val:
                return mime
    if data[:2] == b"\xff\xd8":
        return "image/jpeg"
    return "image/jpeg"


class ImageAnalysisOrchestrator:
    """Coordinates the full image-analysis pipeline for one student submission."""

    def __init__(
        self,
        db: Any,
        ai_client: Any,
        media_service: Any,
        guard_service: Any,
        prompt_service: Any,
        worker_service: Any,
    ) -> None:
        self._db = db
        self._ai_client = ai_client
        self._media_service = media_service
        self._guard_service = guard_service
        self._prompt_service = prompt_service
        self._worker_service = worker_service

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run(self, payload: dict[str, Any]) -> None:
        """Run the full pipeline for one image_analyze task payload."""
        import time

        pipeline_start = time.perf_counter()

        ctx = ImageAnalysisContext(
            s3_key=payload.get("s3_key", ""),
            student_id=payload.get("student_id", ""),
            country_code=payload.get("country", "GH"),
            language=payload.get("language", "en"),
            teacher_phone=payload.get("teacher_phone", ""),
        )

        logger.info(
            "image_analysis_pipeline_start",
            student_id=ctx.student_id,
            s3_key=ctx.s3_key,
            country=ctx.country_code,
            language=ctx.language,
        )

        try:
            step_start = time.perf_counter()
            await self._load_student_context(ctx)
            logger.info(
                "pipeline_step_1_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._fetch_image(ctx)
            logger.info(
                "pipeline_step_2_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._build_curriculum_graph(ctx)
            logger.info(
                "pipeline_step_3_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._render_prompt(ctx)
            logger.info(
                "pipeline_step_4_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._call_ai(ctx)
            logger.info(
                "pipeline_step_5_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._dispatch_results(ctx)
            logger.info(
                "pipeline_step_6_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
            logger.info(
                "image_analysis_pipeline_complete",
                student_id=ctx.student_id,
                total_latency_ms=total_latency_ms,
                success=True,
            )
        except Exception as exc:
            total_latency_ms = round((time.perf_counter() - pipeline_start) * 1000, 2)
            logger.error(
                "image_analysis_pipeline_failed",
                student_id=ctx.student_id,
                total_latency_ms=total_latency_ms,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            raise

    # ------------------------------------------------------------------
    # Step 1 — Resolve student context
    # ------------------------------------------------------------------

    async def _load_student_context(self, ctx: ImageAnalysisContext) -> None:
        """Load student row and derive country / subject / grade."""
        result = await self._db.execute(
            select(Student)
            .where(Student.id == UUID(ctx.student_id))
            .options(
                selectinload(Student.school),
                selectinload(Student.teacher),
            )
        )
        student = result.scalar_one_or_none()
        if not student:
            raise ValueError(f"Student {ctx.student_id} not found")

        ctx.student = student
        ctx.student_grade = student.current_grade
        ctx.country_key = get_country_from_student(student)
        ctx.subject = get_subject_from_teacher(student.teacher, default="mathematics")

        logger.info(
            "student_context_loaded",
            student_id=ctx.student_id,
            grade=ctx.student_grade,
            country=ctx.country_key,
            subject=ctx.subject,
        )

    # ------------------------------------------------------------------
    # Step 2 — Fetch image from S3
    # ------------------------------------------------------------------

    async def _fetch_image(self, ctx: ImageAnalysisContext) -> None:
        """Download image bytes and detect MIME type."""
        ctx.image_bytes = await self._media_service.download(ctx.s3_key)
        ctx.media_type = _detect_media_type(ctx.image_bytes)
        logger.info(
            "image_fetched",
            s3_key=ctx.s3_key,
            media_type=ctx.media_type,
            size_bytes=len(ctx.image_bytes),
        )

    # ------------------------------------------------------------------
    # Step 3 — Build curriculum graph
    # ------------------------------------------------------------------

    async def _build_curriculum_graph(self, ctx: ImageAnalysisContext) -> None:
        """Query curriculum nodes and serialise to JSON for the prompt."""
        curriculum_result = await self._db.execute(
            select(CurriculumNode)
            .where(
                CurriculumNode.country == ctx.country_key,
                CurriculumNode.subject == ctx.subject,
            )
            .options(
                selectinload(CurriculumNode.indicators).selectinload(
                    CurriculumIndicator.error_patterns
                )
            )
            .limit(_CURRICULUM_NODE_LIMIT)
        )
        nodes = curriculum_result.scalars().all()

        if len(nodes) == _CURRICULUM_NODE_LIMIT:
            logger.warning(
                "curriculum_node_limit_reached",
                country=ctx.country_key,
                subject=ctx.subject,
                limit=_CURRICULUM_NODE_LIMIT,
                message="Results may be incomplete. Consider paginating or adding a grade filter.",
            )

        graph = [
            {
                "node_id": str(node.id),
                "code": node.code,
                "title": node.title,
                "description": node.description,
                "indicators": [
                    {
                        "indicator_code": ind.indicator_code,
                        "title": ind.title,
                        "error_patterns": [
                            {
                                "error_description": ep.error_description,
                                "severity": ep.severity,
                            }
                            for ep in ind.error_patterns
                        ],
                    }
                    for ind in node.indicators
                ],
            }
            for node in nodes
        ]

        ctx.curriculum_graph_json = json.dumps(graph, indent=2)
        logger.info(
            "curriculum_graph_built",
            node_count=len(nodes),
            country=ctx.country_key,
            subject=ctx.subject,
        )

    # ------------------------------------------------------------------
    # Step 4 — Render prompt
    # ------------------------------------------------------------------

    async def _render_prompt(self, ctx: ImageAnalysisContext) -> None:
        """Render the ANALYSIS-001 prompt with student + curriculum context."""
        school_name = ctx.student.school.name if ctx.student.school else "Unknown School"

        ctx.rendered_prompt = self._prompt_service.render_prompt(
            "ANALYSIS-001",
            country=ctx.country_key,
            extra_context={
                "prerequisite_graph_json": ctx.curriculum_graph_json,
                "current_grade": ctx.student_grade,
                "student_name": ctx.student.first_name,
                "school_name": school_name,
            },
        )
        logger.info("prompt_rendered", prompt_id="ANALYSIS-001")

    # ------------------------------------------------------------------
    # Step 5 — Call AI and log cost
    # ------------------------------------------------------------------

    async def _call_ai(self, ctx: ImageAnalysisContext) -> None:
        """Send image + prompt to AI client and persist cost log."""
        rendered = ctx.rendered_prompt
        image_b64 = base64.b64encode(ctx.image_bytes).decode()

        response = await self._ai_client.generate(
            prompt_id="ANALYSIS-001",
            system=rendered.system_prompt,
            messages=[{"role": "user", "content": rendered.user_template}],
            model=rendered.model,
            max_tokens=rendered.max_tokens,
            temperature=rendered.temperature,
            json_mode=True,
            images=[
                ImageContent(
                    data=image_b64,
                    media_type=ctx.media_type,
                    source_type="base64",
                )
            ],
        )
        ctx.ai_response = response

        if response:
            await self._log_ai_cost(ctx, response)

        logger.info(
            "ai_call_complete",
            student_id=ctx.student_id,
            success=response is not None and response.json_parsed is not None,
        )

    async def _log_ai_cost(self, ctx: ImageAnalysisContext, response: Any) -> None:
        """Write AIUsageLog and commit. Isolated so failures don't kill the pipeline."""
        try:
            input_cost, output_cost, total_cost = calculate_cost(
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )
            usage_log = AIUsageLog(
                student_id=ctx.student.id,
                teacher_id=ctx.student.teacher_id,
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
            await self._db.commit()  # explicit commit — flush() alone is not enough

            logger.info(
                "ai_cost_logged",
                provider=response.provider,
                model=response.model,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                total_cost_usd=float(total_cost),
            )
        except Exception as exc:
            # Cost logging failure must not abort the analysis pipeline.
            # Log and move on; the analysis result is more valuable than the cost row.
            logger.warning("ai_cost_log_failed", error=str(exc))
            await self._db.rollback()

    # ------------------------------------------------------------------
    # Step 6 — Dispatch results to ExerciseBookScanner
    # ------------------------------------------------------------------

    async def _dispatch_results(self, ctx: ImageAnalysisContext) -> None:
        """Hand off parsed AI response to ExerciseBookScanner."""
        response = ctx.ai_response
        if not response or not response.json_parsed:
            logger.warning(
                "image_analyze_no_result",
                student_id=ctx.student_id,
                reason="AI returned no parseable JSON",
            )
            return

        logger.info(
            "analysis_response_received",
            student_id=ctx.student_id,
            response_keys=list(response.json_parsed.keys()),
            gaps_found=len(response.json_parsed.get("gap_node_ids", [])),
        )

        from gapsense.engagement.exercise_book_scanner import ExerciseBookScanner
        from gapsense.engagement.whatsapp_client import WhatsAppClient
        from gapsense.services.notification_service import (
            DemoNotificationService,
            WhatsAppNotificationService,
        )

        # Inject appropriate notification service based on teacher phone pattern
        # Demo phones: +2335000* prefix or ending with unlikely patterns
        # Note: Removed "1234567"/"01234567" as they can appear in valid phone numbers
        test_patterns = ["1111111", "2222222", "3333333", "0000000", "9999999"]
        is_demo = ctx.teacher_phone.startswith("+2335000") or any(
            ctx.teacher_phone.endswith(pattern) for pattern in test_patterns
        )

        if is_demo:
            notification_service = DemoNotificationService()
            logger.info("using_demo_notification_service", teacher_phone=ctx.teacher_phone)
        else:
            whatsapp_client = WhatsAppClient.from_settings()
            notification_service = WhatsAppNotificationService(whatsapp_client=whatsapp_client)
            logger.info("using_whatsapp_notification_service", teacher_phone=ctx.teacher_phone)

        scanner = ExerciseBookScanner(
            db=self._db,
            media_service=self._media_service,
            worker_service=self._worker_service,
            guard_service=self._guard_service,
            ai_client=self._ai_client,
            prompt_service=self._prompt_service,
            notification_service=notification_service,
        )
        await scanner.process_analysis_result(
            student_id=ctx.student_id,
            teacher_phone=ctx.teacher_phone,
            analysis=response.json_parsed,
            country=ctx.country_code,
            language=ctx.language,
        )
        logger.info("analysis_dispatched", student_id=ctx.student_id)
