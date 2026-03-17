"""
Unit and property-based tests for EmbeddingService.

Tests construction, error handling, indicator chunk formatting,
and rate-limit retry logic.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.ai.embedding_service import EmbeddingService
from gapsense.core.exceptions import ConfigurationError

# ============================================================================
# Property-Based Tests
# ============================================================================


class TestIndicatorChunkProperty:
    """Property 2: Indicator chunk deterministic format.

    Feature: phase2-hybrid-rag-retrieval, Property 2: Indicator chunk deterministic format
    """

    # **Validates: Requirements 3.5**
    @settings(max_examples=100)
    @given(
        node_code=st.text(min_size=0, max_size=50),
        node_title=st.text(min_size=0, max_size=100),
        indicator_code=st.text(min_size=0, max_size=50),
        indicator_title=st.text(min_size=0, max_size=100),
        error_patterns=st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=10),
    )
    def test_indicator_chunk_matches_template_format(
        self,
        node_code: str,
        node_title: str,
        indicator_code: str,
        indicator_title: str,
        error_patterns: list[str],
    ):
        """For any valid inputs, build_indicator_chunk output matches the template format."""
        result = EmbeddingService.build_indicator_chunk(
            node_code=node_code,
            node_title=node_title,
            indicator_code=indicator_code,
            indicator_title=indicator_title,
            error_patterns=error_patterns,
        )

        # Verify the output starts with the curriculum node line
        expected_line1 = f"Curriculum node: {node_code} \u2014 {node_title}"
        assert result.startswith(
            expected_line1 + "\n"
        ), f"Expected result to start with '{expected_line1}\\n'"

        # Verify the indicator line follows
        expected_line2 = f"Indicator: {indicator_code} \u2014 {indicator_title}"
        assert expected_line2 + "\n" in result, f"Expected result to contain '{expected_line2}\\n'"

        # Verify the common errors line is at the end
        expected_errors = "; ".join(error_patterns) if error_patterns else ""
        expected_line3 = f"Common errors: {expected_errors}"
        assert result.endswith(expected_line3), f"Expected result to end with '{expected_line3}'"

        # Verify the overall structure: line1\nline2\nline3
        expected_full = f"{expected_line1}\n{expected_line2}\n{expected_line3}"
        assert result == expected_full

    # **Validates: Requirements 3.5**
    @settings(max_examples=100)
    @given(
        node_code=st.text(min_size=0, max_size=50),
        node_title=st.text(min_size=0, max_size=100),
        indicator_code=st.text(min_size=0, max_size=50),
        indicator_title=st.text(min_size=0, max_size=100),
        error_patterns=st.lists(st.text(min_size=0, max_size=100), min_size=0, max_size=10),
    )
    def test_indicator_chunk_is_deterministic(
        self,
        node_code: str,
        node_title: str,
        indicator_code: str,
        indicator_title: str,
        error_patterns: list[str],
    ):
        """Calling build_indicator_chunk twice with the same inputs produces identical output."""
        result1 = EmbeddingService.build_indicator_chunk(
            node_code=node_code,
            node_title=node_title,
            indicator_code=indicator_code,
            indicator_title=indicator_title,
            error_patterns=error_patterns,
        )
        result2 = EmbeddingService.build_indicator_chunk(
            node_code=node_code,
            node_title=node_title,
            indicator_code=indicator_code,
            indicator_title=indicator_title,
            error_patterns=error_patterns,
        )
        assert result1 == result2, "build_indicator_chunk is not deterministic"


# ============================================================================
# Unit Tests
# ============================================================================


def _make_settings(embedding_model: str = "openai", openai_api_key: str = "test-key"):
    """Create a mock Settings object for testing."""
    settings = MagicMock()
    settings.EMBEDDING_MODEL = embedding_model
    settings.OPENAI_API_KEY = openai_api_key
    return settings


class TestEmbeddingServiceConstruction:
    """Test EmbeddingService construction and configuration."""

    def test_openai_backend_without_api_key_raises_configuration_error(self):
        """OpenAI backend without API key raises ConfigurationError."""
        settings = _make_settings(embedding_model="openai", openai_api_key="")

        with pytest.raises(ConfigurationError, match="OPENAI_API_KEY is required"):
            EmbeddingService(settings)

    def test_openai_backend_with_api_key_constructs_successfully(self):
        """OpenAI backend with API key constructs without error."""
        settings = _make_settings(embedding_model="openai", openai_api_key="sk-test-key")

        service = EmbeddingService(settings)

        assert service.model_name == "openai-text-embedding-3-small"
        assert service.dimensions == 1536

    def test_minilm_backend_constructs_without_api_key(self):
        """MiniLM backend constructs without API key."""
        settings = _make_settings(embedding_model="minilm", openai_api_key="")

        service = EmbeddingService(settings)

        assert service.model_name == "minilm-all-MiniLM-L6-v2"
        assert service.dimensions == 384

    def test_minilm_backend_with_api_key_constructs_successfully(self):
        """MiniLM backend ignores API key and constructs successfully."""
        settings = _make_settings(embedding_model="minilm", openai_api_key="sk-test-key")

        service = EmbeddingService(settings)

        assert service.model_name == "minilm-all-MiniLM-L6-v2"
        assert service.dimensions == 384

    def test_backend_is_fixed_at_construction(self):
        """Backend is determined at construction time and doesn't change."""
        settings = _make_settings(embedding_model="openai", openai_api_key="sk-test-key")
        service = EmbeddingService(settings)

        assert service._backend == "openai"
        assert service.model_name == "openai-text-embedding-3-small"
        assert service.dimensions == 1536


