"""
Unit tests for AI model string updates.

Verifies that all Python files have been updated to use claude-sonnet-4-6
instead of claude-sonnet-4-5, and that cost_calculator has entries for
the new models.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6
"""

from pathlib import Path


class TestModelStringUpdates:
    """Verify model strings are updated across the codebase."""

    def test_async_client_uses_claude_sonnet_4_6(self):
        """Requirement 8.1: async_client.py default model is claude-sonnet-4-6."""
        from gapsense.ai import async_client

        source = Path(async_client.__file__).read_text()
        assert "claude-sonnet-4-6" in source, "async_client.py should contain claude-sonnet-4-6"
        # Should NOT contain the old model string
        assert (
            "claude-sonnet-4-5-20250929" not in source
        ), "async_client.py should not contain old model claude-sonnet-4-5-20250929"

    def test_prompt_service_uses_claude_sonnet_4_6(self):
        """Requirement 8.2: prompt_service.py fallback model is claude-sonnet-4-6."""
        from gapsense.ai import prompt_service

        source = Path(prompt_service.__file__).read_text()
        assert "claude-sonnet-4-6" in source, "prompt_service.py should contain claude-sonnet-4-6"

    def test_prompt_loader_uses_claude_sonnet_4_6(self):
        """Requirement 8.3: prompt_loader.py fallback model is claude-sonnet-4-6."""
        from gapsense.ai import prompt_loader

        source = Path(prompt_loader.__file__).read_text()
        assert "claude-sonnet-4-6" in source, "prompt_loader.py should contain claude-sonnet-4-6"

    def test_prompts_model_uses_claude_sonnet_4_6(self):
        """Requirement 8.4: models/prompts.py model_target default is claude-sonnet-4-6."""
        from gapsense.core.models import prompts

        source = Path(prompts.__file__).read_text()
        assert "claude-sonnet-4-6" in source, "models/prompts.py should contain claude-sonnet-4-6"

    def test_diagnostics_model_uses_claude_sonnet_4_6(self):
        """Requirement 8.5: models/diagnostics.py model_used comment references claude-sonnet-4-6."""
        from gapsense.core.models import diagnostics

        source = Path(diagnostics.__file__).read_text()
        assert (
            "claude-sonnet-4-6" in source
        ), "models/diagnostics.py should contain claude-sonnet-4-6"

    def test_cost_calculator_has_claude_sonnet_4_6_entry(self):
        """Requirement 8.6: cost_calculator has entry for claude-sonnet-4-6."""
        from gapsense.ai.cost_calculator import ANTHROPIC_PRICING

        assert (
            "claude-sonnet-4-6" in ANTHROPIC_PRICING
        ), "cost_calculator should have claude-sonnet-4-6 pricing entry"
        pricing = ANTHROPIC_PRICING["claude-sonnet-4-6"]
        assert "input" in pricing and "output" in pricing

    def test_cost_calculator_has_claude_haiku_4_5_20251001_entry(self):
        """Requirement 8.6: cost_calculator has entry for claude-haiku-4-5-20251001."""
        from gapsense.ai.cost_calculator import ANTHROPIC_PRICING

        assert (
            "claude-haiku-4-5-20251001" in ANTHROPIC_PRICING
        ), "cost_calculator should have claude-haiku-4-5-20251001 pricing entry"
        pricing = ANTHROPIC_PRICING["claude-haiku-4-5-20251001"]
        assert "input" in pricing and "output" in pricing


class TestCostCalculatorPricing:
    """Verify cost calculator returns correct values for new models."""

    def test_claude_sonnet_4_6_pricing(self):
        """Verify claude-sonnet-4-6 pricing is correct ($3/MTok input, $15/MTok output)."""
        from decimal import Decimal

        from gapsense.ai.cost_calculator import calculate_cost

        input_cost, output_cost, total_cost = calculate_cost(
            provider="anthropic",
            model="claude-sonnet-4-6",
            input_tokens=1000000,  # 1 MTok
            output_tokens=1000000,  # 1 MTok
        )

        assert input_cost == Decimal("3.00"), f"Expected $3.00, got {input_cost}"
        assert output_cost == Decimal("15.00"), f"Expected $15.00, got {output_cost}"
        assert total_cost == Decimal("18.00"), f"Expected $18.00, got {total_cost}"

    def test_claude_haiku_4_5_20251001_pricing(self):
        """Verify claude-haiku-4-5-20251001 pricing is correct ($1/MTok input, $5/MTok output)."""
        from decimal import Decimal

        from gapsense.ai.cost_calculator import calculate_cost

        input_cost, output_cost, total_cost = calculate_cost(
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            input_tokens=1000000,  # 1 MTok
            output_tokens=1000000,  # 1 MTok
        )

        assert input_cost == Decimal("1.00"), f"Expected $1.00, got {input_cost}"
        assert output_cost == Decimal("5.00"), f"Expected $5.00, got {output_cost}"
        assert total_cost == Decimal("6.00"), f"Expected $6.00, got {total_cost}"
