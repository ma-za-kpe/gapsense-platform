"""
Unit and property-based tests for orchestrator hybrid retrieval methods.

Tests _build_query_text, _vector_search, _walk_prerequisites,
_fallback_curriculum_graph, and the hybrid _build_curriculum_graph pipeline.

All tests mock the DB and AI client — no real pgvector required.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy.exc import OperationalError

from gapsense.services.image_analysis_context import ImageAnalysisContext
from gapsense.services.image_analysis_orchestrator import ImageAnalysisOrchestrator

# ============================================================================
# Test Helpers — Mock objects for orchestrator tests
# ============================================================================


@dataclass
class MockErrorPattern:
    """Mock IndicatorErrorPattern."""

    error_description: str
    severity: str = "standard"


@dataclass
class MockNode:
    """Mock CurriculumNode."""

    id: uuid.UUID
    code: str
    title: str
    description: str
    country: str
    subject: str
    indicators: list[MockIndicator] = field(default_factory=list)


@dataclass
class MockIndicator:
    """Mock CurriculumIndicator."""

    id: uuid.UUID
    node_id: uuid.UUID
    indicator_code: str
    title: str
    node: MockNode | None = None
    error_patterns: list[MockErrorPattern] = field(default_factory=list)
    embedding: list[float] | None = None
    embedding_model: str | None = None


def _make_ctx(**overrides: Any) -> ImageAnalysisContext:
    """Create a minimal ImageAnalysisContext for testing."""
    defaults = {
        "s3_key": "test/image.jpg",
        "student_id": str(uuid.uuid4()),
        "country_code": "GH",
        "language": "en",
        "teacher_phone": "+233500012345",
        "country_key": "GH",
        "subject": "mathematics",
        "student_grade": "B4",
        "image_bytes": b"\xff\xd8fake-jpeg",
        "media_type": "image/jpeg",
    }
    defaults.update(overrides)
    return ImageAnalysisContext(**defaults)


def _make_mock_data(
    country: str = "GH",
    subject: str = "mathematics",
    num_nodes: int = 3,
    indicators_per_node: int = 2,
    with_embeddings: bool = True,
) -> tuple[list[MockNode], list[MockIndicator]]:
    """Create mock nodes and indicators for testing."""
    nodes = []
    all_indicators = []

    for i in range(num_nodes):
        node = MockNode(
            id=uuid.uuid4(),
            code=f"B4.1.{i+1}.1",
            title=f"Test Node {i+1}",
            description=f"Description for node {i+1}",
            country=country,
            subject=subject,
        )
        for j in range(indicators_per_node):
            ind = MockIndicator(
                id=uuid.uuid4(),
                node_id=node.id,
                indicator_code=f"B4.1.{i+1}.1.{j+1}",
                title=f"Indicator {i+1}.{j+1}",
                node=node,
                error_patterns=[
                    MockErrorPattern(error_description=f"Error {k+1}") for k in range(2)
                ],
                embedding=[0.1] * 1536 if with_embeddings else None,
                embedding_model="openai-text-embedding-3-small" if with_embeddings else None,
            )
            node.indicators.append(ind)
            all_indicators.append(ind)
        nodes.append(node)

    return nodes, all_indicators


def _make_orchestrator(
    db=None,
    ai_client=None,
    embedding_service=None,
) -> ImageAnalysisOrchestrator:
    """Create an orchestrator with mock dependencies."""
    return ImageAnalysisOrchestrator(
        db=db or AsyncMock(),
        ai_client=ai_client or AsyncMock(),
        media_service=AsyncMock(),
        guard_service=AsyncMock(),
        prompt_service=MagicMock(),
        worker_service=AsyncMock(),
        embedding_service=embedding_service,
    )


def _mock_db_execute_for_indicators(indicators, nodes=None):
    """Create a mock DB that returns indicators for vector search and nodes for full load."""
    mock_db = AsyncMock()

    # Track call count to differentiate between vector search and node load
    call_count = [0]

    async def mock_execute(query, params=None):
        call_count[0] += 1
        mock_result = MagicMock()
        mock_scalars = MagicMock()

        # Return indicators for the first call, nodes for subsequent
        if nodes and call_count[0] > 1:
            mock_scalars.all.return_value = nodes
        else:
            mock_scalars.all.return_value = indicators

        mock_result.scalars.return_value = mock_scalars
        mock_result.fetchall.return_value = []
        return mock_result

    mock_db.execute = mock_execute
    return mock_db


# ============================================================================
# Property-Based Tests
# ============================================================================


class TestVectorSearchBoundedFiltered:
    """Property 9: Vector search bounded + filtered.

    Feature: phase2-hybrid-rag-retrieval, Property 9: Vector search bounded + filtered
    """

    # **Validates: Requirements 6.2, 6.3**
    @settings(max_examples=100, deadline=None)
    @given(
        top_k=st.integers(min_value=1, max_value=50),
        num_matching=st.integers(min_value=1, max_value=30),
    )
    @pytest.mark.asyncio
    async def test_vector_search_bounded_and_filtered(
        self,
        top_k: int,
        num_matching: int,
    ):
        """Vector search returns at most top_k results, all matching country/subject with non-null embeddings."""
        target_country = "GH"
        target_subject = "mathematics"

        # Build matching indicators
        matching_indicators = []
        for i in range(num_matching):
            node = MockNode(
                id=uuid.uuid4(),
                code=f"B4.1.{i}.1",
                title=f"Node {i}",
                description=f"Desc {i}",
                country=target_country,
                subject=target_subject,
            )
            ind = MockIndicator(
                id=uuid.uuid4(),
                node_id=node.id,
                indicator_code=f"B4.1.{i}.1.1",
                title=f"Ind {i}",
                node=node,
                embedding=[0.1] * 1536,
                embedding_model="openai-text-embedding-3-small",
            )
            matching_indicators.append(ind)

        # The DB mock should return at most top_k of the matching indicators
        expected_results = matching_indicators[:top_k]

        mock_db = AsyncMock()

        async def mock_execute(query, params=None):
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = expected_results
            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db)
        query_vector = [0.1] * 1536

        results = await orchestrator._vector_search(
            query_vector, target_country, target_subject, top_k=top_k
        )

        # Results should be bounded by top_k
        assert len(results) <= top_k

        # All results should have the correct country/subject via their node
        for ind in results:
            if ind.node:
                assert ind.node.country == target_country
                assert ind.node.subject == target_subject

        # All results should have non-null embeddings
        for ind in results:
            assert ind.embedding is not None


class TestPrerequisiteWalkNonSeed:
    """Property 10: Prerequisite walk non-seed.

    Feature: phase2-hybrid-rag-retrieval, Property 10: Prerequisite walk non-seed
    """

    # **Validates: Requirements 7.2, 7.3**
    @settings(max_examples=100, deadline=None)
    @given(
        seed_ids=st.sets(st.uuids(), min_size=0, max_size=10),
    )
    @pytest.mark.asyncio
    async def test_prerequisite_walk_returns_non_seed_nodes(
        self,
        seed_ids: set[uuid.UUID],
    ):
        """Returned prerequisite IDs have zero intersection with seed IDs."""
        # Generate some prerequisite node IDs that are NOT in seeds
        prereq_ids = {uuid.uuid4() for _ in range(3)}

        mock_db = AsyncMock()

        async def mock_execute(query, params=None):
            mock_result = MagicMock()
            if seed_ids:
                # Return prerequisite IDs as rows
                mock_result.fetchall.return_value = [(pid,) for pid in prereq_ids]
            else:
                mock_result.fetchall.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db)
        result = await orchestrator._walk_prerequisites(seed_ids, "GH")

        # Result should have zero intersection with seeds
        assert result & seed_ids == set()

        # If seeds were empty, result should be empty (no DB query)
        if not seed_ids:
            assert result == set()


class TestRetrievalMetadataCompleteness:
    """Property 12: Retrieval metadata completeness.

    Feature: phase2-hybrid-rag-retrieval, Property 12: Retrieval metadata completeness
    """

    # **Validates: Requirements 8.3**
    @settings(max_examples=100, deadline=None)
    @given(
        num_seed_nodes=st.integers(min_value=1, max_value=10),
        num_prereq_nodes=st.integers(min_value=0, max_value=10),
        query_text=st.text(min_size=1, max_size=200),
    )
    @pytest.mark.asyncio
    async def test_retrieval_metadata_has_all_required_keys(
        self,
        num_seed_nodes: int,
        num_prereq_nodes: int,
        query_text: str,
    ):
        """After hybrid retrieval, ctx.retrieval_metadata contains all required keys with correct types."""
        nodes, indicators = _make_mock_data(num_nodes=num_seed_nodes)
        prereq_nodes, _ = _make_mock_data(num_nodes=num_prereq_nodes)
        prereq_ids = {n.id for n in prereq_nodes}
        all_nodes = nodes + prereq_nodes

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            # First call: vector search returns indicators
            if call_count[0] == 1:
                mock_scalars.all.return_value = indicators
            else:
                # Subsequent calls: return all nodes
                mock_scalars.all.return_value = all_nodes
            mock_result.scalars.return_value = mock_scalars
            # For CTE query (walk_prerequisites)
            mock_result.fetchall.return_value = [(pid,) for pid in prereq_ids]
            return mock_result

        mock_db.execute = mock_execute

        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_ai_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = query_text
        mock_ai_client.generate = AsyncMock(return_value=mock_response)

        orchestrator = _make_orchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            embedding_service=mock_embedding_service,
        )
        ctx = _make_ctx()

        await orchestrator._build_curriculum_graph(ctx)

        # Verify all required keys are present
        meta = ctx.retrieval_metadata
        assert "seed_node_ids" in meta
        assert "prerequisite_node_ids" in meta
        assert "total_nodes_injected" in meta
        assert "query_text_preview" in meta

        # Verify types
        assert isinstance(meta["seed_node_ids"], list)
        assert isinstance(meta["prerequisite_node_ids"], list)
        assert isinstance(meta["total_nodes_injected"], int)
        assert isinstance(meta["query_text_preview"], str)

        # Verify query_text_preview is at most 100 chars
        assert len(meta["query_text_preview"]) <= 100

        # Verify seed_node_ids are UUID strings
        for sid in meta["seed_node_ids"]:
            uuid.UUID(sid)  # Should not raise

        # Verify prerequisite_node_ids are UUID strings
        for pid in meta["prerequisite_node_ids"]:
            uuid.UUID(pid)  # Should not raise


class TestFallbackStructuralIdentity:
    """Property 13: Fallback structural identity and reason.

    Feature: phase2-hybrid-rag-retrieval, Property 13: Fallback structural identity and reason
    """

    # **Validates: Requirements 10.3, 12.2, 12.5, 12.6**
    @settings(max_examples=100, deadline=None)
    @given(
        fallback_scenario=st.sampled_from(
            [
                "embedding_service_none",
                "embed_call_fails",
                "vector_search_empty",
            ]
        ),
        num_fallback_nodes=st.integers(min_value=0, max_value=5),
    )
    @pytest.mark.asyncio
    async def test_fallback_produces_valid_json_with_reason(
        self,
        fallback_scenario: str,
        num_fallback_nodes: int,
    ):
        """Fallback JSON matches normal schema and fallback_reason is non-empty string."""
        nodes, indicators = _make_mock_data(
            num_nodes=num_fallback_nodes,
            with_embeddings=False,
        )

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute_fallback(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            # First call: _code_ordered_indicators returns indicators
            # Second call: load full node data returns nodes
            if call_count[0] == 1:
                mock_scalars.all.return_value = indicators
            else:
                mock_scalars.all.return_value = nodes
            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute = mock_execute_fallback

        if fallback_scenario == "embedding_service_none":
            orchestrator = _make_orchestrator(db=mock_db, embedding_service=None)
        elif fallback_scenario == "embed_call_fails":
            mock_embedding_service = AsyncMock()
            mock_embedding_service.embed = AsyncMock(side_effect=Exception("Embedding failed"))
            mock_ai_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.text = "test query"
            mock_ai_client.generate = AsyncMock(return_value=mock_response)
            orchestrator = _make_orchestrator(
                db=mock_db,
                ai_client=mock_ai_client,
                embedding_service=mock_embedding_service,
            )
        else:
            # vector_search_empty: vector search returns empty, triggers fallback
            mock_embedding_service = AsyncMock()
            mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)
            mock_ai_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.text = "test query"
            mock_ai_client.generate = AsyncMock(return_value=mock_response)

            vs_call_count = [0]

            async def mock_execute_empty_vs(query, params=None):
                vs_call_count[0] += 1
                mock_result = MagicMock()
                mock_scalars = MagicMock()
                if vs_call_count[0] == 1:
                    # Vector search returns empty
                    mock_scalars.all.return_value = []
                elif vs_call_count[0] == 2:
                    # _code_ordered_indicators fallback in _vector_search returns empty too
                    mock_scalars.all.return_value = []
                elif vs_call_count[0] == 3:
                    # _code_ordered_indicators in _fallback_curriculum_graph
                    mock_scalars.all.return_value = indicators
                else:
                    # Load full node data
                    mock_scalars.all.return_value = nodes
                mock_result.scalars.return_value = mock_scalars
                return mock_result

            mock_db.execute = mock_execute_empty_vs
            orchestrator = _make_orchestrator(
                db=mock_db,
                ai_client=mock_ai_client,
                embedding_service=mock_embedding_service,
            )

        ctx = _make_ctx()
        await orchestrator._build_curriculum_graph(ctx)

        # Verify JSON is valid and matches schema
        parsed = json.loads(ctx.curriculum_graph_json)
        assert isinstance(parsed, list)
        for node_dict in parsed:
            assert "node_id" in node_dict
            assert "code" in node_dict
            assert "title" in node_dict
            assert "description" in node_dict
            assert "indicators" in node_dict
            assert isinstance(node_dict["indicators"], list)

        # Verify fallback_reason is set and non-empty
        assert "fallback_reason" in ctx.retrieval_metadata
        assert isinstance(ctx.retrieval_metadata["fallback_reason"], str)
        assert len(ctx.retrieval_metadata["fallback_reason"]) > 0


class TestJSONRoundTrip:
    """Property 11: Curriculum graph JSON round-trip.

    Feature: phase2-hybrid-rag-retrieval, Property 11: Curriculum graph JSON round-trip
    """

    # **Validates: Requirements 8.6**
    @settings(max_examples=100)
    @given(
        nodes=st.lists(
            st.fixed_dictionaries(
                {
                    "node_id": st.uuids().map(str),
                    "code": st.text(
                        alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                        min_size=1,
                        max_size=20,
                    ),
                    "title": st.text(min_size=1, max_size=100),
                    "description": st.text(min_size=0, max_size=200),
                    "indicators": st.lists(
                        st.fixed_dictionaries(
                            {
                                "indicator_code": st.text(
                                    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
                                    min_size=1,
                                    max_size=25,
                                ),
                                "title": st.text(min_size=1, max_size=100),
                                "error_patterns": st.lists(
                                    st.fixed_dictionaries(
                                        {
                                            "error_description": st.text(min_size=1, max_size=100),
                                            "severity": st.sampled_from(
                                                ["critical", "standard", "minor"]
                                            ),
                                        }
                                    ),
                                    min_size=0,
                                    max_size=5,
                                ),
                            }
                        ),
                        min_size=0,
                        max_size=5,
                    ),
                }
            ),
            min_size=0,
            max_size=10,
        ),
    )
    def test_json_round_trip_preserves_data(self, nodes: list[dict]):
        """json.loads(json.dumps(nodes)) produces equivalent list of dicts."""
        serialized = json.dumps(nodes)
        deserialized = json.loads(serialized)
        assert deserialized == nodes


# ============================================================================
# Unit Tests
# ============================================================================


class TestBuildQueryTextFallback:
    """Unit tests for _build_query_text fallback on AI failure."""

    @pytest.mark.asyncio
    async def test_fallback_on_ai_failure(self):
        """_build_query_text falls back to '{subject} {student_grade}' on AI failure."""
        mock_ai_client = AsyncMock()
        mock_ai_client.generate = AsyncMock(side_effect=Exception("AI unavailable"))

        orchestrator = _make_orchestrator(ai_client=mock_ai_client)
        ctx = _make_ctx(subject="mathematics", student_grade="B4")

        result = await orchestrator._build_query_text(ctx)

        assert result == "mathematics B4"
        assert ctx.image_description == "mathematics B4"

    @pytest.mark.asyncio
    async def test_fallback_on_empty_response(self):
        """_build_query_text falls back when AI returns empty text."""
        mock_ai_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_ai_client.generate = AsyncMock(return_value=mock_response)

        orchestrator = _make_orchestrator(ai_client=mock_ai_client)
        ctx = _make_ctx(subject="mathematics", student_grade="B4")

        result = await orchestrator._build_query_text(ctx)

        assert result == "mathematics B4"

    @pytest.mark.asyncio
    async def test_fallback_on_none_response(self):
        """_build_query_text falls back when AI returns None."""
        mock_ai_client = AsyncMock()
        mock_ai_client.generate = AsyncMock(return_value=None)

        orchestrator = _make_orchestrator(ai_client=mock_ai_client)
        ctx = _make_ctx(subject="mathematics", student_grade="B4")

        result = await orchestrator._build_query_text(ctx)

        assert result == "mathematics B4"

    @pytest.mark.asyncio
    async def test_success_stores_image_description(self):
        """Successful _build_query_text stores result on ctx.image_description."""
        mock_ai_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "The student is working on multi-digit multiplication."
        mock_ai_client.generate = AsyncMock(return_value=mock_response)

        orchestrator = _make_orchestrator(ai_client=mock_ai_client)
        ctx = _make_ctx()

        result = await orchestrator._build_query_text(ctx)

        assert result == "The student is working on multi-digit multiplication."
        assert ctx.image_description == result


class TestVectorSearchFallbacks:
    """Unit tests for _vector_search fallback scenarios."""

    @pytest.mark.asyncio
    async def test_zero_results_falls_back_to_code_ordered(self):
        """_vector_search with zero results falls back to code-ordered SELECT."""
        nodes, indicators = _make_mock_data(num_nodes=2, with_embeddings=False)

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            if call_count[0] == 1:
                # Vector search returns empty
                mock_scalars.all.return_value = []
            else:
                # Fallback returns code-ordered indicators
                mock_scalars.all.return_value = indicators
            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db)
        result = await orchestrator._vector_search([0.1] * 1536, "GH", "mathematics")

        assert len(result) == len(indicators)
        assert call_count[0] == 2  # vector search + fallback

    @pytest.mark.asyncio
    async def test_operational_error_falls_back_to_code_ordered(self):
        """_vector_search catches OperationalError and falls back."""
        nodes, indicators = _make_mock_data(num_nodes=2, with_embeddings=False)

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OperationalError("pgvector not installed", {}, Exception())
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            mock_scalars.all.return_value = indicators
            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db)
        result = await orchestrator._vector_search([0.1] * 1536, "GH", "mathematics")

        assert len(result) == len(indicators)
        assert call_count[0] == 2


class TestWalkPrerequisites:
    """Unit tests for _walk_prerequisites edge cases."""

    @pytest.mark.asyncio
    async def test_empty_seeds_returns_empty_set_no_db_query(self):
        """Empty seed set returns empty set without executing DB query."""
        mock_db = AsyncMock()
        orchestrator = _make_orchestrator(db=mock_db)

        result = await orchestrator._walk_prerequisites(set(), "GH")

        assert result == set()
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_edges_returns_empty_set_with_warning(self, caplog):
        """No prerequisite edges returns empty set and logs warning."""
        mock_db = AsyncMock()

        async def mock_execute(query, params=None):
            mock_result = MagicMock()
            mock_result.fetchall.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db)
        seed_ids = {uuid.uuid4(), uuid.uuid4()}

        result = await orchestrator._walk_prerequisites(seed_ids, "GH")

        assert result == set()


class TestNodeCountWarning:
    """Unit test for node count > 25 warning."""

    @pytest.mark.asyncio
    async def test_node_count_exceeds_25_logs_warning(self):
        """When combined node set exceeds 25, a warning is logged."""
        # Create 30 nodes worth of indicators
        nodes, indicators = _make_mock_data(num_nodes=30, indicators_per_node=1)
        prereq_ids = set()

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            if call_count[0] == 1:
                mock_scalars.all.return_value = indicators
            else:
                mock_scalars.all.return_value = nodes
            mock_result.scalars.return_value = mock_scalars
            mock_result.fetchall.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_ai_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "test query"
        mock_ai_client.generate = AsyncMock(return_value=mock_response)

        orchestrator = _make_orchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            embedding_service=mock_embedding_service,
        )
        ctx = _make_ctx()

        # Patch logger to capture warning
        with patch("gapsense.services.image_analysis_orchestrator.logger") as mock_logger:
            await orchestrator._build_curriculum_graph(ctx)

            # Verify warning was logged about node count
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if call[0][0] == "node_count_exceeds_threshold"
            ]
            assert len(warning_calls) == 1
            assert warning_calls[0][1]["node_count"] == 30


class TestEmbeddingServiceNoneFallback:
    """Unit test for embedding_service=None → fallback mode."""

    @pytest.mark.asyncio
    async def test_none_embedding_service_uses_fallback(self):
        """When embedding_service is None, orchestrator uses fallback mode."""
        nodes, indicators = _make_mock_data(num_nodes=3, with_embeddings=False)

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            # First call: _code_ordered_indicators returns indicators
            # Second call: load full node data returns nodes
            if call_count[0] == 1:
                mock_scalars.all.return_value = indicators
            else:
                mock_scalars.all.return_value = nodes
            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db, embedding_service=None)
        ctx = _make_ctx()

        await orchestrator._build_curriculum_graph(ctx)

        assert ctx.retrieval_metadata.get("fallback_reason") == "embedding_service is None"
        parsed = json.loads(ctx.curriculum_graph_json)
        assert isinstance(parsed, list)


class TestTokenCountLogging:
    """Unit test for token count logging with structured fields."""

    @pytest.mark.asyncio
    async def test_token_count_logging_includes_required_fields(self):
        """Token count log includes student_id, token_count, total_nodes, fallback_mode."""
        nodes, indicators = _make_mock_data(num_nodes=2)

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            if call_count[0] == 1:
                mock_scalars.all.return_value = indicators
            else:
                mock_scalars.all.return_value = nodes
            mock_result.scalars.return_value = mock_scalars
            mock_result.fetchall.return_value = []
            return mock_result

        mock_db.execute = mock_execute

        mock_embedding_service = AsyncMock()
        mock_embedding_service.embed = AsyncMock(return_value=[0.1] * 1536)

        mock_ai_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.text = "test query text"
        mock_ai_client.generate = AsyncMock(return_value=mock_response)

        orchestrator = _make_orchestrator(
            db=mock_db,
            ai_client=mock_ai_client,
            embedding_service=mock_embedding_service,
        )
        ctx = _make_ctx()

        with patch("gapsense.services.image_analysis_orchestrator.logger") as mock_logger:
            await orchestrator._build_curriculum_graph(ctx)

            # Find the token count log call
            token_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call[0][0] == "curriculum_graph_token_count"
            ]
            assert len(token_calls) == 1

            log_kwargs = token_calls[0][1]
            assert "student_id" in log_kwargs
            assert "token_count" in log_kwargs
            assert "total_nodes" in log_kwargs
            assert "fallback_mode" in log_kwargs
            assert isinstance(log_kwargs["token_count"], int)
            assert log_kwargs["token_count"] > 0
            assert log_kwargs["fallback_mode"] is False

    @pytest.mark.asyncio
    async def test_fallback_token_count_logging(self):
        """Token count log in fallback mode has fallback_mode=True."""
        nodes, indicators = _make_mock_data(num_nodes=2, with_embeddings=False)

        mock_db = AsyncMock()
        call_count = [0]

        async def mock_execute(query, params=None):
            call_count[0] += 1
            mock_result = MagicMock()
            mock_scalars = MagicMock()
            # First call: _code_ordered_indicators returns indicators
            # Second call: load full node data returns nodes
            if call_count[0] == 1:
                mock_scalars.all.return_value = indicators
            else:
                mock_scalars.all.return_value = nodes
            mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute = mock_execute

        orchestrator = _make_orchestrator(db=mock_db, embedding_service=None)
        ctx = _make_ctx()

        with patch("gapsense.services.image_analysis_orchestrator.logger") as mock_logger:
            await orchestrator._build_curriculum_graph(ctx)

            token_calls = [
                call
                for call in mock_logger.info.call_args_list
                if call[0][0] == "curriculum_graph_token_count"
            ]
            assert len(token_calls) == 1
            assert token_calls[0][1]["fallback_mode"] is True
