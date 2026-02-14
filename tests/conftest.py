"""
Pytest Configuration and Fixtures

Shared test fixtures for unit and integration tests.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from gapsense.core.models.base import Base


@pytest.fixture
async def async_engine():
    """Create async engine for testing."""
    engine = create_async_engine(
        "postgresql+asyncpg://gapsense:localdev@localhost:5432/gapsense_test",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def db_session(async_engine) -> AsyncSession:
    """Create database session for testing."""
    async_session = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()
