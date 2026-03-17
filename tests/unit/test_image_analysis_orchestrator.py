"""
Unit tests for ImageAnalysisOrchestrator.

Tests the 7-step image analysis pipeline:
1. load_student_context
2. fetch_image
3. transcribe_image
4. build_curriculum_graph
5. render_prompt
6. call_ai
7. dispatch_results
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from gapsense.ai.async_client import AIResponse
from gapsense.ai.prompt_service import RenderedPrompt
from gapsense.services.image_analysis_context import ImageAnalysisContext
from gapsense.services.image_analysis_orchestrator import (
    ImageAnalysisOrchestrator,
    _detect_media_type,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_student(
    student_id: str = "123e4567-e89b-12d3-a456-426614174000",
    first_name: str = "Joshua",
    current_grade: str = "JHS1",
):
    """Create a mock Student object."""
    student = Mock()
    student.id = UUID(student_id)
    student.first_name = first_name
    student.current_grade = current_grade
    student.teacher_id = UUID("223e4567-e89b-12d3-a456-426614174000")
    student.teacher = Mock()
    student.teacher.subject = "mathematics"
    student.school = Mock()
    student.school.name = "Test School"
    student.school.district = Mock()
    student.school.district.region = Mock()
    student.school.district.region.country_code = "GH"
    return student


def _make_mock_curriculum_node(node_id: str, code: str, title: str):
    """Create a mock CurriculumNode with indicators."""
    node = Mock()
    node.id = UUID(node_id)
    node.code = code
    node.title = title
    node.description = f"Description for {code}"

    # Add indicators
    indicator = Mock()
    indicator.indicator_code = f"{code}.1"
    indicator.title = f"Indicator for {code}"

    # Add error patterns
    error_pattern = Mock()
    error_pattern.error_description = "Common error"
    error_pattern.severity = "medium"
    indicator.error_patterns = [error_pattern]

    node.indicators = [indicator]
    return node


def _make_rendered_prompt():
    """Create a mock RenderedPrompt for ANALYSIS-001."""
    return RenderedPrompt(
        prompt_id="ANALYSIS-001",
        system_prompt="You are an education AI.",
        user_template="Analyze this image: {{prerequisite_graph_json}}",
        model="claude-sonnet-4-5-20250929",
        temperature=0.3,
        max_tokens=4096,
        country="GH",
        language="en",
    )


def _make_transcription_rendered_prompt():
    """Create a mock RenderedPrompt for TRANSCRIPTION-001."""
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


def _make_ai_response(gap_node_ids: list[str] | None = None):
    """Create a mock AIResponse for ANALYSIS-001."""
    return AIResponse(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        prompt_id="ANALYSIS-001",
        input_tokens=1000,
        output_tokens=500,
        latency_ms=2000.0,
        text="Analysis complete",
        json_parsed={
            "gap_node_ids": gap_node_ids or [],
            "confidence": 0.95,
        },
    )


def _make_transcription_ai_response():
    """Create a mock AIResponse for TRANSCRIPTION-001."""
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


# ---------------------------------------------------------------------------
# Tests for _detect_media_type
# ---------------------------------------------------------------------------


class TestDetectMediaType:
    """Test MIME type detection from magic bytes."""

    def test_detects_png(self):
        """PNG files are correctly identified."""
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"..." * 100
        assert _detect_media_type(png_bytes) == "image/png"

    def test_detects_gif87a(self):
        """GIF87a files are correctly identified."""
        gif_bytes = b"GIF87a" + b"..." * 100
        assert _detect_media_type(gif_bytes) == "image/gif"

    def test_detects_gif89a(self):
        """GIF89a files are correctly identified."""
        gif_bytes = b"GIF89a" + b"..." * 100
        assert _detect_media_type(gif_bytes) == "image/gif"

    def test_detects_webp(self):
        """WebP files are correctly identified."""
        webp_bytes = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"..." * 100
        assert _detect_media_type(webp_bytes) == "image/webp"

    def test_detects_jpeg(self):
        """JPEG files are correctly identified."""
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"..." * 100
        assert _detect_media_type(jpeg_bytes) == "image/jpeg"

    def test_defaults_to_jpeg_for_unknown(self):
        """Unknown formats default to JPEG."""
        unknown_bytes = b"\x00\x00\x00\x00" + b"..." * 100
        assert _detect_media_type(unknown_bytes) == "image/jpeg"


# ---------------------------------------------------------------------------
# Tests for ImageAnalysisOrchestrator
# ---------------------------------------------------------------------------


class TestImageAnalysisOrchestratorStep1:
    """Test Step 1: load_student_context."""

    @pytest.mark.asyncio
    async def test_loads_student_and_context(self):
        """Step 1 loads student and populates country/subject/grade."""
        # Arrange
        mock_db = AsyncMock()
        mock_student = _make_mock_student()

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_student
        mock_db.execute.return_value = mock_result

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Act
        await orchestrator._load_student_context(ctx)

        # Assert
        assert ctx.student == mock_student
        assert ctx.student_grade == "JHS1"
        assert ctx.country_key == "GH"
        assert ctx.subject == "mathematics"

    @pytest.mark.asyncio
    async def test_raises_when_student_not_found(self):
        """Step 1 raises ValueError if student doesn't exist."""
        # Arrange
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Act & Assert
        with pytest.raises(ValueError, match="Student .* not found"):
            await orchestrator._load_student_context(ctx)


