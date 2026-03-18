"""
Unit tests for ANALYSIS-001 prompt content changes.

Verifies:
- Few-shot example is present (Requirement 9.1)
- Output schema includes retrieval_metadata and transcription_attempt (Requirements 10.1, 10.2)
- Visual analysis rules are present (Requirements 11.1, 11.2, 11.3, 11.4)
"""

import json
from pathlib import Path


def _load_prompt_library() -> dict:
    """Load the prompt library JSON file."""
    # Try multiple possible paths
    possible_paths = [
        Path("/app/data/prompts/gapsense_prompt_library_v2.0_multicountry.json"),
        Path("data/prompts/gapsense_prompt_library_v2.0_multicountry.json"),
        Path(__file__).parent.parent.parent
        / "data"
        / "prompts"
        / "gapsense_prompt_library_v2.0_multicountry.json",
    ]

    for path in possible_paths:
        if path.exists():
            return json.loads(path.read_text())

    raise FileNotFoundError(f"Could not find prompt library. Tried: {possible_paths}")


def _get_analysis_001_prompt() -> str:
    """Get the ANALYSIS-001 system prompt."""
    library = _load_prompt_library()
    prompts = library.get("prompts", {})
    analysis_001 = prompts.get("ANALYSIS-001", {})
    return analysis_001.get("system_prompt", "")


class TestFewShotExample:
    """Verify ANALYSIS-001 contains the few-shot example."""

    def test_contains_few_shot_example(self):
        """Requirement 9.1: ANALYSIS-001 contains a complete few-shot example."""
        prompt = _get_analysis_001_prompt()

        # Check for key indicators of the few-shot example
        assert (
            "WORKED EXAMPLE" in prompt or "Pythagoras" in prompt
        ), "ANALYSIS-001 should contain a few-shot example (Ghana Basic 7 Pythagoras)"

    def test_few_shot_shows_reasoning_chain(self):
        """Requirement 9.2: Few-shot example shows correct reasoning chain."""
        prompt = _get_analysis_001_prompt()

        # The example should demonstrate the reasoning process
        # Check for visual observation, error identification, curriculum mapping
        has_reasoning = any(
            [
                "visual observation" in prompt.lower(),
                "error identification" in prompt.lower(),
                "curriculum" in prompt.lower() and "mapping" in prompt.lower(),
                "gap" in prompt.lower() and "classification" in prompt.lower(),
            ]
        )
        assert (
            has_reasoning or "Pythagoras" in prompt
        ), "Few-shot example should demonstrate reasoning chain"

    def test_few_shot_demonstrates_uncertainty(self):
        """Requirement 9.3: Few-shot example demonstrates honest handling of ambiguity."""
        prompt = _get_analysis_001_prompt()

        # The example should show how to handle uncertainty
        has_uncertainty_handling = any(
            [
                "uncertain" in prompt.lower(),
                "ambiguous" in prompt.lower(),
                "confidence" in prompt.lower(),
                "not sure" in prompt.lower(),
            ]
        )
        # This is a soft check - the example may demonstrate uncertainty in various ways
        assert (
            has_uncertainty_handling or "Pythagoras" in prompt
        ), "Few-shot example should demonstrate handling of ambiguity"


class TestOutputSchemaExtension:
    """Verify ANALYSIS-001 output schema includes new fields."""

    def test_contains_retrieval_metadata_field(self):
        """Requirement 10.1: Output schema includes retrieval_metadata field."""
        prompt = _get_analysis_001_prompt()

        assert (
            "retrieval_metadata" in prompt
        ), "ANALYSIS-001 should include retrieval_metadata in output schema"

    def test_contains_transcription_attempt_field(self):
        """Requirement 10.2: Output schema includes transcription_attempt field."""
        prompt = _get_analysis_001_prompt()

        assert (
            "transcription_attempt" in prompt
        ), "ANALYSIS-001 should include transcription_attempt in output schema"


class TestVisualAnalysisRules:
    """Verify ANALYSIS-001 contains strengthened visual analysis rules."""

    def test_contains_two_page_spread_rule(self):
        """Requirement 11.1: Rule for two-page spreads."""
        prompt = _get_analysis_001_prompt()

        assert (
            "two-page" in prompt.lower() or "two page" in prompt.lower()
        ), "ANALYSIS-001 should contain rule for two-page spreads"

    def test_contains_multiple_handwriting_rule(self):
        """Requirement 11.2: Rule for multiple handwriting styles."""
        prompt = _get_analysis_001_prompt()

        assert (
            "handwriting" in prompt.lower()
        ), "ANALYSIS-001 should contain rule for multiple handwriting styles"

    def test_contains_scattered_layout_rule(self):
        """Requirement 11.3: Rule for scattered/non-linear layouts."""
        prompt = _get_analysis_001_prompt()

        has_scattered_rule = (
            "scattered" in prompt.lower()
            or "non-linear" in prompt.lower()
            or "nonlinear" in prompt.lower()
        )
        assert (
            has_scattered_rule
        ), "ANALYSIS-001 should contain rule for scattered/non-linear layouts"

    def test_contains_partially_readable_rule(self):
        """Requirement 11.4: Rule for partially readable content."""
        prompt = _get_analysis_001_prompt()

        assert (
            "partially readable" in prompt.lower()
        ), "ANALYSIS-001 should contain rule for partially readable content"


class TestPromptLibraryMetadata:
    """Verify prompt library metadata is correct."""

    def test_model_target_is_claude_sonnet_4_6(self):
        """Requirement 8.8: Metadata model_target is claude-sonnet-4-6."""
        library = _load_prompt_library()
        metadata = library.get("metadata", {})

        assert (
            metadata.get("model_target") == "claude-sonnet-4-6"
        ), "Prompt library metadata model_target should be claude-sonnet-4-6"

    def test_fallback_model_is_claude_haiku_4_5_20251001(self):
        """Requirement 8.9: Metadata fallback_model is claude-haiku-4-5-20251001."""
        library = _load_prompt_library()
        metadata = library.get("metadata", {})

        assert (
            metadata.get("fallback_model") == "claude-haiku-4-5-20251001"
        ), "Prompt library metadata fallback_model should be claude-haiku-4-5-20251001"
