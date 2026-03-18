"""
Embedding Job — Generate and store embeddings for curriculum indicators.

Standalone async job that runs at curriculum import time to pre-compute
indicator-level embeddings for vector search.

CLI: python -m gapsense.jobs.embedding_job --country GH --subject mathematics [--force-refresh]
"""

from __future__ import annotations

import argparse
import asyncio
import time
from dataclasses import dataclass
from typing import Any

import structlog
from sqlalchemy import func, select, text
from sqlalchemy.orm import selectinload

from gapsense.ai.embedding_service import EmbeddingService
from gapsense.config import settings
from gapsense.core.exceptions import ConfigurationError
from gapsense.core.models.curriculum import (
    CurriculumIndicator,
    CurriculumNode,
)

logger = structlog.get_logger(__name__)


@dataclass
class EmbeddingJobResult:
    """Summary of an embedding job run."""

    country: str
    subject: str
    total_indicators: int
    newly_embedded: int
    already_embedded: int
    errors: int
    duration_seconds: float


async def run_embedding_job(
    country: str,
    subject: str,
    force_refresh: bool = False,
    *,
    session_factory: Any = None,
    embedding_service: EmbeddingService | None = None,
) -> EmbeddingJobResult:
    """Generate and store embeddings for all curriculum indicators.

    Steps:
    1. Validate embedding model consistency (abort if mismatch without force_refresh)
    2. Query indicators where embedding IS NULL (or all if force_refresh)
    3. Build indicator chunks via EmbeddingService.build_indicator_chunk
    4. Call EmbeddingService.embed_batch
    5. Write vectors + model name back to DB
    6. Create IVFFlat index if >= 100 vectors exist
    7. Return EmbeddingJobResult summary

    Args:
        country: ISO country code (e.g., "GH").
        subject: Subject name (e.g., "mathematics").
        force_refresh: If True, overwrite existing embeddings.
        session_factory: Optional async session factory (for testing).
        embedding_service: Optional pre-constructed EmbeddingService (for testing).
    """
    start_time = time.monotonic()

    # Create DB session and embedding service if not injected
    if session_factory is None:
        from gapsense.core.database import AsyncSessionLocal

        session_factory = AsyncSessionLocal

    if embedding_service is None:
        embedding_service = EmbeddingService(settings)

    async with session_factory() as session:
        # Step 1: Count total indicators for this country/subject
        total_count_query = (
            select(func.count(CurriculumIndicator.id))
            .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
            .where(CurriculumNode.country == country, CurriculumNode.subject == subject)
        )
        total_result = await session.execute(total_count_query)
        total_indicators = total_result.scalar_one()

        if total_indicators == 0:
            logger.warning(
                "embedding_job_no_indicators",
                country=country,
                subject=subject,
            )
            duration = time.monotonic() - start_time
            return EmbeddingJobResult(
                country=country,
                subject=subject,
                total_indicators=0,
                newly_embedded=0,
                already_embedded=0,
                errors=0,
                duration_seconds=round(duration, 2),
            )

        # Step 2: Validate embedding model consistency
        if not force_refresh:
            existing_model_query = (
                select(CurriculumIndicator.embedding_model)
                .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
                .where(
                    CurriculumNode.country == country,
                    CurriculumNode.subject == subject,
                    CurriculumIndicator.embedding.isnot(None),
                )
                .distinct()
            )
            existing_result = await session.execute(existing_model_query)
            existing_models = [row[0] for row in existing_result.fetchall() if row[0] is not None]

            for model in existing_models:
                if model != embedding_service.model_name:
                    error_msg = (
                        f"Embedding model mismatch: existing embeddings use '{model}' "
                        f"but current backend is '{embedding_service.model_name}'. "
                        f"Run with --force-refresh to re-embed all indicators."
                    )
                    logger.error("embedding_model_mismatch", error=error_msg)
                    raise ConfigurationError(error_msg)

        # Step 3: Query indicators to embed
        indicators_query = (
            select(CurriculumIndicator)
            .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
            .options(
                selectinload(CurriculumIndicator.node),
                selectinload(CurriculumIndicator.error_patterns),
            )
            .where(CurriculumNode.country == country, CurriculumNode.subject == subject)
        )

        if not force_refresh:
            indicators_query = indicators_query.where(CurriculumIndicator.embedding.is_(None))

        indicators_result = await session.execute(indicators_query)
        indicators_to_embed = list(indicators_result.scalars().all())

        already_embedded = total_indicators - len(indicators_to_embed)
        if force_refresh:
            already_embedded = 0

        if not indicators_to_embed:
            logger.info(
                "embedding_job_all_embedded",
                country=country,
                subject=subject,
                total_indicators=total_indicators,
            )
            duration = time.monotonic() - start_time
            return EmbeddingJobResult(
                country=country,
                subject=subject,
                total_indicators=total_indicators,
                newly_embedded=0,
                already_embedded=already_embedded,
                errors=0,
                duration_seconds=round(duration, 2),
            )

        # Step 4: Build indicator chunks
        chunks: list[str] = []
        for indicator in indicators_to_embed:
            node = indicator.node
            error_pattern_texts = [ep.error_description for ep in indicator.error_patterns]
            chunk = EmbeddingService.build_indicator_chunk(
                node_code=node.code,
                node_title=node.title,
                indicator_code=indicator.indicator_code,
                indicator_title=indicator.title,
                error_patterns=error_pattern_texts,
            )
            chunks.append(chunk)

        # Step 5: Embed batch and write back to DB
        newly_embedded = 0
        errors = 0

        try:
            embeddings = await embedding_service.embed_batch(chunks)
        except Exception:
            logger.exception(
                "embedding_batch_failed",
                country=country,
                subject=subject,
                batch_size=len(chunks),
            )
            duration = time.monotonic() - start_time
            return EmbeddingJobResult(
                country=country,
                subject=subject,
                total_indicators=total_indicators,
                newly_embedded=0,
                already_embedded=already_embedded,
                errors=len(indicators_to_embed),
                duration_seconds=round(duration, 2),
            )

        for indicator, embedding_vector in zip(indicators_to_embed, embeddings, strict=False):
            try:
                indicator.embedding = embedding_vector
                indicator.embedding_model = embedding_service.model_name
                newly_embedded += 1
            except Exception:
                logger.exception(
                    "embedding_write_failed",
                    indicator_id=str(indicator.id),
                )
                errors += 1

        await session.commit()

        logger.info(
            "embedding_job_completed",
            country=country,
            subject=subject,
            total_indicators=total_indicators,
            newly_embedded=newly_embedded,
            already_embedded=already_embedded,
            errors=errors,
        )

        # Step 6: Create IVFFlat index if enough vectors exist
        await _maybe_create_ivfflat_index(session, country, subject)

    duration = time.monotonic() - start_time
    return EmbeddingJobResult(
        country=country,
        subject=subject,
        total_indicators=total_indicators,
        newly_embedded=newly_embedded,
        already_embedded=already_embedded,
        errors=errors,
        duration_seconds=round(duration, 2),
    )


