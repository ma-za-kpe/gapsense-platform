"""
AI Cost Calculator

Calculates costs for AI API calls based on token usage and provider pricing.
Pricing accurate as of March 2026.
"""

from decimal import Decimal

# Pricing per million tokens (MTok) as of March 2026
# Source: https://platform.claude.com/docs/en/about-claude/pricing
ANTHROPIC_PRICING = {
    "claude-opus-4-20250514": {
        "input": Decimal("5.00"),  # $5/MTok
        "output": Decimal("25.00"),  # $25/MTok
    },
    "claude-sonnet-4-20250514": {
        "input": Decimal("3.00"),  # $3/MTok
        "output": Decimal("15.00"),  # $15/MTok
    },
    "claude-3-7-sonnet-20250219": {
        "input": Decimal("3.00"),  # $3/MTok
        "output": Decimal("15.00"),  # $15/MTok
    },
    "claude-3-5-sonnet-20241022": {
        "input": Decimal("3.00"),  # $3/MTok
        "output": Decimal("15.00"),  # $15/MTok
    },
    "claude-haiku-4-5": {
        "input": Decimal("1.00"),  # $1/MTok
        "output": Decimal("5.00"),  # $5/MTok
    },
    "claude-3-5-haiku-20241022": {
        "input": Decimal("1.00"),  # $1/MTok (deprecated Feb 2026)
        "output": Decimal("5.00"),  # $5/MTok
    },
    "claude-3-haiku-20240307": {
        "input": Decimal("0.25"),  # $0.25/MTok
        "output": Decimal("1.25"),  # $1.25/MTok
    },
}


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> tuple[Decimal, Decimal, Decimal]:
    """Calculate AI API call cost.

    Args:
        provider: "anthropic"
        model: Model name (e.g., "claude-haiku-4-5")
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Tuple of (input_cost, output_cost, total_cost) in USD

    Example:
        >>> calculate_cost("anthropic", "claude-haiku-4-5", 2000, 5000)
        (Decimal('0.002000'), Decimal('0.025000'), Decimal('0.027000'))
    """
    # Get pricing for model
    pricing = ANTHROPIC_PRICING.get(model) if provider == "anthropic" else None

    if not pricing:
        # Unknown model - return zero cost
        return Decimal("0.00"), Decimal("0.00"), Decimal("0.00")

    # Convert tokens to millions and calculate cost
    input_cost = (Decimal(input_tokens) / Decimal("1000000")) * pricing["input"]
    output_cost = (Decimal(output_tokens) / Decimal("1000000")) * pricing["output"]
    total_cost = input_cost + output_cost

    return input_cost, output_cost, total_cost


def estimate_image_tokens(width: int = 1000, height: int = 1000) -> int:
    """Estimate tokens for an image.

    Claude uses ~1,334 tokens for a 1000×1000 pixel image.
    Actual token count may vary based on content complexity.

    Args:
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Estimated token count

    Example:
        >>> estimate_image_tokens(1000, 1000)
        1334
        >>> estimate_image_tokens(2000, 2000)
        5336
    """
    # Base: ~1334 tokens for 1000x1000 image
    base_tokens = 1334
    base_pixels = 1000 * 1000

    # Scale linearly with pixel count
    pixels = width * height
    return int((pixels / base_pixels) * base_tokens)


def format_cost(cost_usd: Decimal) -> str:
    """Format cost for display.

    Args:
        cost_usd: Cost in USD

    Returns:
        Formatted cost string

    Example:
        >>> format_cost(Decimal("0.027"))
        '$0.03'
        >>> format_cost(Decimal("1.234567"))
        '$1.23'
    """
    return f"${cost_usd:.2f}"
