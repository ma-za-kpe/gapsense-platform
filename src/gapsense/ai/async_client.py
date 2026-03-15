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
    """Async AI client with retry, fallback, concurrency control, and multimodal support."""

    def __init__(
        self,
        anthropic_api_key: str,
        grok_api_key: str | None = None,
        max_concurrent: int = 10,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        from anthropic import AsyncAnthropic

        self._anthropic = AsyncAnthropic(api_key=anthropic_api_key)
        self._grok_api_key = grok_api_key
        self._grok_client: Any | None = None
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
        model: str = "claude-sonnet-4-5-20250929",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        json_mode: bool = False,
        images: list[ImageContent] | None = None,
    ) -> AIResponse | None:
        """Generate completion with retry, fallback, and logging.

        Returns None when all providers fail (signals rule-based fallback).
        """
        async with self._semaphore:
            # Try Anthropic first
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
            if response is not None:
                return response

            # Fallback to Grok
            if self._grok_api_key:
                response = await self._call_grok(
                    prompt_id=prompt_id,
                    system=system,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    json_mode=json_mode,
                )
                if response is not None:
                    return response

            logger.warning(
                "all_providers_failed",
                prompt_id=prompt_id,
            )
            return None

    async def close(self) -> None:
        """Close HTTP connection pools."""
        await self._anthropic.close()
        if self._grok_client is not None:
            await self._grok_client.close()

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
                        messages=effective_messages,
                    ),
                    timeout=self._timeout_seconds,
                )
                latency_ms = (time.perf_counter() - start) * 1000

                text = raw.content[0].text if raw.content else ""
                input_tokens = raw.usage.input_tokens
                output_tokens = raw.usage.output_tokens

                json_parsed = None
                if json_mode:
                    try:
                        json_parsed = json.loads(text)
                    except json.JSONDecodeError:
                        logger.warning(
                            "json_parse_failed",
                            provider="anthropic",
                            prompt_id=prompt_id,
                        )

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
    # Grok fallback provider
    # ------------------------------------------------------------------

    async def _call_grok(
        self,
        *,
        prompt_id: str,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> AIResponse | None:
        if self._grok_client is None:
            from openai import AsyncOpenAI

            self._grok_client = AsyncOpenAI(
                api_key=self._grok_api_key,
                base_url="https://api.x.ai/v1",
            )

        openai_messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        openai_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": "grok-3",
            "messages": openai_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        start = time.perf_counter()
        try:
            raw = await asyncio.wait_for(
                self._grok_client.chat.completions.create(**kwargs),
                timeout=self._timeout_seconds,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            text = raw.choices[0].message.content if raw.choices else ""
            input_tokens = raw.usage.prompt_tokens if raw.usage else 0
            output_tokens = raw.usage.completion_tokens if raw.usage else 0

            json_parsed = None
            if json_mode and text:
                try:
                    json_parsed = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning(
                        "json_parse_failed",
                        provider="grok",
                        prompt_id=prompt_id,
                    )

            response = AIResponse(
                text=text or "",
                provider="grok",
                model="grok-3",
                prompt_id=prompt_id,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                json_parsed=json_parsed,
            )

            logger.info(
                "ai_call_success",
                provider="grok",
                prompt_id=prompt_id,
                latency_ms=round(latency_ms, 2),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                success=True,
            )
            return response

        except Exception as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "ai_call_failed",
                provider="grok",
                prompt_id=prompt_id,
                latency_ms=round(latency_ms, 2),
                error=str(exc),
                success=False,
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
