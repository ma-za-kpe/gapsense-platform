#!/usr/bin/env python3
"""
Load curriculum data into database.

Runs CurriculumLoader to populate curriculum_nodes from gapsense-data/curricula/
"""

import asyncio

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from gapsense.config import settings
from gapsense.services.curriculum_loader import CurriculumLoader

logger = structlog.get_logger(__name__)


async def main():
    """Load all curricula."""
    # Create async engine
    engine = create_async_engine(settings.database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session_maker() as session:
        loader = CurriculumLoader(db_session=session, settings=settings)

        logger.info("Loading curriculum data from all countries...")
        summary = await loader.load_all_countries()

        logger.info(
            "Curriculum load complete",
            total_files=summary.total_files,
            nodes_created=summary.total_nodes_created,
            nodes_updated=summary.total_nodes_updated,
            errors=summary.total_errors,
            countries=list(summary.by_country.keys()),
        )

        # Print summary for each country
        for country, country_summary in summary.by_country.items():
            print(f"\n{country.upper()}:")
            print(f"  Files: {country_summary.files}")
            print(f"  Nodes created: {country_summary.nodes_created}")
            print(f"  Nodes updated: {country_summary.nodes_updated}")
            print(f"  Errors: {country_summary.errors}")
            if country_summary.by_subject:
                print(f"  By subject: {country_summary.by_subject}")

        print(
            f"\nTOTAL: {summary.total_nodes_created} created, {summary.total_nodes_updated} updated"
        )

        await session.commit()


if __name__ == "__main__":
    asyncio.run(main())
