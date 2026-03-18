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
from typing import TYPE_CHECKING, Any
from uuid import UUID

import structlog
import tiktoken  # type: ignore[import-not-found]
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import selectinload

from gapsense.ai.async_client import ImageContent
from gapsense.ai.cost_calculator import calculate_cost
from gapsense.core.country_utils import get_country_from_student, get_subject_from_teacher
from gapsense.core.models import AIUsageLog, Student
from gapsense.core.models.curriculum import CurriculumIndicator, CurriculumNode
from gapsense.services.image_analysis_context import ImageAnalysisContext

if TYPE_CHECKING:
    from gapsense.ai.embedding_service import EmbeddingService

logger = structlog.get_logger(__name__)

# Magic bytes → MIME type mapping
_MEDIA_TYPE_MAP: list[tuple[bytes, int | None, bytes | None, str]] = [
    (b"\x89PNG\r\n\x1a\n", None, None, "image/png"),
    (b"GIF87a", None, None, "image/gif"),
    (b"GIF89a", None, None, "image/gif"),
    (b"RIFF", 12, b"WEBP", "image/webp"),
]


def _detect_media_type(data: bytes) -> str:
    for prefix, extra_end, extra_val, mime in _MEDIA_TYPE_MAP:
        if data[: len(prefix)] == prefix and (extra_end is None or data[8:extra_end] == extra_val):
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
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._db = db
        self._ai_client = ai_client
        self._media_service = media_service
        self._guard_service = guard_service
        self._prompt_service = prompt_service
        self._worker_service = worker_service
        self._embedding_service = embedding_service

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
            await self._transcribe_image(ctx)
            logger.info(
                "pipeline_step_3_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._build_curriculum_graph(ctx)
            logger.info(
                "pipeline_step_4_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._render_prompt(ctx)
            logger.info(
                "pipeline_step_5_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._call_ai(ctx)
            logger.info(
                "pipeline_step_6_complete",
                latency_ms=round((time.perf_counter() - step_start) * 1000, 2),
            )

            step_start = time.perf_counter()
            await self._dispatch_results(ctx)
            logger.info(
                "pipeline_step_7_complete",
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
    # Step 3 — Transcribe image (NEW)
    # ------------------------------------------------------------------

    async def _transcribe_image(self, ctx: ImageAnalysisContext) -> None:
        """Stage 1: pure OCR transcription of the student exercise book image.

        Sends the image to the AI client with the TRANSCRIPTION-001 prompt
        and stores the structured JSON result and flat transcription text
        on the context.  On *any* failure the method logs a warning, sets
        safe defaults, and returns without raising — the pipeline degrades
        gracefully to Phase 2 behaviour.
        """
        try:
            rendered = self._prompt_service.render_prompt(
                "TRANSCRIPTION-001",
                country=ctx.country_key,
            )

            image_b64 = base64.b64encode(ctx.image_bytes).decode()

            response = await self._ai_client.generate(
                prompt_id="TRANSCRIPTION-001",
                system=rendered.system_prompt,
                messages=[
                    {"role": "user", "content": "Transcribe this student exercise book page."}
                ],
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

            if response and response.json_parsed:
                ctx.transcription_result = response.json_parsed

                parts: list[str] = []
                for q in ctx.transcription_result.get("questions", []):
                    text = q.get("question_text", "").strip()
                    work = q.get("student_work", "").strip()
                    if text:
                        parts.append(text)
                    if work:
                        parts.append(work)
                ctx.transcription_text = " ".join(parts)

            if response:
                await self._log_ai_cost(ctx, response, prompt_id="TRANSCRIPTION-001")

            logger.info(
                "transcription_complete",
                student_id=ctx.student_id,
                success=bool(ctx.transcription_result),
                transcription_text_length=len(ctx.transcription_text),
            )
        except Exception as exc:
            logger.warning(
                "transcription_failed",
                student_id=ctx.student_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            ctx.transcription_result = {}
            ctx.transcription_text = ""

    # ------------------------------------------------------------------
    # Step 4 — Build curriculum graph
    # ------------------------------------------------------------------

    async def _build_curriculum_graph(self, ctx: ImageAnalysisContext) -> None:
        """Hybrid retrieval: vector search + prerequisite walk.

        Pipeline:
        1. _build_query_text → ctx.image_description
        2. EmbeddingService.embed(query_text) → query_vector
        3. _vector_search(query_vector) → indicators → seed_node_ids
        4. _walk_prerequisites(seed_node_ids) → prerequisite_node_ids
        5. Merge seed + prerequisite node IDs (deduplicated)
        6. Load full node data with indicators and error patterns
        7. Serialize to JSON → ctx.curriculum_graph_json
        8. Populate ctx.retrieval_metadata
        9. Log token count

        Falls back to code-ordered SELECT if:
        - self._embedding_service is None
        - Vector search returns zero results
        - Any OperationalError from pgvector
        """
        if self._embedding_service is None:
            await self._fallback_curriculum_graph(ctx, "embedding_service is None")
            return

        # Step 1: Generate query text from image
        query_text = await self._build_query_text(ctx)

        # Step 2: Embed query text
        try:
            query_vector = await self._embedding_service.embed(query_text)
        except Exception as exc:
            logger.warning(
                "embedding_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                student_id=ctx.student_id,
            )
            await self._fallback_curriculum_graph(ctx, f"embed call failed: {exc}")
            return

        # Step 3: Vector search
        indicators = await self._vector_search(query_vector, ctx.country_key, ctx.subject)

        # Check if we fell back (indicators from fallback have no embeddings)
        if not indicators:
            await self._fallback_curriculum_graph(ctx, "vector search returned zero results")
            return

        # Extract seed node IDs
        seed_node_ids: set[UUID] = {ind.node_id for ind in indicators}

        # Step 4: Walk prerequisites
        prerequisite_node_ids = await self._walk_prerequisites(seed_node_ids, ctx.country_key)

        # Step 5: Merge & deduplicate
        all_node_ids = seed_node_ids | prerequisite_node_ids

        # Log warning if combined set exceeds 25 nodes
        if len(all_node_ids) > 25:
            logger.warning(
                "node_count_exceeds_threshold",
                node_count=len(all_node_ids),
                student_id=ctx.student_id,
                threshold=25,
            )

        # Step 6: Load full node data
        node_result = await self._db.execute(
            select(CurriculumNode)
            .where(CurriculumNode.id.in_(all_node_ids))
            .options(
                selectinload(CurriculumNode.indicators).selectinload(
                    CurriculumIndicator.error_patterns
                )
            )
        )
        nodes = node_result.scalars().all()

        # Build code lookups
        seed_node_codes = []
        prerequisite_node_codes = []
        for node in nodes:
            if node.id in seed_node_ids:
                seed_node_codes.append(node.code)
            if node.id in prerequisite_node_ids:
                prerequisite_node_codes.append(node.code)

        # Step 7: Serialize to JSON
        graph = self._serialize_nodes(nodes)
        ctx.curriculum_graph_json = json.dumps(graph, indent=2)

        # Step 8: Populate retrieval metadata
        ctx.retrieval_metadata = {
            "seed_node_ids": [str(nid) for nid in seed_node_ids],
            "prerequisite_node_ids": [str(nid) for nid in prerequisite_node_ids],
            "seed_node_codes": sorted(seed_node_codes),
            "prerequisite_node_codes": sorted(prerequisite_node_codes),
            "total_nodes_injected": len(nodes),
            "query_text_preview": query_text[:100],
        }

        # Step 9: Log token count
        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(ctx.curriculum_graph_json))
        logger.info(
            "curriculum_graph_token_count",
            student_id=ctx.student_id,
            token_count=token_count,
            total_nodes=len(nodes),
            fallback_mode=False,
        )

        logger.info(
            "hybrid_retrieval_complete",
            student_id=ctx.student_id,
            seed_count=len(seed_node_ids),
            prerequisite_count=len(prerequisite_node_ids),
            total_count=len(nodes),
        )

    # ------------------------------------------------------------------
    # Hybrid retrieval helpers
    # ------------------------------------------------------------------

    async def _build_query_text(self, ctx: ImageAnalysisContext) -> str:
        """Generate a text query for vector search.

        Prefers transcription text from Stage 1 when available — this
        skips the Claude Haiku image-description call entirely, saving
        one AI call and its associated cost/latency.

        Falls back to the Phase 2 approach (Haiku image description)
        when transcription_text is empty, and ultimately to
        "{subject} {student_grade}" on failure.
        """
        # ── Prefer Stage 1 transcription text (Requirements 4.1, 4.3) ──
        if ctx.transcription_text:
            logger.info(
                "build_query_text_using_transcription",
                student_id=ctx.student_id,
                transcription_text_length=len(ctx.transcription_text),
            )
            ctx.image_description = ctx.transcription_text
            return ctx.transcription_text

        # ── Fall back to Phase 2 Haiku image description (Requirement 4.2) ──
        logger.info(
            "build_query_text_fallback_to_haiku",
            student_id=ctx.student_id,
            reason="transcription_text is empty",
        )
        prompt = (
            "Describe the mathematical topics and operations visible in this student's "
            "exercise book in 2-3 sentences. Name specific operations (e.g., long division, "
            "fraction addition), number ranges, and any visible error patterns. Do not "
            f"diagnose the student. The student is in grade {ctx.student_grade} in {ctx.country_key}."
        )

        try:
            image_b64 = base64.b64encode(ctx.image_bytes).decode()
            response = await self._ai_client.generate(
                prompt_id="QUERY-TEXT",
                system="You are a math education assistant. Describe what you see concisely.",
                messages=[{"role": "user", "content": prompt}],
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                temperature=0.0,
                json_mode=False,
                images=[
                    ImageContent(
                        data=image_b64,
                        media_type=ctx.media_type,
                        source_type="base64",
                    )
                ],
            )

            if response and response.text and response.text.strip():
                ctx.image_description = response.text.strip()
                return ctx.image_description

        except Exception as exc:
            logger.warning(
                "build_query_text_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                student_id=ctx.student_id,
            )

        # Fallback
        fallback = f"{ctx.subject} {ctx.student_grade}"
        logger.warning(
            "build_query_text_fallback",
            student_id=ctx.student_id,
            fallback_query=fallback,
        )
        ctx.image_description = fallback
        return fallback

    async def _vector_search(
        self,
        query_vector: list[float],
        country: str,
        subject: str,
        top_k: int = 15,
    ) -> list[CurriculumIndicator]:
        """Cosine similarity search against embedded indicators.

        Returns top_k indicators with their CurriculumNode relationships loaded.
        Falls back to code-ordered SELECT on zero results or OperationalError.
        """
        try:
            result = await self._db.execute(
                select(CurriculumIndicator)
                .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
                .where(
                    CurriculumNode.country == country,
                    CurriculumNode.subject == subject,
                    CurriculumIndicator.embedding.isnot(None),
                )
                .order_by(CurriculumIndicator.embedding.cosine_distance(query_vector))
                .limit(top_k)
                .options(selectinload(CurriculumIndicator.node))
            )
            indicators = result.scalars().all()

            if not indicators:
                logger.warning(
                    "vector_search_zero_results",
                    country=country,
                    subject=subject,
                    message="No embeddings found. Has the embedding job been run?",
                )
                return await self._code_ordered_indicators(country, subject)

            return list(indicators)

        except OperationalError as exc:
            logger.error(
                "vector_search_operational_error",
                country=country,
                subject=subject,
                error=str(exc),
            )
            return await self._code_ordered_indicators(country, subject)

    async def _code_ordered_indicators(
        self, country: str, subject: str, limit: int = 20
    ) -> list[CurriculumIndicator]:
        """Code-ordered SELECT of indicators joined to nodes for fallback."""
        result = await self._db.execute(
            select(CurriculumIndicator)
            .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
            .where(
                CurriculumNode.country == country,
                CurriculumNode.subject == subject,
            )
            .order_by(CurriculumNode.code)
            .limit(limit)
            .options(selectinload(CurriculumIndicator.node))
        )
        return list(result.scalars().all())

    async def _walk_prerequisites(
        self,
        seed_node_ids: set[UUID],
        country: str,
        depth: int = 2,
    ) -> set[UUID]:
        """Walk prerequisite graph upward from seed nodes via recursive CTE.

        Returns discovered prerequisite node IDs, excluding the seeds themselves.
        Returns empty set if seed_node_ids is empty (no DB query executed).
        """
        if not seed_node_ids:
            return set()

        seed_list = list(seed_node_ids)
        seed_str_list = [str(sid) for sid in seed_list]

        try:
            cte_sql = text("""
                WITH RECURSIVE prereqs AS (
                    SELECT cp.target_node_id AS node_id, 1 AS depth
                    FROM curriculum_prerequisites cp
                    WHERE cp.source_node_id = ANY(:seed_ids)
                      AND cp.target_node_id != ALL(:seed_ids)

                    UNION

                    SELECT cp.target_node_id AS node_id, p.depth + 1
                    FROM curriculum_prerequisites cp
                    JOIN prereqs p ON cp.source_node_id = p.node_id
                    WHERE p.depth < :max_depth
                      AND cp.target_node_id != ALL(:seed_ids)
                )
                SELECT DISTINCT node_id FROM prereqs
            """)

            result = await self._db.execute(
                cte_sql,
                {"seed_ids": seed_str_list, "max_depth": depth},
            )
            rows = result.fetchall()

            if not rows:
                logger.warning(
                    "walk_prerequisites_no_edges",
                    seed_count=len(seed_node_ids),
                    country=country,
                )
                return set()

            return {UUID(str(row[0])) for row in rows}

        except Exception as exc:
            logger.warning(
                "walk_prerequisites_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                country=country,
            )
            return set()

    async def _fallback_curriculum_graph(self, ctx: ImageAnalysisContext, reason: str) -> None:
        """Pre-Phase-2 fallback: code-ordered SELECT LIMIT 20.

        Sets ctx.retrieval_metadata["fallback_reason"] = reason.
        Output is structurally identical to normal retrieval.
        """
        indicators = await self._code_ordered_indicators(ctx.country_key, ctx.subject)

        # Collect unique nodes from indicators
        nodes_by_id: dict[UUID, CurriculumNode] = {}
        for ind in indicators:
            if ind.node and ind.node.id not in nodes_by_id:
                nodes_by_id[ind.node.id] = ind.node

        # Load full node data with indicators and error patterns
        if nodes_by_id:
            node_result = await self._db.execute(
                select(CurriculumNode)
                .where(CurriculumNode.id.in_(nodes_by_id.keys()))
                .options(
                    selectinload(CurriculumNode.indicators).selectinload(
                        CurriculumIndicator.error_patterns
                    )
                )
            )
            nodes = node_result.scalars().all()
        else:
            nodes = []

        graph = self._serialize_nodes(nodes)
        ctx.curriculum_graph_json = json.dumps(graph, indent=2)

        ctx.retrieval_metadata = {
            "fallback_reason": reason,
            "seed_node_ids": [],
            "prerequisite_node_ids": [],
            "seed_node_codes": [],
            "prerequisite_node_codes": [],
            "total_nodes_injected": len(nodes),
            "query_text_preview": ctx.image_description[:100] if ctx.image_description else "",
        }

        # Log token count
        enc = tiktoken.get_encoding("cl100k_base")
        token_count = len(enc.encode(ctx.curriculum_graph_json))
        logger.info(
            "curriculum_graph_token_count",
            student_id=ctx.student_id,
            token_count=token_count,
            total_nodes=len(nodes),
            fallback_mode=True,
        )

        logger.info(
            "fallback_curriculum_graph",
            student_id=ctx.student_id,
            reason=reason,
            node_count=len(nodes),
        )

    @staticmethod
    def _serialize_nodes(nodes: list[CurriculumNode]) -> list[dict[str, Any]]:
        """Serialize curriculum nodes to the standard JSON format."""
        return [
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

    # ------------------------------------------------------------------
    # Transcript formatting helper
    # ------------------------------------------------------------------

    def _format_transcript_for_prompt(self, transcription_result: dict[str, Any]) -> str:
        """Format a transcription result dict into a human-readable text block.

        Returns an empty string when the result is empty or contains no questions.
        """
        if not transcription_result:
            return ""

        questions = transcription_result.get("questions")
        if not questions:
            return ""

        layout = transcription_result.get("layout", "")
        topic = transcription_result.get("topic_detected", "")
        legibility = transcription_result.get("overall_legibility", "")

        lines: list[str] = []
        if layout:
            lines.append(f"Layout: {layout}")
        if topic:
            lines.append(f"Topic: {topic}")
        if legibility:
            lines.append(f"Legibility: {legibility}")

        lines.append("")
        lines.append("Questions:")

        for q in questions:
            q_num = q.get("question_number", "")
            q_text = q.get("question_text", "")
            student_work = q.get("student_work", "")
            teacher_mark = q.get("teacher_mark", "")
            illegible = q.get("illegible_regions", "")

            label = f"Q{q_num}" if q_num else "Q?"
            q_text_display = f'"{q_text}"' if q_text else '""'
            lines.append(f"  {label}: {q_text_display}")

            work_display = f'"{student_work}"' if student_work else '""'
            lines.append(f"    Student work: {work_display}")

            lines.append(f"    Teacher mark: {teacher_mark or 'none'}")
            lines.append(f"    Illegible regions: {illegible or 'none'}")
            lines.append("")

        return "\n".join(lines).rstrip("\n") + "\n"

    # ------------------------------------------------------------------
    # Step 4 — Render prompt
    # ------------------------------------------------------------------

    async def _render_prompt(self, ctx: ImageAnalysisContext) -> None:
        """Render the ANALYSIS-001 prompt with student + curriculum context."""
        school_name = ctx.student.school.name if ctx.student.school else "Unknown School"

        transcript_section = (
            self._format_transcript_for_prompt(ctx.transcription_result)
            if ctx.transcription_result
            else ""
        )

        ctx.rendered_prompt = self._prompt_service.render_prompt(
            "ANALYSIS-001",
            country=ctx.country_key,
            extra_context={
                "prerequisite_graph_json": ctx.curriculum_graph_json,
                "current_grade": ctx.student_grade,
                "student_name": ctx.student.first_name,
                "school_name": school_name,
                "total_nodes_injected": str(ctx.retrieval_metadata.get("total_nodes_injected", 0)),
                "seed_node_codes": ", ".join(ctx.retrieval_metadata.get("seed_node_codes", [])),
                "prerequisite_node_codes": ", ".join(
                    ctx.retrieval_metadata.get("prerequisite_node_codes", [])
                ),
                "query_text_preview": ctx.retrieval_metadata.get("query_text_preview", ""),
                "transcript_section": transcript_section,
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

    async def _log_ai_cost(
        self,
        ctx: ImageAnalysisContext,
        response: Any,
        prompt_id: str | None = None,
    ) -> None:
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
                prompt_id=prompt_id or response.prompt_id,
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
        from gapsense.engagement.remediation_engine import RemediationEngine
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

        notification_service: Any
        if is_demo:
            notification_service = DemoNotificationService()
            logger.info("using_demo_notification_service", teacher_phone=ctx.teacher_phone)
        else:
            whatsapp_client = WhatsAppClient.from_settings()
            notification_service = WhatsAppNotificationService(whatsapp_client=whatsapp_client)
            logger.info("using_whatsapp_notification_service", teacher_phone=ctx.teacher_phone)

        # Instantiate RemediationEngine for generating teacher-facing practice questions
        remediation_engine = RemediationEngine(
            ai_client=self._ai_client,
            prompt_service=self._prompt_service,
            guard_service=self._guard_service,
        )

        scanner = ExerciseBookScanner(
            db=self._db,
            media_service=self._media_service,
            worker_service=self._worker_service,
            guard_service=self._guard_service,
            ai_client=self._ai_client,
            prompt_service=self._prompt_service,
            notification_service=notification_service,
            remediation_engine=remediation_engine,
        )
        await scanner.process_analysis_result(
            student_id=ctx.student_id,
            teacher_phone=ctx.teacher_phone,
            analysis=response.json_parsed,
            country=ctx.country_code,
            language=ctx.language,
        )
        logger.info("analysis_dispatched", student_id=ctx.student_id)
