"""
Pytest Configuration and Fixtures

Shared test fixtures for unit and integration tests.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import configure_mappers, sessionmaker

from gapsense.core.models import (  # noqa: F401 - imported for SQLAlchemy registration
    Base,
    CurriculumNode,
    CurriculumStrand,
    CurriculumSubStrand,
    Parent,
    Student,
    Teacher,
)

# Ensure all mappers are configured
configure_mappers()


@pytest.fixture
async def async_engine():
    """Create async engine for testing."""
    import os

    # Use DATABASE_URL from environment (set in CI) or default to local
    database_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://gapsense:localdev@localhost:5433/gapsense_test"
    )
    engine = create_async_engine(database_url, echo=False)

    # Drop and recreate all tables
    async with engine.begin() as conn:
        # Drop all tables using CASCADE to ignore circular dependencies
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        # Now create all tables with new schema
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncSession:
    """Create database session for testing."""
    # Truncate all tables before each test (faster than drop/create)
    async_session = sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Truncate all tables (ignore circular dependencies)
        try:
            for table in reversed(Base.metadata.sorted_tables):
                await session.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
            await session.commit()
        except Exception:
            # If truncate fails, just continue (tables may not exist yet)
            await session.rollback()

        # Seed default region and district (required for teacher/student creation)
        try:
            await session.execute(
                text(
                    """
                    INSERT INTO regions (id, name, code)
                    VALUES (1, 'Greater Accra', 'GAR')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )
            await session.execute(
                text(
                    """
                    INSERT INTO districts (id, region_id, name, ges_district_code)
                    VALUES (1, 1, 'Accra Metropolitan', 'GAR-AM-001')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )
            await session.commit()
        except Exception:
            await session.rollback()

        yield session
