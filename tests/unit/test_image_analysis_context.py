"""
Unit tests for ImageAnalysisContext.

Tests context initialization, state mutation, and validation.
"""

from __future__ import annotations

from gapsense.services.image_analysis_context import ImageAnalysisContext

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestImageAnalysisContextInitialization:
    """Test context initialization with required and optional fields."""

    def test_minimal_initialization(self):
        """Context can be created with only required fields."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        assert ctx.s3_key == "test/image.jpg"
        assert ctx.student_id == "123e4567-e89b-12d3-a456-426614174000"
        assert ctx.country_code == "GH"
        assert ctx.language == "en"
        assert ctx.teacher_phone == "+233501234567"

    def test_optional_fields_have_defaults(self):
        """Optional fields are initialized with sensible defaults."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Step 1 fields
        assert ctx.student is None
        assert ctx.country_key == ""
        assert ctx.subject == ""
        assert ctx.student_grade == ""

        # Step 2 fields
        assert ctx.image_bytes == b""
        assert ctx.media_type == "image/jpeg"

        # Step 3 fields
        assert ctx.curriculum_graph_json == ""

        # Step 4 fields
        assert ctx.rendered_prompt is None

        # Step 5 fields
        assert ctx.ai_response is None

        # Metadata
        assert ctx.errors == []


class TestImageAnalysisContextValidation:
    """Test the is_valid property."""

    def test_is_valid_when_no_errors(self):
        """Context is valid when errors list is empty."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        assert ctx.is_valid is True
        assert len(ctx.errors) == 0

    def test_is_invalid_when_has_errors(self):
        """Context is invalid when errors list has items."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        ctx.errors.append("Student not found")
        assert ctx.is_valid is False
        assert len(ctx.errors) == 1

    def test_is_invalid_with_multiple_errors(self):
        """Context is invalid when multiple errors exist."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        ctx.errors.append("Student not found")
        ctx.errors.append("S3 key not found")
        assert ctx.is_valid is False
        assert len(ctx.errors) == 2


class TestImageAnalysisContextStateMutation:
    """Test that context fields can be mutated through pipeline steps."""

    def test_step1_load_student_context(self):
        """Step 1 fields can be populated."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Simulate Step 1
        ctx.student = "mock_student_object"
        ctx.country_key = "ghana"
        ctx.subject = "mathematics"
        ctx.student_grade = "JHS1"

        assert ctx.student == "mock_student_object"
        assert ctx.country_key == "ghana"
        assert ctx.subject == "mathematics"
        assert ctx.student_grade == "JHS1"

    def test_step2_fetch_image(self):
        """Step 2 fields can be populated."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Simulate Step 2
        ctx.image_bytes = b"\x89PNG\r\n\x1a\n"
        ctx.media_type = "image/png"

        assert ctx.image_bytes == b"\x89PNG\r\n\x1a\n"
        assert ctx.media_type == "image/png"

    def test_step3_build_curriculum_graph(self):
        """Step 3 fields can be populated."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Simulate Step 3
        ctx.curriculum_graph_json = '{"nodes": []}'

        assert ctx.curriculum_graph_json == '{"nodes": []}'

    def test_step4_render_prompt(self):
        """Step 4 fields can be populated."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Simulate Step 4
        ctx.rendered_prompt = "mock_rendered_prompt"

        assert ctx.rendered_prompt == "mock_rendered_prompt"

    def test_step5_call_ai(self):
        """Step 5 fields can be populated."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Simulate Step 5
        ctx.ai_response = "mock_ai_response"

        assert ctx.ai_response == "mock_ai_response"

    def test_full_pipeline_state_accumulation(self):
        """Context accumulates state through all steps."""
        ctx = ImageAnalysisContext(
            s3_key="test/image.jpg",
            student_id="123e4567-e89b-12d3-a456-426614174000",
            country_code="GH",
            language="en",
            teacher_phone="+233501234567",
        )

        # Simulate all steps populating fields
        ctx.student = "mock_student"
        ctx.country_key = "ghana"
        ctx.subject = "mathematics"
        ctx.student_grade = "JHS1"
        ctx.image_bytes = b"\x89PNG\r\n\x1a\n"
        ctx.media_type = "image/png"
        ctx.curriculum_graph_json = '{"nodes": []}'
        ctx.rendered_prompt = "mock_rendered_prompt"
        ctx.ai_response = "mock_ai_response"

        # All fields should be populated
        assert ctx.student == "mock_student"
        assert ctx.country_key == "ghana"
        assert ctx.subject == "mathematics"
        assert ctx.student_grade == "JHS1"
        assert ctx.image_bytes == b"\x89PNG\r\n\x1a\n"
        assert ctx.media_type == "image/png"
        assert ctx.curriculum_graph_json == '{"nodes": []}'
        assert ctx.rendered_prompt == "mock_rendered_prompt"
        assert ctx.ai_response == "mock_ai_response"
        assert ctx.is_valid is True
