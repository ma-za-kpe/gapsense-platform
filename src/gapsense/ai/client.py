"""
Unified AI Client with Provider Fallback

Attempts providers in order: Anthropic → Grok → None (triggers rule-based)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


class AIClient:
    """Unified AI client that tries multiple providers in order."""

    def __init__(self, *, anthropic_api_key: str | None = None, grok_api_key: str | None = None):
        """Initialize AI client with available API keys.

        Args:
            anthropic_api_key: Anthropic Claude API key (priority 1)
            grok_api_key: xAI Grok API key (priority 2)
        """
        self.anthropic_api_key = anthropic_api_key
        self.grok_api_key = grok_api_key

    def generate_completion(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[dict[str, str]],
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> str | None:
        """Generate completion using available AI provider.

        Tries providers in order:
        1. Anthropic Claude API (if key available)
        2. xAI Grok API (if key available)
        3. Returns None (triggers rule-based fallback)

        Args:
            model: Model identifier (will be adapted per provider)
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum response tokens
            temperature: Sampling temperature

        Returns:
            Generated text response, or None if all providers failed
        """
        # Try Anthropic first
        if self.anthropic_api_key:
            result = self._try_anthropic(
                model=model,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if result is not None:
                logger.info("AI completion successful via Anthropic")
                return result

        # Fallback to Grok
        if self.grok_api_key:
            result = self._try_grok(
                model=model,
                system=system,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            if result is not None:
                logger.info("AI completion successful via Grok (fallback)")
                return result

        # All providers failed
        logger.warning("All AI providers failed or unavailable, falling back to rule-based")
        return None

    def _try_anthropic(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        """Try Anthropic Claude API.

        Args:
            model: Model identifier
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum response tokens
            temperature: Sampling temperature

        Returns:
            Generated text or None on error
        """
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=self.anthropic_api_key)

            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system,
                messages=list(messages),  # type: ignore[arg-type]  # Convert to list for Anthropic
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, "text"):
                    return content_block.text

            logger.warning("Anthropic response had no text content")
            return None

        except Exception as e:
            logger.warning(f"Anthropic API error: {e}")
            return None

    def _try_grok(
        self,
        *,
        model: str,
        system: str,
        messages: Sequence[dict[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> str | None:
        """Try xAI Grok API (OpenAI-compatible).

        Args:
            model: Model identifier (will use grok-beta)
            system: System prompt
            messages: Conversation messages
            max_tokens: Maximum response tokens
            temperature: Sampling temperature

        Returns:
            Generated text or None on error
        """
        try:
            from openai import OpenAI

            # Grok uses OpenAI-compatible API
            client = OpenAI(
                api_key=self.grok_api_key,
                base_url="https://api.x.ai/v1",  # xAI endpoint
            )

            # Convert messages to OpenAI format (add system message)
            openai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
            openai_messages.extend(messages)

            response = client.chat.completions.create(
                model="grok-3",  # Use Grok 3 model regardless of input model
                messages=openai_messages,  # type: ignore[arg-type]
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Extract text from response
            if response.choices and len(response.choices) > 0:
                return response.choices[0].message.content

            logger.warning("Grok response had no content")
            return None

        except Exception as e:
            logger.warning(f"Grok API error: {e}")
            return None


def get_ai_client() -> AIClient:
    """Get configured AI client instance.

    Returns:
        AIClient with available API keys from settings
    """
    from gapsense.config import settings

    return AIClient(
        anthropic_api_key=settings.ANTHROPIC_API_KEY or None,
        grok_api_key=settings.GROK_API_KEY or None,
    )
