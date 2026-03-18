"""
Async AI Client with Retry, Fallback, Concurrency Control, and Multimodal Support

Uses AsyncAnthropic (primary) with Grok fallback via OpenAI-compatible API.
All calls are async with semaphore-based concurrency control.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# Transient HTTP status codes that trigger retry
_TRANSIENT_STATUS_CODES = frozenset({429, 500, 502, 503, 529})


@dataclass
class ImageContent:
    """Image content for multimodal requests."""

    data: str  # base64 or URL
    media_type: str  # image/jpeg, image/png, image/webp
    source_type: str  # "base64" or "url"


@dataclass
class AIResponse:
    """Structured response from AI provider."""

    text: str
    provider: str  # "anthropic" or "grok"
    model: str
    prompt_id: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    json_parsed: dict[str, Any] | None = field(default=None)


class AsyncAIClient:
    """Async AI client with retry, concurrency control, and multimodal support."""

    def __init__(
        self,
        anthropic_api_key: str,
        max_concurrent: int = 10,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        from anthropic import AsyncAnthropic

        self._anthropic = AsyncAnthropic(api_key=anthropic_api_key)
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate(
        self,
        *,
        prompt_id: str,
        system: str,
        messages: list[dict[str, Any]],
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        json_mode: bool = False,
        images: list[ImageContent] | None = None,
    ) -> AIResponse | None:
        """Generate completion with retry and logging.

        Returns None when provider fails (signals rule-based fallback).
        """
        async with self._semaphore:
            response = await self._call_anthropic(
                prompt_id=prompt_id,
                system=system,
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                json_mode=json_mode,
                images=images,
            )

            if response is None:
                logger.warning("anthropic_failed", prompt_id=prompt_id)

            return response

    async def close(self) -> None:
        """Close HTTP connection pools."""
        await self._anthropic.close()

    # ------------------------------------------------------------------
    # Anthropic provider
    # ------------------------------------------------------------------

    async def _call_anthropic(
        self,
        *,
        prompt_id: str,
        system: str,
        messages: list[dict[str, Any]],
        model: str,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
        images: list[ImageContent] | None,
    ) -> AIResponse | None:
        import anthropic

        # Build system prompt — for JSON mode, prepend instruction
        effective_system = system
        if json_mode:
            effective_system = (
                "You must respond with valid JSON only. No markdown, no explanation, "
                "just a JSON object.\n\n" + system
            )

        # Build messages with image content blocks if provided
        effective_messages = self._build_anthropic_messages(messages, images)

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            start = time.perf_counter()
            try:
                raw = await asyncio.wait_for(
                    self._anthropic.messages.create(
                        model=model,
                        max_tokens=max_tokens,
                        temperature=temperature,
                        system=effective_system,
                        messages=effective_messages,  # type: ignore[arg-type]
                    ),
                    timeout=self._timeout_seconds,
                )
                latency_ms = (time.perf_counter() - start) * 1000

                first_block = raw.content[0]
                text = first_block.text if hasattr(first_block, "text") else ""
                input_tokens = raw.usage.input_tokens
                output_tokens = raw.usage.output_tokens

                json_parsed = None
                if json_mode:
                    json_parsed = self._parse_json_response(text, prompt_id)

                response = AIResponse(
                    text=text,
                    provider="anthropic",
                    model=model,
                    prompt_id=prompt_id,
                    latency_ms=latency_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    json_parsed=json_parsed,
                )

                logger.info(
                    "ai_call_success",
                    provider="anthropic",
                    prompt_id=prompt_id,
                    latency_ms=round(latency_ms, 2),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    success=True,
                )
                return response

            except TimeoutError:
                latency_ms = (time.perf_counter() - start) * 1000
                logger.warning(
                    "ai_call_timeout",
                    provider="anthropic",
                    prompt_id=prompt_id,
                    latency_ms=round(latency_ms, 2),
                    attempt=attempt + 1,
                    success=False,
                )
                last_error = TimeoutError()
                # Timeouts are transient — retry
                if attempt < self._max_retries:
                    await asyncio.sleep(2**attempt)
                continue

            except anthropic.APIStatusError as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                last_error = exc
                if exc.status_code in _TRANSIENT_STATUS_CODES:
                    logger.warning(
                        "ai_call_transient_error",
                        provider="anthropic",
                        prompt_id=prompt_id,
                        latency_ms=round(latency_ms, 2),
                        status_code=exc.status_code,
                        attempt=attempt + 1,
                        success=False,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(2**attempt)
                    continue
                else:
                    # Non-transient error — don't retry
                    logger.error(
                        "ai_call_failed",
                        provider="anthropic",
                        prompt_id=prompt_id,
                        latency_ms=round(latency_ms, 2),
                        status_code=exc.status_code,
                        success=False,
                    )
                    break

            except Exception as exc:
                latency_ms = (time.perf_counter() - start) * 1000
                last_error = exc
                logger.error(
                    "ai_call_failed",
                    provider="anthropic",
                    prompt_id=prompt_id,
                    latency_ms=round(latency_ms, 2),
                    error=str(exc),
                    success=False,
                )
                break

        logger.warning(
            "anthropic_exhausted",
            prompt_id=prompt_id,
            last_error=str(last_error),
        )
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_anthropic_messages(
        messages: list[dict[str, Any]],
        images: list[ImageContent] | None,
    ) -> list[dict[str, Any]]:
        """Build Anthropic-format messages, injecting image content blocks."""
        if not images:
            return messages

        result: list[dict[str, Any]] = []
        for msg in messages:
            if msg.get("role") == "user":
                content_blocks: list[dict[str, Any]] = []
                # Add image blocks first
                for img in images:
                    content_blocks.append(
                        {
                            "type": "image",
                            "source": {
                                "type": img.source_type,
                                "media_type": img.media_type,
                                "data": img.data,
                            },
                        }
                    )
                # Then add the text content
                if isinstance(msg.get("content"), str):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                elif isinstance(msg.get("content"), list):
                    content_blocks.extend(msg["content"])
                result.append({"role": "user", "content": content_blocks})
            else:
                result.append(msg)
        return result

    @staticmethod
    def _parse_json_response(text: str, prompt_id: str) -> dict[str, Any] | None:
        """Parse JSON from AI response, handling markdown fences and truncation.

        Strategies (in order):
        1. Direct json.loads
        2. Strip markdown code fences (```json ... ```)
        3. Strip opening fence only (truncated response missing closing ```)
        4. Attempt to repair truncated JSON by closing open brackets/braces
        """
        import re

        # Strategy 1: Direct parse
        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            pass

        stripped = text.strip()

        # Strategy 2: Strip complete markdown fences
        fence_stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
        fence_stripped = re.sub(r"\n?```\s*$", "", fence_stripped)
        if fence_stripped != stripped:
            try:
                result = json.loads(fence_stripped)
                logger.info(
                    "json_parse_recovered",
                    prompt_id=prompt_id,
                    strategy="strip_fences",
                )
                return result  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass
            # Use fence_stripped for subsequent strategies
            stripped = fence_stripped

        # Strategy 3: Strip opening fence only (truncated — no closing ```)
        if stripped.startswith("```"):
            opening_stripped = re.sub(r"^```(?:json)?\s*\n?", "", stripped)
            try:
                result = json.loads(opening_stripped)
                logger.info(
                    "json_parse_recovered",
                    prompt_id=prompt_id,
                    strategy="strip_opening_fence",
                )
                return result  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                stripped = opening_stripped

        # Strategy 4: Repair truncated JSON by closing open brackets/braces
        # This handles the case where max_tokens cut off the response mid-JSON
        repaired = stripped.rstrip()
        # Remove trailing comma if present (common truncation artifact)
        repaired = re.sub(r",\s*$", "", repaired)
        # Count open vs close brackets
        open_braces = repaired.count("{") - repaired.count("}")
        open_brackets = repaired.count("[") - repaired.count("]")
        if open_braces > 0 or open_brackets > 0:
            # Close any open strings (if truncated mid-string)
            if repaired.count('"') % 2 != 0:
                repaired += '"'
            # Remove trailing incomplete key-value pair
            repaired = re.sub(r',\s*"[^"]*"?\s*:?\s*"?[^"]*$', "", repaired)
            # Close brackets and braces
            repaired += "]" * open_brackets
            repaired += "}" * open_braces
            try:
                result = json.loads(repaired)
                logger.info(
                    "json_parse_recovered",
                    prompt_id=prompt_id,
                    strategy="repair_truncated",
                    added_braces=open_braces,
                    added_brackets=open_brackets,
                )
                return result  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                pass

        logger.warning(
            "json_parse_failed",
            prompt_id=prompt_id,
            text_preview=text[:200],
        )
        return None
