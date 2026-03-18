"""
Phase 3 Integration & Edge-Case Unit Tests.

Tests cover:
- 11.1 TRANSCRIPTION-001 prompt registration (Requirements 1.1, 1.4)
- 11.2 ImageAnalysisContext defaults (Requirements 3.1, 3.2)
- 11.3 Pipeline step order (Requirements 6.1, 6.2, 6.3)
- 11.4 Transcript section in rendered prompt (Requirements 5.1, 5.5)
- 11.5 Dual cost logging (Requirements 7.1, 7.2, 7.4, 7.5)
- 11.6 Edge cases (Requirements 2.4, 4.2, 5.6)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from gapsense.ai.async_client import AIResponse
from gapsense.ai.prompt_service import RenderedPrompt
from gapsense.services.image_analysis_context import ImageAnalysisContext
from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

STUDENT_ID = "123e4567-e89b-12d3-a456-426614174000"
TEACHER_ID = "223e4567-e89b-12d3-a456-426614174000"
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 100


def _make_mock_student():
    student = Mock()
    student.id = UUID(STUDENT_ID)
    student.first_name = "Joshua"
    student.current_grade = "JHS1"
    student.teacher_id = UUID(TEACHER_ID)
    student.teacher = Mock()
    student.teacher.subject = "mathematics"
    student.school = Mock()
    student.school.name = "Test School"
    student.school.district = Mock()
    student.school.district.region = Mock()
    student.school.district.region.country_code = "GH"
    return student


def _make_transcription_rendered():
    return RenderedPrompt(
        prompt_id="TRANSCRIPTION-001",
        system_prompt="Transcribe this student exercise book page.",
        user_template=None,
        model="claude-sonnet-4-6",
        temperature=0.1,
        max_tokens=2048,
        country="GH",
        language="en",
    )


def _make_analysis_rendered():
    return RenderedPrompt(
        prompt_id="ANALYSIS-001",
        system_prompt="You are an education AI.",
        user_template="Analyze: {{prerequisite_graph_json}} {{transcript_section}}",
        model="claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_tokens=4096,
        country="GH",
        language="en",
    )


def _make_transcription_response():
    return AIResponse(
        provider="anthropic",
        model="claude-sonnet-4-6",
        prompt_id="TRANSCRIPTION-001",
        input_tokens=800,
        output_tokens=400,
        latency_ms=1500.0,
        text="Transcription complete",
        json_parsed={
            "layout": "portrait, single column",
            "subject_detected": "mathematics",
            "grade_detected": "JHS1",
            "topic_detected": "fractions",
            "teacher_marks_present": True,
            "questions": [
                {
                    "question_number": "1",
                    "question_text": "Add 1/3 + 1/4",
                    "student_work": "1/3 + 1/4 = 2/7",
                    "teacher_mark": "✗",
                    "teacher_score": "",
                    "has_diagram": False,
                    "illegible_regions": "",
                }
            ],
            "overall_legibility": "legible",
            "handwriting_styles_detected": "print",
            "ocr_notes": "",
        },
    )


def _make_analysis_response():
    return AIResponse(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        prompt_id="ANALYSIS-001",
        input_tokens=1000,
        output_tokens=500,
        latency_ms=2000.0,
        text="Analysis complete",
        json_parsed={
            "gap_node_ids": [],
            "confidence": 0.95,
        },
    )


def _make_ctx(**overrides):
    defaults = {
        "s3_key": "test/image.jpg",
        "student_id": STUDENT_ID,
        "country_code": "GH",
        "language": "en",
        "teacher_phone": "+233501234567",
    }
    defaults.update(overrides)
    return ImageAnalysisContext(**defaults)


def _make_orchestrator(**overrides):
    defaults = {
        "db": AsyncMock(),
        "ai_client": AsyncMock(),
        "media_service": AsyncMock(),
        "guard_service": Mock(),
        "prompt_service": Mock(),
        "worker_service": Mock(),
        "embedding_service": None,
    }
    defaults.update(overrides)
    return ImageAnalysisOrchestrator(**defaults)


# ===========================================================================
# 11.1 — TRANSCRIPTION-001 prompt registration
# Validates: Requirements 1.1, 1.4
# ===========================================================================


class TestTranscription001PromptRegistration:
    """Verify TRANSCRIPTION-001 is registered and has correct parameters."""

    def test_render_transcription_001_without_error(self):
        """PromptService can render TRANSCRIPTION-001 without error.

        Validates: Requirements 1.1
        """
        mock_prompt_service = Mock()
        mock_prompt_service.render_prompt.return_value = _make_transcription_rendered()

        result = mock_prompt_service.render_prompt("TRANSCRIPTION-001", country="GH")

        assert result.prompt_id == "TRANSCRIPTION-001"
        mock_prompt_service.render_prompt.assert_called_once_with("TRANSCRIPTION-001", country="GH")

    def test_rendered_prompt_has_correct_model_params(self):
        """Rendered TRANSCRIPTION-001 has model=claude-sonnet-4-6, temperature=0.1, max_tokens=2048.

        Validates: Requirements 1.4
        """
        mock_prompt_service = Mock()
        mock_prompt_service.render_prompt.return_value = _make_transcription_rendered()

        result = mock_prompt_service.render_prompt("TRANSCRIPTION-001", country="GH")

        assert result.model == "claude-sonnet-4-6"
        assert result.temperature == 0.1
        assert result.max_tokens == 2048


# ===========================================================================
# 11.2 — ImageAnalysisContext defaults
# Validates: Requirements 3.1, 3.2
# ===========================================================================


class TestImageAnalysisContextDefaults:
    """Verify transcription fields default correctly on a fresh context."""

    def test_transcription_text_defaults_to_empty_string(self):
        """Fresh context has transcription_text == ''.

        Validates: Requirements 3.1
        """
        ctx = _make_ctx()
        assert ctx.transcription_text == ""

    def test_transcription_result_defaults_to_empty_dict(self):
        """Fresh context has transcription_result == {}.

        Validates: Requirements 3.2
        """
        ctx = _make_ctx()
        assert ctx.transcription_result == {}

    def test_defaults_are_independent_across_instances(self):
        """Mutating one context's transcription_result doesn't affect another."""
        ctx1 = _make_ctx()
        ctx2 = _make_ctx()
        ctx1.transcription_result["key"] = "value"
        assert ctx2.transcription_result == {}


# ===========================================================================
# 11.3 — Pipeline step order
# Validates: Requirements 6.1, 6.2, 6.3
# ===========================================================================


class TestPipelineStepOrder:
    """Verify run() executes steps in the correct 7-step order."""

    @pytest.mark.asyncio
    async def test_step_order_is_correct(self):
        """Steps execute in order: load_student_context, fetch_image,
        transcribe_image, build_curriculum_graph, render_prompt, call_ai,
        dispatch_results.

        Validates: Requirements 6.1, 6.2, 6.3
        """
        call_order: list[str] = []

        orchestrator = _make_orchestrator()

        async def _track(name):
            async def _step(ctx):
                call_order.append(name)

            return _step

        # Patch all pipeline steps to record call order
        with (
            patch.object(
                orchestrator,
                "_load_student_context",
                side_effect=lambda _ctx: call_order.append("load_student_context"),
            ),
            patch.object(
                orchestrator,
                "_fetch_image",
                side_effect=lambda _ctx: call_order.append("fetch_image"),
            ),
            patch.object(
                orchestrator,
                "_transcribe_image",
                side_effect=lambda _ctx: call_order.append("transcribe_image"),
            ),
            patch.object(
                orchestrator,
                "_build_curriculum_graph",
                side_effect=lambda _ctx: call_order.append("build_curriculum_graph"),
            ),
            patch.object(
                orchestrator,
                "_render_prompt",
                side_effect=lambda _ctx: call_order.append("render_prompt"),
            ),
            patch.object(
                orchestrator,
                "_call_ai",
                side_effect=lambda _ctx: call_order.append("call_ai"),
            ),
            patch.object(
                orchestrator,
                "_dispatch_results",
                side_effect=lambda _ctx: call_order.append("dispatch_results"),
            ),
        ):
            payload = {
                "s3_key": "test/image.jpg",
                "student_id": STUDENT_ID,
                "country": "GH",
                "language": "en",
                "teacher_phone": "+233501234567",
            }
            await orchestrator.run(payload)

        assert call_order == [
            "load_student_context",
            "fetch_image",
            "transcribe_image",
            "build_curriculum_graph",
            "render_prompt",
            "call_ai",
            "dispatch_results",
        ]

    @pytest.mark.asyncio
    async def test_transcribe_before_build_curriculum(self):
        """transcribe_image completes before build_curriculum_graph starts.

        Validates: Requirements 6.2
        """
        timestamps: list[tuple[str, str]] = []

        orchestrator = _make_orchestrator()

        with (
            patch.object(
                orchestrator,
                "_load_student_context",
                side_effect=lambda _ctx: None,
            ),
            patch.object(
                orchestrator,
                "_fetch_image",
                side_effect=lambda _ctx: None,
            ),
            patch.object(
                orchestrator,
                "_transcribe_image",
                side_effect=lambda _ctx: timestamps.append(("transcribe_image", "done")),
            ),
            patch.object(
                orchestrator,
                "_build_curriculum_graph",
                side_effect=lambda _ctx: timestamps.append(("build_curriculum_graph", "done")),
            ),
            patch.object(orchestrator, "_render_prompt", side_effect=lambda _ctx: None),
            patch.object(orchestrator, "_call_ai", side_effect=lambda _ctx: None),
            patch.object(orchestrator, "_dispatch_results", side_effect=lambda _ctx: None),
        ):
            await orchestrator.run(
                {
                    "s3_key": "test/image.jpg",
                    "student_id": STUDENT_ID,
                    "country": "GH",
                    "language": "en",
                    "teacher_phone": "+233501234567",
                }
            )

        assert timestamps[0][0] == "transcribe_image"
        assert timestamps[1][0] == "build_curriculum_graph"


# ===========================================================================
# 11.4 — Transcript section in rendered prompt
# Validates: Requirements 5.1, 5.5
# ===========================================================================


class TestTranscriptSectionInRenderedPrompt:
    """Verify ANALYSIS-001 prompt includes/excludes transcript section."""

    @pytest.mark.asyncio
    async def test_nonempty_transcription_includes_stage1_section(self):
        """With non-empty transcription_result, rendered ANALYSIS-001 prompt
        contains 'STAGE 1 TRANSCRIPTION'.

        Validates: Requirements 5.1
        """
        mock_prompt_service = Mock()

        # Capture the extra_context passed to render_prompt
        captured_extra_context = {}

        def _capture_render(prompt_id, *, country, extra_context=None):
            if prompt_id == "ANALYSIS-001" and extra_context:
                captured_extra_context.update(extra_context)
            return _make_analysis_rendered()

        mock_prompt_service.render_prompt.side_effect = _capture_render

        orchestrator = _make_orchestrator(prompt_service=mock_prompt_service)

        ctx = _make_ctx()
        ctx.student = _make_mock_student()
        ctx.student_grade = "JHS1"
        ctx.country_key = "GH"
        ctx.curriculum_graph_json = '{"nodes": []}'
        ctx.retrieval_metadata = {"total_nodes_injected": 0}
        ctx.transcription_result = {
            "layout": "portrait",
            "topic_detected": "fractions",
            "overall_legibility": "legible",
            "questions": [
                {
                    "question_number": "1",
                    "question_text": "Add 1/3 + 1/4",
                    "student_work": "2/7",
                    "teacher_mark": "",
                    "illegible_regions": "",
                }
            ],
        }

        await orchestrator._render_prompt(ctx)

        # The transcript_section should be non-empty
        assert captured_extra_context.get("transcript_section") != ""
        assert "Layout: portrait" in captured_extra_context["transcript_section"]

    @pytest.mark.asyncio
    async def test_empty_transcription_excludes_stage1_section(self):
        """With empty transcription_result, rendered ANALYSIS-001 prompt
        does not contain 'STAGE 1 TRANSCRIPTION'.

        Validates: Requirements 5.5
        """
        mock_prompt_service = Mock()

        captured_extra_context = {}

        def _capture_render(prompt_id, *, country, extra_context=None):
            if prompt_id == "ANALYSIS-001" and extra_context:
                captured_extra_context.update(extra_context)
            return _make_analysis_rendered()

        mock_prompt_service.render_prompt.side_effect = _capture_render

        orchestrator = _make_orchestrator(prompt_service=mock_prompt_service)

        ctx = _make_ctx()
        ctx.student = _make_mock_student()
        ctx.student_grade = "JHS1"
        ctx.country_key = "GH"
        ctx.curriculum_graph_json = '{"nodes": []}'
        ctx.retrieval_metadata = {"total_nodes_injected": 0}
        ctx.transcription_result = {}  # Empty

        await orchestrator._render_prompt(ctx)

        assert captured_extra_context.get("transcript_section") == ""


# ===========================================================================
# 11.5 — Dual cost logging
# Validates: Requirements 7.1, 7.2, 7.4, 7.5
# ===========================================================================


class TestDualCostLogging:
    """Verify two AIUsageLog records are created with distinct prompt_ids."""

    @pytest.mark.asyncio
    async def test_two_usage_logs_created_with_correct_prompt_ids(self):
        """Full pipeline with mocked AI creates two AIUsageLog records:
        one for TRANSCRIPTION-001 and one for ANALYSIS-001.

        Validates: Requirements 7.1, 7.2, 7.4, 7.5
        """
        mock_db = AsyncMock()
        mock_ai_client = AsyncMock()
        mock_media_service = AsyncMock()
        mock_prompt_service = Mock()

        # Step 1: Student lookup
        mock_student = _make_mock_student()
        mock_student_result = Mock()
        mock_student_result.scalar_one_or_none.return_value = mock_student

        # Step 4: Curriculum nodes (fallback path)
        mock_node = Mock()
        mock_node.id = UUID("323e4567-e89b-12d3-a456-426614174000")
        mock_node.code = "B7.1.1"
        mock_node.title = "Number Operations"
        mock_node.description = "Desc"
        mock_indicator = Mock()
        mock_indicator.node = mock_node
        mock_indicator.node_id = mock_node.id
        mock_indicator.indicator_code = "B7.1.1.1"
        mock_indicator.title = "Indicator"
        mock_indicator.error_patterns = []
        mock_node.indicators = [mock_indicator]

        mock_indicator_result = Mock()
        mock_indicator_result.scalars.return_value.all.return_value = [mock_indicator]
        mock_node_result = Mock()
        mock_node_result.scalars.return_value.all.return_value = [mock_node]

        mock_db.execute.side_effect = [
            mock_student_result,
            mock_indicator_result,
            mock_node_result,
        ]

        # Step 2: Image fetch
        mock_media_service.download.return_value = JPEG_BYTES

        # Prompt renders: TRANSCRIPTION-001 then ANALYSIS-001
        mock_prompt_service.render_prompt.side_effect = [
            _make_transcription_rendered(),
            _make_analysis_rendered(),
        ]

        # AI calls: transcription then analysis
        mock_ai_client.generate.side_effect = [
            _make_transcription_response(),
            _make_analysis_response(),
        ]

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            media_service=mock_media_service,
            guard_service=Mock(),
            prompt_service=mock_prompt_service,
            worker_service=Mock(),
            embedding_service=None,
        )

        payload = {
            "s3_key": "test/image.jpg",
            "student_id": STUDENT_ID,
            "country": "GH",
            "language": "en",
            "teacher_phone": "+233501234567",
        }

        with patch(
            "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner"
        ) as mock_scanner_class:
            mock_scanner = AsyncMock()
            mock_scanner_class.return_value = mock_scanner
            await orchestrator.run(payload)

        # Collect all AIUsageLog objects added to the DB
        added_objects = [c.args[0] for c in mock_db.add.call_args_list]

        # Filter to AIUsageLog instances (by checking prompt_id attribute)
        usage_logs = [obj for obj in added_objects if hasattr(obj, "prompt_id")]

        prompt_ids = [log.prompt_id for log in usage_logs]
        assert (
            "TRANSCRIPTION-001" in prompt_ids
        ), f"Expected TRANSCRIPTION-001 in prompt_ids, got {prompt_ids}"
        assert (
            "ANALYSIS-001" in prompt_ids
        ), f"Expected ANALYSIS-001 in prompt_ids, got {prompt_ids}"
        assert len(usage_logs) == 2


# ===========================================================================
# 11.6 — Edge cases
# Validates: Requirements 2.4, 4.2, 5.6
# ===========================================================================


class TestEdgeCases:
    """Edge-case tests for the two-stage pipeline."""

    @pytest.mark.asyncio
    async def test_empty_questions_produces_empty_transcription_text(self):
        """Empty questions list produces transcription_text == ''.

        Validates: Requirements 2.4
        """
        mock_ai_client = AsyncMock()
        mock_prompt_service = Mock()
        mock_prompt_service.render_prompt.return_value = _make_transcription_rendered()

        # AI returns valid JSON but with empty questions list
        mock_ai_client.generate.return_value = AIResponse(
            provider="anthropic",
            model="claude-sonnet-4-6",
            prompt_id="TRANSCRIPTION-001",
            input_tokens=800,
            output_tokens=200,
            latency_ms=1000.0,
            text="{}",
            json_parsed={
                "layout": "portrait",
                "subject_detected": "mathematics",
                "grade_detected": "JHS1",
                "topic_detected": "unknown",
                "teacher_marks_present": False,
                "questions": [],
                "overall_legibility": "legible",
                "handwriting_styles_detected": "print",
                "ocr_notes": "",
            },
        )

        mock_db = AsyncMock()
        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            media_service=AsyncMock(),
            guard_service=Mock(),
            prompt_service=mock_prompt_service,
            worker_service=Mock(),
        )

        ctx = _make_ctx()
        ctx.student = _make_mock_student()
        ctx.country_key = "GH"
        ctx.image_bytes = JPEG_BYTES
        ctx.media_type = "image/jpeg"

        await orchestrator._transcribe_image(ctx)

        assert ctx.transcription_text == ""

    @pytest.mark.asyncio
    async def test_fallback_to_haiku_on_empty_transcription(self):
        """When transcription_text is empty, _build_query_text invokes the
        Haiku image description path.

        Validates: Requirements 4.2
        """
        mock_ai_client = AsyncMock()
        # Haiku description response
        mock_ai_client.generate.return_value = AIResponse(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            prompt_id="QUERY-TEXT",
            input_tokens=100,
            output_tokens=50,
            latency_ms=500.0,
            text="Student is working on fraction addition.",
            json_parsed=None,
        )

        orchestrator = _make_orchestrator(ai_client=mock_ai_client)

        ctx = _make_ctx()
        ctx.student = _make_mock_student()
        ctx.country_key = "GH"
        ctx.subject = "mathematics"
        ctx.student_grade = "JHS1"
        ctx.image_bytes = JPEG_BYTES
        ctx.media_type = "image/jpeg"
        ctx.transcription_text = ""  # Empty — should trigger Haiku fallback

        result = await orchestrator._build_query_text(ctx)

        # Haiku was called
        mock_ai_client.generate.assert_awaited_once()
        call_kwargs = mock_ai_client.generate.call_args
        assert call_kwargs.kwargs.get("model") == "claude-haiku-4-5-20251001" or (
            call_kwargs.args and "haiku" in str(call_kwargs)
        )
        assert result == "Student is working on fraction addition."

    @pytest.mark.asyncio
    async def test_image_attached_to_stage2_alongside_transcript(self):
        """Image is still attached to Stage 2 call alongside
        transcript-enhanced prompt.

        Validates: Requirements 5.6
        """
        mock_ai_client = AsyncMock()
        mock_ai_client.generate.return_value = _make_analysis_response()

        orchestrator = _make_orchestrator(ai_client=mock_ai_client)

        ctx = _make_ctx()
        ctx.student = _make_mock_student()
        ctx.image_bytes = JPEG_BYTES
        ctx.media_type = "image/jpeg"
        ctx.rendered_prompt = _make_analysis_rendered()
        # Simulate non-empty transcription
        ctx.transcription_result = {"questions": [{"question_text": "Q1"}]}
        ctx.transcription_text = "Q1"

        await orchestrator._call_ai(ctx)

        # Verify AI was called with images parameter
        mock_ai_client.generate.assert_awaited_once()
        call_kwargs = mock_ai_client.generate.call_args.kwargs

        assert "images" in call_kwargs, "Image must be attached to Stage 2 call"
        assert len(call_kwargs["images"]) == 1
        assert call_kwargs["images"][0].media_type == "image/jpeg"
        assert call_kwargs["prompt_id"] == "ANALYSIS-001"
