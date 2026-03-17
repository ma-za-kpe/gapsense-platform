"""
EmbeddingService for generating vector embeddings from text.

Supports two backends:
- OpenAI text-embedding-3-small (1536 dimensions) for production
- sentence-transformers all-MiniLM-L6-v2 (384 dimensions) for development

Backend is fixed at construction time and never switches during lifetime.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

import structlog

if TYPE_CHECKING:
    from gapsense.config import Settings

logger = structlog.get_logger(__name__)


class EmbeddingService:
    """Generates vector embeddings from text using a configurable backend.

    Backend is fixed at construction time and never switches during lifetime.
    """

    # Model name constants
    OPENAI_MODEL_NAME = "openai-text-embedding-3-small"
    MINILM_MODEL_NAME = "minilm-all-MiniLM-L6-v2"

    # Dimensionality constants
    OPENAI_DIMENSIONS = 1536
    MINILM_DIMENSIONS = 384

    # OpenAI batch size limit
    OPENAI_BATCH_SIZE = 100

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 1.0

    def __init__(self, settings: Settings) -> None:
        """Construct with backend from settings.EMBEDDING_MODEL.

        Args:
            settings: Application settings containing EMBEDDING_MODEL and OPENAI_API_KEY.

        Raises:
            ConfigurationError: If backend is 'openai' and OPENAI_API_KEY is not set.
        """
        from gapsense.core.exceptions import ConfigurationError

        self._backend: Literal["openai", "minilm"] = settings.EMBEDDING_MODEL

        if self._backend == "openai":
            if not settings.OPENAI_API_KEY:
                raise ConfigurationError(
                    "OPENAI_API_KEY is required when EMBEDDING_MODEL is 'openai'. "
                    "Set OPENAI_API_KEY in your environment or use EMBEDDING_MODEL='minilm' "
                    "for local development."
                )
            self._openai_api_key = settings.OPENAI_API_KEY
            self._openai_client: openai.AsyncOpenAI | None = None
        else:
            # MiniLM backend - lazy load the model
            self._minilm_model: SentenceTransformer | None = None

    @property
    def model_name(self) -> str:
        """Return canonical model name for the embedding_model column.

        Returns:
            'openai-text-embedding-3-small' or 'minilm-all-MiniLM-L6-v2'
        """
        if self._backend == "openai":
            return self.OPENAI_MODEL_NAME
        return self.MINILM_MODEL_NAME

    @property
    def dimensions(self) -> int:
        """Return vector dimensionality: 1536 (OpenAI) or 384 (MiniLM)."""
        if self._backend == "openai":
            return self.OPENAI_DIMENSIONS
        return self.MINILM_DIMENSIONS

    def _get_openai_client(self) -> openai.AsyncOpenAI:
        """Lazy-initialize and return the OpenAI async client."""
        if self._openai_client is None:
            import openai

            self._openai_client = openai.AsyncOpenAI(api_key=self._openai_api_key)
        return self._openai_client

    def _get_minilm_model(self) -> SentenceTransformer:
        """Lazy-initialize and return the MiniLM model."""
        if self._minilm_model is None:
            from sentence_transformers import SentenceTransformer

            self._minilm_model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._minilm_model

    async def embed(self, text: str) -> list[float]:
        """Return a single embedding vector for the given text.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        if self._backend == "openai":
            return await self._embed_openai_single(text)
        return await self._embed_minilm_single(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts efficiently.

        OpenAI calls are batched in groups of 100.
        Retries with exponential backoff up to 3 attempts on rate-limit errors.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        if self._backend == "openai":
            return await self._embed_openai_batch(texts)
        return await self._embed_minilm_batch(texts)

    async def _embed_openai_single(self, text: str) -> list[float]:
        """Embed a single text using OpenAI API with retry logic."""
        result = await self._embed_openai_batch([text])
        return result[0]

    async def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts using OpenAI API with batching and retry logic."""

        client = self._get_openai_client()
        all_embeddings: list[list[float]] = []

        # Process in batches of OPENAI_BATCH_SIZE
        for i in range(0, len(texts), self.OPENAI_BATCH_SIZE):
            batch = texts[i : i + self.OPENAI_BATCH_SIZE]
            batch_embeddings = await self._embed_openai_batch_with_retry(client, batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def _embed_openai_batch_with_retry(
        self, client: openai.AsyncOpenAI, texts: list[str]
    ) -> list[list[float]]:
        """Embed a batch with exponential backoff retry on rate-limit errors."""
        import openai

        backoff = self.INITIAL_BACKOFF_SECONDS

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await client.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts,
                )
                # Sort by index to ensure correct ordering
                sorted_data = sorted(response.data, key=lambda x: x.index)
                return [item.embedding for item in sorted_data]

            except openai.RateLimitError as e:
                if attempt == self.MAX_RETRIES - 1:
                    # Last attempt, re-raise
                    logger.error(
                        "openai_rate_limit_exhausted",
                        attempts=self.MAX_RETRIES,
                        error=str(e),
                    )
                    raise

                logger.warning(
                    "openai_rate_limit_retry",
                    attempt=attempt + 1,
                    max_retries=self.MAX_RETRIES,
                    backoff_seconds=backoff,
                )
                await asyncio.sleep(backoff)
                backoff *= 2  # Exponential backoff

        # Should never reach here, but satisfy type checker
        raise RuntimeError("Unexpected exit from retry loop")  # pragma: no cover

    async def _embed_minilm_single(self, text: str) -> list[float]:
        """Embed a single text using MiniLM model."""
        result = await self._embed_minilm_batch([text])
        return result[0]

    async def _embed_minilm_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts using MiniLM model.

        Runs the model in a thread pool to avoid blocking the event loop.
        """
        model = self._get_minilm_model()

        # Run in thread pool since sentence-transformers is synchronous
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(texts, convert_to_numpy=True).tolist(),
        )
        return embeddings

    @staticmethod
    def build_indicator_chunk(
        node_code: str,
        node_title: str,
        indicator_code: str,
        indicator_title: str,
        error_patterns: list[str],
    ) -> str:
        """Build deterministic indicator chunk text for embedding.

        Format:
            Curriculum node: {node_code} — {node_title}
            Indicator: {indicator_code} — {indicator_title}
            Common errors: {ep1}; {ep2}; {ep3}

        Args:
            node_code: The curriculum node code (e.g., "B4.1.3.1").
            node_title: The curriculum node title.
            indicator_code: The indicator code.
            indicator_title: The indicator title.
            error_patterns: List of common error pattern descriptions.

        Returns:
            A deterministic string suitable for embedding.
        """
        error_patterns_str = "; ".join(error_patterns) if error_patterns else ""

        return (
            f"Curriculum node: {node_code} — {node_title}\n"
            f"Indicator: {indicator_code} — {indicator_title}\n"
            f"Common errors: {error_patterns_str}"
        )