class TestImageAnalysisOrchestratorStep2:
    """Test Step 2: fetch_image."""

    @pytest.mark.asyncio
    async def test_fetches_image_and_detects_type(self):
        """Step 2 downloads image bytes and detects MIME type."""
        # Arrange
        png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_media_service = AsyncMock()
        mock_media_service.download.return_value = png_bytes

        orchestrator = ImageAnalysisOrchestrator(
            db=Mock(),
            ai_client=Mock(),
            media_service=mock_media_service,
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.png",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Act
        await orchestrator._fetch_image(ctx)

        # Assert
        assert ctx.image_bytes == png_bytes
        assert ctx.media_type == "image/png"
        mock_media_service.download.assert_awaited_once_with("test/image.png")


class TestImageAnalysisOrchestratorStep3:
    """Test Step 3: build_curriculum_graph."""

    @pytest.mark.asyncio
    async def test_builds_curriculum_graph_json(self):
        """Step 3 queries curriculum nodes and serializes to JSON."""
        # Arrange
        mock_db = AsyncMock()
        node1 = _make_mock_curriculum_node(
            "323e4567-e89b-12d3-a456-426614174000", "B7.1.1", "Number Operations"
        )
        node2 = _make_mock_curriculum_node(
            "423e4567-e89b-12d3-a456-426614174000", "B7.2.1", "Algebra Basics"
        )

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [node1, node2]
        mock_db.execute.return_value = mock_result

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.country_key = "GH"
        ctx.subject = "mathematics"

        # Act
        await orchestrator._build_curriculum_graph(ctx)

        # Assert
        assert ctx.curriculum_graph_json != ""
        assert "B7.1.1" in ctx.curriculum_graph_json
        assert "B7.2.1" in ctx.curriculum_graph_json
        assert "Number Operations" in ctx.curriculum_graph_json
        assert "Algebra Basics" in ctx.curriculum_graph_json

    @pytest.mark.asyncio
    async def test_fallback_when_no_embedding_service(self):
        """Step 3 falls back to code-ordered SELECT when embedding_service is None."""
        # Arrange
        mock_db = AsyncMock()
        nodes = [
            _make_mock_curriculum_node(
                f"323e4567-e89b-12d3-a456-42661417{i:04d}", f"B7.{i}.1", f"Topic {i}"
            )
            for i in range(5)
        ]

        # _code_ordered_indicators returns indicators with .node loaded
        mock_indicator_result = Mock()
        mock_indicators = []
        for node in nodes:
            ind = Mock()
            ind.node = node
            ind.node_id = node.id
            mock_indicators.append(ind)
        mock_indicator_result.scalars.return_value.all.return_value = mock_indicators

        # Full node load
        mock_node_result = Mock()
        mock_node_result.scalars.return_value.all.return_value = nodes

        mock_db.execute.side_effect = [mock_indicator_result, mock_node_result]

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
            embedding_service=None,  # No embedding service → fallback
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.country_key = "GH"
        ctx.subject = "mathematics"

        # Act
        await orchestrator._build_curriculum_graph(ctx)

        # Assert - fallback was used
        assert ctx.retrieval_metadata.get("fallback_reason") == "embedding_service is None"
        assert ctx.curriculum_graph_json != ""


class TestImageAnalysisOrchestratorStep4:
    """Test Step 4: render_prompt."""

    @pytest.mark.asyncio
    async def test_renders_prompt_with_context(self):
        """Step 4 renders ANALYSIS-001 prompt with curriculum graph."""
        # Arrange
        mock_prompt_service = Mock()
        rendered = _make_rendered_prompt()
        mock_prompt_service.render_prompt.return_value = rendered

        mock_student = _make_mock_student(first_name="Joshua")

        orchestrator = ImageAnalysisOrchestrator(
            db=Mock(),
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=mock_prompt_service,
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.student = mock_student
        ctx.student_grade = "JHS1"
        ctx.country_key = "GH"
        ctx.curriculum_graph_json = '{"nodes": []}'

        # Act
        await orchestrator._render_prompt(ctx)

        # Assert
        assert ctx.rendered_prompt == rendered
        mock_prompt_service.render_prompt.assert_called_once_with(
            "ANALYSIS-001",
            country="GH",
            extra_context={
                "prerequisite_graph_json": '{"nodes": []}',
                "current_grade": "JHS1",
                "student_name": "Joshua",
                "school_name": "Test School",
                "total_nodes_injected": "0",
                "seed_node_codes": "",
                "prerequisite_node_codes": "",
                "query_text_preview": "",
                "transcript_section": "",
            },
        )


class TestImageAnalysisOrchestratorStep5:
    """Test Step 5: call_ai."""

    @pytest.mark.asyncio
    async def test_calls_ai_and_logs_cost(self):
        """Step 5 sends image to AI and logs usage."""
        # Arrange
        mock_ai_client = AsyncMock()
        ai_response = _make_ai_response(gap_node_ids=["B7.1.1"])
        mock_ai_client.generate.return_value = ai_response

        mock_db = AsyncMock()
        rendered = _make_rendered_prompt()

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.student = _make_mock_student()
        ctx.image_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        ctx.media_type = "image/jpeg"
        ctx.rendered_prompt = rendered

        # Act
        await orchestrator._call_ai(ctx)

        # Assert
        assert ctx.ai_response == ai_response
        mock_ai_client.generate.assert_awaited_once()

        # Verify AI cost was logged
        mock_db.add.assert_called_once()
        mock_db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cost_logging_failure_does_not_abort_pipeline(self):
        """Step 5 continues even if cost logging fails."""
        # Arrange
        mock_ai_client = AsyncMock()
        ai_response = _make_ai_response()
        mock_ai_client.generate.return_value = ai_response

        mock_db = AsyncMock()
        mock_db.commit.side_effect = Exception("DB commit failed")

        rendered = _make_rendered_prompt()

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.student = _make_mock_student()
        ctx.image_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        ctx.media_type = "image/jpeg"
        ctx.rendered_prompt = rendered

        # Act (should not raise exception)
        await orchestrator._call_ai(ctx)

        # Assert - AI response is still set
        assert ctx.ai_response == ai_response
        mock_db.rollback.assert_awaited_once()


class TestImageAnalysisOrchestratorStep6:
    """Test Step 6: dispatch_results."""

    @pytest.mark.asyncio
    async def test_dispatches_results_to_scanner(self):
        """Step 6 calls ExerciseBookScanner with AI results."""
        # Arrange
        ai_response = _make_ai_response(gap_node_ids=["B7.1.1", "B7.2.1"])

        orchestrator = ImageAnalysisOrchestrator(
            db=Mock(),
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.ai_response = ai_response

        # Act (mock ExerciseBookScanner)
        with patch(
            "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner"
        ) as mock_scanner_class:
            mock_scanner = AsyncMock()
            mock_scanner_class.return_value = mock_scanner

            await orchestrator._dispatch_results(ctx)

            # Assert
            mock_scanner.process_analysis_result.assert_awaited_once_with(
                student_id="123e4567-e89b-12d3-a456-426614174000",
                teacher_phone="+233501234567",
                analysis={"gap_node_ids": ["B7.1.1", "B7.2.1"], "confidence": 0.95},
                country="GH",
                language="en",
            )

    @pytest.mark.asyncio
    async def test_skips_dispatch_when_no_ai_result(self):
        """Step 6 skips dispatch if AI returned no result."""
        # Arrange
        orchestrator = ImageAnalysisOrchestrator(
            db=Mock(),
            ai_client=Mock(),
            media_service=Mock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
        )

        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )
        ctx.ai_response = None

        # Act (mock ExerciseBookScanner)
        with patch(
            "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner"
        ) as mock_scanner_class:
            mock_scanner = AsyncMock()
            mock_scanner_class.return_value = mock_scanner

            await orchestrator._dispatch_results(ctx)

            # Assert - scanner was never called
            mock_scanner.process_analysis_result.assert_not_awaited()


class TestImageAnalysisOrchestratorFullPipeline:
    """Test the complete run() method."""

    @pytest.mark.asyncio
    async def test_full_pipeline_success(self):
        """Full pipeline executes all 7 steps successfully."""
        # Arrange - mock all dependencies
        mock_db = AsyncMock()
        mock_ai_client = AsyncMock()
        mock_media_service = AsyncMock()
        mock_prompt_service = Mock()

        # Step 1: Student lookup
        mock_student = _make_mock_student()
        mock_student_result = Mock()
        mock_student_result.scalar_one_or_none.return_value = mock_student

        # Step 4: Curriculum nodes (fallback path - 2 DB calls)
        node = _make_mock_curriculum_node(
            "323e4567-e89b-12d3-a456-426614174000", "B7.1.1", "Number Operations"
        )
        # First call: _code_ordered_indicators
        mock_indicator = Mock()
        mock_indicator.node = node
        mock_indicator.node_id = node.id
        mock_indicator_result = Mock()
        mock_indicator_result.scalars.return_value.all.return_value = [mock_indicator]

        # Second call: full node load
        mock_node_result = Mock()
        mock_node_result.scalars.return_value.all.return_value = [node]

        mock_db.execute.side_effect = [mock_student_result, mock_indicator_result, mock_node_result]

        # Step 2: Image fetch
        jpeg_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        mock_media_service.download.return_value = jpeg_bytes

        # Step 3: Transcription + Step 5: Prompt render
        transcription_rendered = _make_transcription_rendered_prompt()
        analysis_rendered = _make_rendered_prompt()
        mock_prompt_service.render_prompt.side_effect = [
            transcription_rendered,  # Step 3: _transcribe_image
            analysis_rendered,  # Step 5: _render_prompt
        ]

        # Step 3: Transcription AI + Step 6: Analysis AI
        transcription_response = _make_transcription_ai_response()
        ai_response = _make_ai_response(gap_node_ids=["B7.1.1"])
        mock_ai_client.generate.side_effect = [
            transcription_response,  # Step 3: _transcribe_image
            ai_response,  # Step 6: _call_ai
        ]

        orchestrator = ImageAnalysisOrchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            media_service=mock_media_service,
            guard_service=Mock(),
            prompt_service=mock_prompt_service,
            worker_service=Mock(),
            embedding_service=None,  # Fallback path
        )

        payload = {
            "s3_key": "test/image.jpg",
            "student_id": "123e4567-e89b-12d3-a456-426614174000",
            "country": "GH",
            "language": "en",
            "teacher_phone": "+233501234567",
        }

        # Act (mock ExerciseBookScanner)
        with patch(
            "gapsense.engagement.exercise_book_scanner.ExerciseBookScanner"
        ) as mock_scanner_class:
            mock_scanner = AsyncMock()
            mock_scanner_class.return_value = mock_scanner

            await orchestrator.run(payload)

            # Assert - all steps executed
            assert mock_db.execute.await_count == 3  # Student + 2 curriculum queries (fallback)
            mock_media_service.download.assert_awaited_once()
            assert (
                mock_prompt_service.render_prompt.call_count == 2
            )  # TRANSCRIPTION-001 + ANALYSIS-001
            assert mock_ai_client.generate.await_count == 2  # Stage 1 + Stage 2
            mock_scanner.process_analysis_result.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests for _format_transcript_for_prompt
# ---------------------------------------------------------------------------


class TestFormatTranscriptForPrompt:
    """Test the _format_transcript_for_prompt helper method."""

    def _make_orchestrator(self):
        """Create an orchestrator with mocked dependencies for unit testing."""
        return ImageAnalysisOrchestrator(
            db=AsyncMock(),
            ai_client=AsyncMock(),
            media_service=AsyncMock(),
            guard_service=Mock(),
            prompt_service=Mock(),
            worker_service=Mock(),
            embedding_service=None,
        )

    def test_empty_dict_returns_empty_string(self):
        orch = self._make_orchestrator()
        assert orch._format_transcript_for_prompt({}) == ""

    def test_none_like_falsy_returns_empty_string(self):
        orch = self._make_orchestrator()
        assert orch._format_transcript_for_prompt({}) == ""

    def test_no_questions_key_returns_empty_string(self):
        orch = self._make_orchestrator()
        result = orch._format_transcript_for_prompt({"layout": "portrait"})
        assert result == ""

    def test_empty_questions_list_returns_empty_string(self):
        orch = self._make_orchestrator()
        result = orch._format_transcript_for_prompt({"questions": []})
        assert result == ""

    def test_basic_formatting(self):
        orch = self._make_orchestrator()
        transcription = {
            "layout": "portrait, single column",
            "topic_detected": "Fractions — addition of unlike fractions",
            "overall_legibility": "mostly_legible",
            "questions": [
                {
                    "question_number": "1",
                    "question_text": "Add 1/3 + 1/4",
                    "student_work": "1/3 + 1/4 = 2/7",
                    "teacher_mark": "✗",
                    "illegible_regions": "",
                },
                {
                    "question_number": "2",
                    "question_text": "Simplify 6/8",
                    "student_work": "6/8 = 3/4",
                    "teacher_mark": "✓",
                    "illegible_regions": "",
                },
            ],
        }
        result = orch._format_transcript_for_prompt(transcription)

        assert "Layout: portrait, single column" in result
        assert "Topic: Fractions — addition of unlike fractions" in result
        assert "Legibility: mostly_legible" in result
        assert 'Q1: "Add 1/3 + 1/4"' in result
        assert 'Student work: "1/3 + 1/4 = 2/7"' in result
        assert "Teacher mark: ✗" in result
        assert 'Q2: "Simplify 6/8"' in result
        assert 'Student work: "6/8 = 3/4"' in result
        assert "Teacher mark: ✓" in result

    def test_missing_header_fields_omitted(self):
        orch = self._make_orchestrator()
        transcription = {
            "questions": [
                {
                    "question_number": "1",
                    "question_text": "What is 2+2?",
                    "student_work": "4",
                    "teacher_mark": "✓",
                    "illegible_regions": "",
                }
            ],
        }
        result = orch._format_transcript_for_prompt(transcription)

        assert "Layout:" not in result
        assert "Topic:" not in result
        assert "Legibility:" not in result
        assert "Questions:" in result
        assert 'Q1: "What is 2+2?"' in result

    def test_illegible_regions_displayed(self):
        orch = self._make_orchestrator()
        transcription = {
            "questions": [
                {
                    "question_number": "3",
                    "question_text": "Solve for x",
                    "student_work": "x = [illegible]",
                    "teacher_mark": "",
                    "illegible_regions": "bottom-right corner smudged",
                }
            ],
        }
        result = orch._format_transcript_for_prompt(transcription)

        assert "Illegible regions: bottom-right corner smudged" in result
        assert "Teacher mark: none" in result

    def test_missing_question_number_shows_placeholder(self):
        orch = self._make_orchestrator()
        transcription = {
            "questions": [
                {
                    "question_text": "Some question",
                    "student_work": "Some answer",
                }
            ],
        }
        result = orch._format_transcript_for_prompt(transcription)

        assert "Q?:" in result