class TestEmbeddingServiceRateLimitRetry:
    """Test rate-limit retry logic for OpenAI backend."""

    @pytest.mark.asyncio
    async def test_rate_limit_retry_succeeds_after_two_failures(self):
        """Mock 2x 429 then success → returns vector."""
        import openai

        settings = _make_settings(embedding_model="openai", openai_api_key="sk-test-key")
        service = EmbeddingService(settings)

        # Create mock rate limit error
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        # Create mock success response
        mock_embedding = MagicMock()
        mock_embedding.index = 0
        mock_embedding.embedding = [0.1] * 1536

        mock_success = MagicMock()
        mock_success.data = [mock_embedding]

        # Mock the OpenAI client
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(
            side_effect=[rate_limit_error, rate_limit_error, mock_success]
        )
        service._openai_client = mock_client

        with patch("gapsense.ai.embedding_service.asyncio.sleep", new_callable=AsyncMock):
            result = await service.embed("test text")

        assert len(result) == 1536
        assert mock_client.embeddings.create.call_count == 3

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted_raises_after_max_retries(self):
        """All 3 attempts fail with rate limit → raises RateLimitError."""
        import openai

        settings = _make_settings(embedding_model="openai", openai_api_key="sk-test-key")
        service = EmbeddingService(settings)

        # Create mock rate limit error
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=mock_response,
            body=None,
        )

        # Mock the OpenAI client - all attempts fail
        mock_client = AsyncMock()
        mock_client.embeddings.create = AsyncMock(
            side_effect=[rate_limit_error, rate_limit_error, rate_limit_error]
        )
        service._openai_client = mock_client

        with patch("gapsense.ai.embedding_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(openai.RateLimitError):
                await service.embed("test text")

        assert mock_client.embeddings.create.call_count == 3


class TestBuildIndicatorChunk:
    """Unit tests for build_indicator_chunk static method."""

    def test_basic_format(self):
        """Verify basic indicator chunk format with typical inputs."""
        result = EmbeddingService.build_indicator_chunk(
            node_code="B4.1.3.1",
            node_title="Fraction Operations",
            indicator_code="B4.1.3.1.2",
            indicator_title="Add fractions with unlike denominators",
            error_patterns=[
                "Adds numerators and denominators separately",
                "Ignores denominator when adding",
                "Fails to find common denominator",
            ],
        )

        expected = (
            "Curriculum node: B4.1.3.1 \u2014 Fraction Operations\n"
            "Indicator: B4.1.3.1.2 \u2014 Add fractions with unlike denominators\n"
            "Common errors: Adds numerators and denominators separately; "
            "Ignores denominator when adding; Fails to find common denominator"
        )
        assert result == expected

    def test_empty_error_patterns(self):
        """Verify format with empty error patterns list."""
        result = EmbeddingService.build_indicator_chunk(
            node_code="B1.1.1.1",
            node_title="Counting",
            indicator_code="B1.1.1.1.1",
            indicator_title="Count to 10",
            error_patterns=[],
        )

        expected = (
            "Curriculum node: B1.1.1.1 \u2014 Counting\n"
            "Indicator: B1.1.1.1.1 \u2014 Count to 10\n"
            "Common errors: "
        )
        assert result == expected

    def test_single_error_pattern(self):
        """Verify format with a single error pattern."""
        result = EmbeddingService.build_indicator_chunk(
            node_code="B2.1.1.1",
            node_title="Addition",
            indicator_code="B2.1.1.1.1",
            indicator_title="Add single digits",
            error_patterns=["Counts on fingers incorrectly"],
        )

        assert "Common errors: Counts on fingers incorrectly" in result
        assert ";" not in result.split("Common errors: ")[1]
