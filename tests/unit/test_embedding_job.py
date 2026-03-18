"""
Unit and property-based tests for the embedding job.

Tests embedding job idempotency, result accounting, model consistency
enforcement, IVFFlat index guard, and force refresh behaviour.

All tests mock the DB and EmbeddingService — no real pgvector required.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.core.exceptions import ConfigurationError
from gapsense.jobs.embedding_job import (
    IVFFLAT_MIN_VECTORS,
    EmbeddingJobResult,
    _maybe_create_ivfflat_index,
    run_embedding_job,
)

# ============================================================================
# Test Helpers — In-memory mock DB for embedding job
# ============================================================================


@dataclass
class MockErrorPattern:
    """Mock IndicatorErrorPattern."""

    error_description: str


@dataclass
class MockNode:
    """Mock CurriculumNode."""

    id: uuid.UUID
    code: str
    title: str
    country: str
    subject: str


@dataclass
class MockIndicator:
    """Mock CurriculumIndicator with mutable embedding fields."""

    id: uuid.UUID
    node_id: uuid.UUID
    indicator_code: str
    title: str
    node: MockNode
    error_patterns: list[MockErrorPattern] = field(default_factory=list)
    embedding: list[float] | None = None
    embedding_model: str | None = None


def _make_indicators(
    count: int,
    country: str = "GH",
    subject: str = "mathematics",
    *,
    pre_embedded: int = 0,
    embedding_model: str | None = None,
) -> tuple[list[MockIndicator], list[MockNode]]:
    """Create mock indicators and nodes for testing.

    Args:
        count: Total number of indicators to create.
        pre_embedded: Number of indicators that already have embeddings.
        embedding_model: Model name for pre-embedded indicators.
    """
    node = MockNode(
        id=uuid.uuid4(),
        code="B4.1.3.1",
        title="Fraction Operations",
        country=country,
        subject=subject,
    )

    indicators = []
    for i in range(count):
        ind = MockIndicator(
            id=uuid.uuid4(),
            node_id=node.id,
            indicator_code=f"B4.1.3.1.{i + 1}",
            title=f"Indicator {i + 1}",
            node=node,
            error_patterns=[MockErrorPattern(error_description=f"Error {i + 1}")],
        )
        if i < pre_embedded:
            ind.embedding = [0.1] * 1536
            ind.embedding_model = embedding_model or "openai-text-embedding-3-small"
        indicators.append(ind)

    return indicators, [node]


def _make_mock_embedding_service(
    model_name: str = "openai-text-embedding-3-small", dims: int = 1536
):
    """Create a mock EmbeddingService."""
    service = MagicMock()
    service.model_name = model_name
    service.dimensions = dims

    async def mock_embed_batch(texts):
        return [[0.5] * dims for _ in texts]

    service.embed_batch = AsyncMock(side_effect=mock_embed_batch)
    return service


def _make_mock_session_factory(
    indicators: list[MockIndicator],
    nodes: list[MockNode],
):
    """Create a mock async session factory that simulates DB queries.

    Classifies SQLAlchemy queries by inspecting selected_columns, _distinct,
    and whereclause string representations.
    """
    all_indicators = indicators

    class MockResult:
        def __init__(self, value):
            self._value = value

        def scalar_one(self):
            return self._value

        def scalars(self):
            return self

        def all(self):
            return self._value

        def fetchall(self):
            return self._value

    def _get_where_strings(query) -> list[str]:
        """Get string representations of all where clauses."""
        if query.whereclause is None:
            return []
        try:
            return [str(c) for c in query.whereclause.clauses]
        except Exception:
            return [str(query.whereclause)]

    def _is_count_query(query) -> bool:
        """Check if query selects a count() aggregate."""
        from sqlalchemy.sql.functions import count as sa_count

        try:
            for col in query.selected_columns:
                # Check if the column is a count() function call
                if hasattr(col, "element") or (hasattr(col, "name") and col.name == "count_1"):
                    return True
                if isinstance(col, sa_count):
                    return True
                # Check the type name
                type_name = type(col).__name__
                if type_name == "Function" or getattr(col, "name", "") == "count":
                    return True
            return False
        except Exception:
            return False

    class MockSession:
        def __init__(self):
            self._committed = False

        async def execute(self, query, *args, **kwargs):
            from sqlalchemy.sql.expression import TextClause

            # Raw text SQL (CREATE INDEX)
            if isinstance(query, TextClause):
                return MockResult(None)

            where_strs = _get_where_strings(query)
            has_is_not_null = any("IS NOT NULL" in w for w in where_strs)
            has_is_null = any("IS NULL" in w and "IS NOT NULL" not in w for w in where_strs)

            # Count queries
            if _is_count_query(query):
                if has_is_not_null:
                    # Count of non-null embeddings (IVFFlat check)
                    count = sum(1 for ind in all_indicators if ind.embedding is not None)
                    return MockResult(count)
                # Total count (no embedding filter)
                return MockResult(len(all_indicators))

            # Distinct embedding_model query
            if hasattr(query, "_distinct") and query._distinct:
                models = set()
                for ind in all_indicators:
                    if ind.embedding is not None and ind.embedding_model is not None:
                        models.add(ind.embedding_model)
                return MockResult([(m,) for m in models])

            # SELECT indicators with IS NULL filter (unembedded only)
            if has_is_null:
                result = [ind for ind in all_indicators if ind.embedding is None]
                return MockResult(result)

            # Default: return all indicators (force_refresh path)
            return MockResult(list(all_indicators))

        async def commit(self):
            self._committed = True

        async def rollback(self):
            pass

        async def close(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    def factory():
        return MockSession()

    return factory


# ============================================================================
# Property-Based Tests
# ============================================================================


class TestEmbeddingJobIdempotency:
    """Property 3: Embedding job idempotency.

    Feature: phase2-hybrid-rag-retrieval, Property 3: Embedding job idempotency
    """

    # **Validates: Requirements 4.2, 4.5**
    @settings(max_examples=100)
    @given(
        num_indicators=st.integers(min_value=1, max_value=20),
    )
    @pytest.mark.asyncio
    async def test_second_run_reports_zero_newly_embedded(self, num_indicators: int):
        """Running the job twice without force_refresh: second run has newly_embedded=0."""
        indicators, nodes = _make_indicators(num_indicators)
        embedding_service = _make_mock_embedding_service()

        # First run: embed all indicators
        session_factory = _make_mock_session_factory(indicators, nodes)
        result1 = await run_embedding_job(
            country="GH",
            subject="mathematics",
            force_refresh=False,
            session_factory=session_factory,
            embedding_service=embedding_service,
        )

        assert result1.newly_embedded == num_indicators
        assert result1.total_indicators == num_indicators

        # After first run, all indicators should have embeddings
        # (our mock session factory reflects the mutated indicators)
        session_factory2 = _make_mock_session_factory(indicators, nodes)
        result2 = await run_embedding_job(
            country="GH",
            subject="mathematics",
            force_refresh=False,
            session_factory=session_factory2,
            embedding_service=embedding_service,
        )

        assert result2.newly_embedded == 0
        assert result2.already_embedded == result1.newly_embedded + result1.already_embedded


class TestEmbeddingJobResultAccounting:
    """Property 6: Embedding job result accounting.

    Feature: phase2-hybrid-rag-retrieval, Property 6: Embedding job result accounting
    """

    # **Validates: Requirements 4.7**
    @settings(max_examples=100)
    @given(
        num_indicators=st.integers(min_value=0, max_value=30),
        pre_embedded=st.integers(min_value=0, max_value=30),
    )
    @pytest.mark.asyncio
    async def test_total_equals_newly_plus_already_plus_errors(
        self, num_indicators: int, pre_embedded: int
    ):
        """total_indicators == newly_embedded + already_embedded + errors."""
        # Ensure pre_embedded doesn't exceed total
        pre_embedded = min(pre_embedded, num_indicators)

        indicators, nodes = _make_indicators(num_indicators, pre_embedded=pre_embedded)
        embedding_service = _make_mock_embedding_service()
        session_factory = _make_mock_session_factory(indicators, nodes)

        result = await run_embedding_job(
            country="GH",
            subject="mathematics",
            force_refresh=False,
            session_factory=session_factory,
            embedding_service=embedding_service,
        )

        assert (
            result.total_indicators
            == result.newly_embedded + result.already_embedded + result.errors
        )


class TestEmbeddingModelConsistencyEnforcement:
    """Property 7: Embedding model consistency enforcement.

    Feature: phase2-hybrid-rag-retrieval, Property 7: Embedding model consistency enforcement
    """

    # **Validates: Requirements 4.8, 13.2**
    @settings(max_examples=100)
    @given(
        num_indicators=st.integers(min_value=2, max_value=20),
    )
    @pytest.mark.asyncio
    async def test_mismatch_aborts_without_modifications(self, num_indicators: int):
        """DB with different model embeddings + no force_refresh → abort, no modifications."""
        # Pre-embed half with a different model
        pre_embedded = max(1, num_indicators // 2)
        indicators, nodes = _make_indicators(
            num_indicators,
            pre_embedded=pre_embedded,
            embedding_model="old-model-v1",
        )

        # Current service uses a different model
        embedding_service = _make_mock_embedding_service(model_name="openai-text-embedding-3-small")
        session_factory = _make_mock_session_factory(indicators, nodes)

        # Capture original embeddings to verify no modifications
        original_embeddings = {
            ind.id: (ind.embedding[:] if ind.embedding else None, ind.embedding_model)
            for ind in indicators
        }

        with pytest.raises(ConfigurationError, match="model mismatch"):
            await run_embedding_job(
                country="GH",
                subject="mathematics",
                force_refresh=False,
                session_factory=session_factory,
                embedding_service=embedding_service,
            )

        # Verify no embeddings were modified
        for ind in indicators:
            orig_emb, orig_model = original_embeddings[ind.id]
            assert ind.embedding == orig_emb
            assert ind.embedding_model == orig_model


# ============================================================================
# Unit Tests
# ============================================================================


class TestIVFFlatGuard:
    """Test IVFFlat index creation with minimum vector guard."""

    @pytest.mark.asyncio
    async def test_skip_index_with_warning_when_below_minimum(self):
        """50 indicators → skip index creation with warning."""
        indicators, nodes = _make_indicators(50, pre_embedded=50)
        session_factory = _make_mock_session_factory(indicators, nodes)

        session = session_factory()
        async with session:
            with patch("gapsense.jobs.embedding_job.logger") as mock_logger:
                await _maybe_create_ivfflat_index(session, "GH", "mathematics")
                mock_logger.warning.assert_called_once()
                call_kwargs = mock_logger.warning.call_args
                assert call_kwargs[0][0] == "ivfflat_index_skipped"
                assert call_kwargs[1]["embedding_count"] == 50
                assert call_kwargs[1]["minimum_required"] == IVFFLAT_MIN_VECTORS

    @pytest.mark.asyncio
    async def test_create_index_when_above_minimum(self):
        """150 indicators → index created."""
        indicators, nodes = _make_indicators(150, pre_embedded=150)
        session_factory = _make_mock_session_factory(indicators, nodes)

        session = session_factory()
        async with session:
            with patch("gapsense.jobs.embedding_job.logger") as mock_logger:
                await _maybe_create_ivfflat_index(session, "GH", "mathematics")
                mock_logger.info.assert_called_once()
                call_kwargs = mock_logger.info.call_args
                assert call_kwargs[0][0] == "ivfflat_index_created"

    @pytest.mark.asyncio
    async def test_index_already_exists_no_error(self):
        """IVFFlat index already exists → no error (IF NOT EXISTS handles it)."""
        indicators, nodes = _make_indicators(150, pre_embedded=150)
        session_factory = _make_mock_session_factory(indicators, nodes)

        # Run twice — second should not error
        session1 = session_factory()
        async with session1:
            await _maybe_create_ivfflat_index(session1, "GH", "mathematics")

        session2 = session_factory()
        async with session2:
            await _maybe_create_ivfflat_index(session2, "GH", "mathematics")


class TestForceRefresh:
    """Test force_refresh overwrites existing embeddings."""

    @pytest.mark.asyncio
    async def test_force_refresh_overwrites_existing(self):
        """Force refresh overwrites existing embeddings."""
        indicators, nodes = _make_indicators(5, pre_embedded=5, embedding_model="old-model")

        new_service = _make_mock_embedding_service(model_name="new-model-v2", dims=1536)
        session_factory = _make_mock_session_factory(indicators, nodes)

        result = await run_embedding_job(
            country="GH",
            subject="mathematics",
            force_refresh=True,
            session_factory=session_factory,
            embedding_service=new_service,
        )

        assert result.newly_embedded == 5
        assert result.already_embedded == 0

        # All indicators should now have the new model
        for ind in indicators:
            assert ind.embedding_model == "new-model-v2"
            assert ind.embedding is not None


class TestEmbeddingJobResultDataclass:
    """Test EmbeddingJobResult dataclass."""

    def test_dataclass_fields(self):
        """EmbeddingJobResult has all required fields."""
        result = EmbeddingJobResult(
            country="GH",
            subject="mathematics",
            total_indicators=100,
            newly_embedded=80,
            already_embedded=15,
            errors=5,
            duration_seconds=12.34,
        )
        assert result.country == "GH"
        assert result.subject == "mathematics"
        assert result.total_indicators == 100
        assert result.newly_embedded == 80
        assert result.already_embedded == 15
        assert result.errors == 5
        assert result.duration_seconds == 12.34
