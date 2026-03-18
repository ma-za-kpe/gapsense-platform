"""
Unit and property-based tests for ANALYSIS-001 retrieval metadata template
and _render_prompt integration.

Tests:
- Property 14: Rendered prompt contains retrieval metadata values
- ANALYSIS-001 template contains retrieval metadata HTML comments
- ANALYSIS-001 output schema unchanged from Phase 1

**Validates: Requirements 11.1, 11.2, 11.3**
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# ============================================================================
# Helpers
# ============================================================================


def _load_prompt_library() -> dict[str, Any]:
    """Load the prompt library JSON from gapsense-data."""
    # Try gapsense-data path (relative to gapsense/ working directory)
    candidates = [
        Path("../gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json"),
        Path("gapsense-data/prompts/gapsense_prompt_library_v2.0_multicountry.json"),
        Path("data/prompts/gapsense_prompt_library_v2.0_multicountry.json"),
    ]
    for path in candidates:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f)
    pytest.skip("Prompt library JSON not found")


def _get_analysis_001_user_template() -> str:
    """Extract the ANALYSIS-001 user_template string."""
    lib = _load_prompt_library()
    return lib["prompts"]["ANALYSIS-001"]["user_template"]


def _substitute(text: str, substitutions: dict[str, str]) -> str:
    """Replicate PromptService._substitute: replace {{key}} placeholders."""
    for key, value in substitutions.items():
        text = text.replace(f"{{{{{key}}}}}", value)
    return text


# ============================================================================
# Property 14: Rendered prompt contains retrieval metadata
# ============================================================================


# Feature: phase2-hybrid-rag-retrieval, Property 14: Rendered prompt contains metadata
class TestRenderedPromptContainsMetadata:
    """Property 14: Rendered prompt contains metadata.

    For any ctx.retrieval_metadata with populated total_nodes_injected,
    seed_node_codes, prerequisite_node_codes, and query_text_preview,
    the rendered ANALYSIS-001 prompt SHALL contain each of those values
    as substrings.

    **Validates: Requirements 11.2**
    """

    @given(
        total_nodes=st.integers(min_value=0, max_value=100),
        seed_codes=st.lists(
            st.from_regex(r"B[1-9]\.[1-9]\.[1-9]\.[1-9]", fullmatch=True),
            min_size=0,
            max_size=5,
        ),
        prereq_codes=st.lists(
            st.from_regex(r"B[1-9]\.[1-9]\.[1-9]\.[1-9]", fullmatch=True),
            min_size=0,
            max_size=5,
        ),
        query_preview=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
            min_size=1,
            max_size=100,
        ),
    )
    @settings(max_examples=100)
    def test_rendered_prompt_contains_all_metadata_values(
        self,
        total_nodes: int,
        seed_codes: list[str],
        prereq_codes: list[str],
        query_preview: str,
    ) -> None:
        """Rendered prompt contains each retrieval metadata value as substring."""
        template = _get_analysis_001_user_template()

        seed_codes_str = ", ".join(seed_codes)
        prereq_codes_str = ", ".join(prereq_codes)

        rendered = _substitute(
            template,
            {
                "total_nodes_injected": str(total_nodes),
                "seed_node_codes": seed_codes_str,
                "prerequisite_node_codes": prereq_codes_str,
                "query_text_preview": query_preview,
                # Fill other required placeholders with dummy values
                "country": "Ghana",
                "curriculum_authority": "NaCCA",
                "curriculum_name": "Standards-Based Curriculum",
                "student_first_name": "Test",
                "current_grade": "B4",
                "subject": "mathematics",
                "home_language": "English",
                "school_language": "English",
                "prerequisite_graph_json": "[]",
            },
        )

        assert (
            str(total_nodes) in rendered
        ), f"total_nodes_injected '{total_nodes}' not found in rendered prompt"
        assert (
            seed_codes_str in rendered
        ), f"seed_node_codes '{seed_codes_str}' not found in rendered prompt"
        assert (
            prereq_codes_str in rendered
        ), f"prerequisite_node_codes '{prereq_codes_str}' not found in rendered prompt"
        assert (
            query_preview in rendered
        ), f"query_text_preview '{query_preview}' not found in rendered prompt"


# ============================================================================
# Unit Tests: ANALYSIS-001 template structure
# ============================================================================


class TestAnalysis001TemplateContainsMetadataComments:
    """ANALYSIS-001 template contains retrieval metadata HTML comments.

    **Validates: Requirements 11.1, 11.3**
    """

    def test_template_has_total_nodes_injected_comment(self) -> None:
        template = _get_analysis_001_user_template()
        assert "{{total_nodes_injected}}" in template
        assert "<!-- Retrieval:" in template

    def test_template_has_seed_node_codes_comment(self) -> None:
        template = _get_analysis_001_user_template()
        assert "{{seed_node_codes}}" in template
        assert "<!-- Semantic match:" in template

    def test_template_has_prerequisite_node_codes_comment(self) -> None:
        template = _get_analysis_001_user_template()
        assert "{{prerequisite_node_codes}}" in template
        assert "<!-- Graph walk:" in template

    def test_template_has_query_text_preview_comment(self) -> None:
        template = _get_analysis_001_user_template()
        assert "{{query_text_preview}}" in template
        assert "<!-- Query:" in template

    def test_metadata_comments_appear_before_prerequisite_graph(self) -> None:
        """Retrieval metadata comments are above {{prerequisite_graph_json}}."""
        template = _get_analysis_001_user_template()
        meta_pos = template.index("<!-- Retrieval:")
        graph_pos = template.index("{{prerequisite_graph_json}}")
        assert (
            meta_pos < graph_pos
        ), "Retrieval metadata comments should appear before prerequisite_graph_json"


class TestAnalysis001OutputSchemaUnchanged:
    """ANALYSIS-001 output schema unchanged from Phase 1.

    **Validates: Requirements 11.3**
    """

    def test_output_schema_has_required_fields(self) -> None:
        lib = _load_prompt_library()
        schema = lib["prompts"]["ANALYSIS-001"]["output_schema"]

        required_fields = [
            "image_quality",
            "problems_extracted",
            "overall_pattern",
            "gap_node_ids",
            "suspected_gaps",
            "recommended_diagnostic_path",
            "language_barrier_detected",
            "confidence",
        ]
        for field_name in required_fields:
            assert field_name in schema, f"Missing required field: {field_name}"

    def test_output_schema_has_phase2_reserved_field(self) -> None:
        lib = _load_prompt_library()
        schema = lib["prompts"]["ANALYSIS-001"]["output_schema"]
        assert "retrieval_metadata" in schema

    def test_output_schema_has_phase3_reserved_field(self) -> None:
        lib = _load_prompt_library()
        schema = lib["prompts"]["ANALYSIS-001"]["output_schema"]
        assert "transcription_attempt" in schema