IVFFLAT_MIN_VECTORS = 100
IVFFLAT_INDEX_NAME = "idx_curriculum_indicators_embedding"


async def _maybe_create_ivfflat_index(session: Any, country: str, subject: str) -> None:
    """Create IVFFlat index if enough non-null embeddings exist.

    Checks count of non-null embeddings for the country/subject.
    If >= 100: creates the index (IF NOT EXISTS).
    If < 100: skips and logs a warning.
    """
    count_query = (
        select(func.count(CurriculumIndicator.id))
        .join(CurriculumNode, CurriculumIndicator.node_id == CurriculumNode.id)
        .where(
            CurriculumNode.country == country,
            CurriculumNode.subject == subject,
            CurriculumIndicator.embedding.isnot(None),
        )
    )
    count_result = await session.execute(count_query)
    embedding_count = count_result.scalar_one()

    if embedding_count < IVFFLAT_MIN_VECTORS:
        logger.warning(
            "ivfflat_index_skipped",
            country=country,
            subject=subject,
            embedding_count=embedding_count,
            minimum_required=IVFFLAT_MIN_VECTORS,
            message=(
                f"Skipping IVFFlat index creation: {embedding_count} embeddings "
                f"found, minimum {IVFFLAT_MIN_VECTORS} required."
            ),
        )
        return

    create_index_sql = text(
        f"CREATE INDEX IF NOT EXISTS {IVFFLAT_INDEX_NAME} "
        f"ON curriculum_indicators USING ivfflat (embedding vector_cosine_ops) "
        f"WITH (lists = 100)"
    )

    try:
        await session.execute(create_index_sql)
        await session.commit()
        logger.info(
            "ivfflat_index_created",
            country=country,
            subject=subject,
            embedding_count=embedding_count,
        )
    except Exception:
        logger.exception(
            "ivfflat_index_creation_failed",
            country=country,
            subject=subject,
        )


def main() -> None:
    """CLI entry point for the embedding job."""
    parser = argparse.ArgumentParser(
        description="Generate and store embeddings for curriculum indicators.",
    )
    parser.add_argument(
        "--country",
        required=True,
        help="ISO country code (e.g., GH, UG, KE, NG)",
    )
    parser.add_argument(
        "--subject",
        required=True,
        help="Subject name (e.g., mathematics)",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        default=False,
        help="Overwrite existing embeddings",
    )

    args = parser.parse_args()

    result = asyncio.run(
        run_embedding_job(
            country=args.country,
            subject=args.subject,
            force_refresh=args.force_refresh,
        )
    )

    print("Embedding job completed:")
    print(f"  Country: {result.country}")
    print(f"  Subject: {result.subject}")
    print(f"  Total indicators: {result.total_indicators}")
    print(f"  Newly embedded: {result.newly_embedded}")
    print(f"  Already embedded: {result.already_embedded}")
    print(f"  Errors: {result.errors}")
    print(f"  Duration: {result.duration_seconds:.2f}s")


if __name__ == "__main__":
    main()
