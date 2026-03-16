"""
Pytest Configuration and Fixtures

Shared test fixtures for unit and integration tests.
Includes custom Hypothesis strategies for domain types.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from hypothesis import strategies as st
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


# ============================================================================
# Database Fixtures
# ============================================================================


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

        # Reset all sequences to ensure clean state
        try:
            # Get all sequences and reset them
            sequences_query = text("""
                SELECT sequence_name
                FROM information_schema.sequences
                WHERE sequence_schema = 'public'
            """)
            result = await session.execute(sequences_query)
            sequences = result.fetchall()

            for (seq_name,) in sequences:
                await session.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1"))

            await session.commit()
        except Exception:
            # If sequence reset fails, just continue
            await session.rollback()

        # Seed default region and district for MVP teacher onboarding
        # This matches the production seed migration
        # Uses unique names that won't conflict with test-created regions
        try:
            await session.execute(
                text("""
                INSERT INTO regions (id, name, code)
                VALUES (1, 'Default Seed Region', 'DSR')
                ON CONFLICT (id) DO NOTHING;
            """)
            )
            await session.execute(
                text("""
                INSERT INTO districts (id, region_id, name, ges_district_code)
                VALUES (1, 1, 'Default Seed District', 'DSR-DS-001')
                ON CONFLICT (id) DO NOTHING;
            """)
            )
            # Advance sequences past seeded IDs to avoid collisions
            await session.execute(
                text("SELECT setval('regions_id_seq', GREATEST(nextval('regions_id_seq'), 2))")
            )
            await session.execute(
                text("SELECT setval('districts_id_seq', GREATEST(nextval('districts_id_seq'), 2))")
            )
            await session.commit()
        except Exception:
            await session.rollback()

        yield session


@pytest.fixture
async def async_client() -> AsyncClient:
    """Create async HTTP client for testing FastAPI endpoints."""
    from httpx import ASGITransport

    from gapsense.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def region_district_school(db_session: AsyncSession):
    """Create Region → District → School hierarchy for tests.

    Fixes foreign key errors by providing proper geographic hierarchy.
    Returns tuple of (region, district, school) for test use.
    """
    from gapsense.core.models import District, Region, School

    # Create region (root of hierarchy)
    region = Region(
        name="Greater Accra",
        code="GAR",
    )
    db_session.add(region)
    await db_session.flush()

    # Create district in that region
    district = District(
        name="Test District",
        region_id=region.id,
    )
    db_session.add(district)
    await db_session.flush()

    # Create school in that district
    school = School(
        name="Test School",
        district_id=district.id,
        school_type="jhs",
        is_active=True,
    )
    db_session.add(school)
    await db_session.flush()

    await db_session.commit()
    await db_session.refresh(region)
    await db_session.refresh(district)
    await db_session.refresh(school)

    return region, district, school


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================

# Strategy for generating CountryConfig instances
country_config_st = st.fixed_dictionaries(
    {
        "country_code": st.sampled_from(["GH", "UG", "KE", "NG"]),
        "country_name": st.sampled_from(["Ghana", "Uganda", "Kenya", "Nigeria"]),
        "curriculum_authority": st.text(
            min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))
        ),
        "currency": st.text(
            min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L", "N", "S"))
        ),
        "common_foods": st.lists(
            st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=5,
        ),
        "common_names": st.lists(
            st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=5,
        ),
        "household_materials": st.lists(
            st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=5,
        ),
        "geographic_contexts": st.lists(
            st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=5,
        ),
        "supported_languages": st.just(["en", "tw"]),
        "timezone": st.just("GMT"),
    }
)

# Strategy for generating L1LanguageContext data
l1_language_context_st = st.fixed_dictionaries(
    {
        "language_code": st.sampled_from(["en", "tw", "ee", "ga", "dag"]),
        "language_name": st.sampled_from(["English", "Twi", "Ewe", "Ga", "Dagbani"]),
        "greetings": st.lists(
            st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=3,
        ),
        "encouragement_phrases": st.lists(
            st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=3,
        ),
        "math_vocabulary": st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=1,
            max_size=3,
        ),
        "materials": st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=0,
            max_size=3,
        ),
        "action_verbs": st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
            min_size=0,
            max_size=3,
        ),
    }
)

# Strategy for WorkerTask payloads
worker_task_st = st.fixed_dictionaries(
    {
        "task_type": st.sampled_from(
            ["tts_generate", "image_analyze", "scheduled_message", "voice_transcribe"]
        ),
        "payload": st.fixed_dictionaries(
            {
                "text": st.text(min_size=1, max_size=100),
                "language": st.sampled_from(["en", "tw", "ee"]),
                "country": st.sampled_from(["GH", "UG", "KE", "NG"]),
            }
        ),
        "retry_count": st.integers(min_value=0, max_value=5),
        "max_retries": st.integers(min_value=1, max_value=5),
    }
)

# Strategy for ImageContent
image_content_st = st.fixed_dictionaries(
    {
        "data": st.text(
            min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"))
        ),
        "media_type": st.sampled_from(["image/jpeg", "image/png", "image/webp"]),
        "source_type": st.sampled_from(["base64", "url"]),
    }
)


# ============================================================================
# Mock Service Fixtures
# ============================================================================


@pytest.fixture
def mock_ai_client():
    """Mock AsyncAIClient for testing."""
    from gapsense.ai.async_client import AIResponse

    client = MagicMock()
    client.generate = AsyncMock(
        return_value=AIResponse(
            text="mock response",
            provider="anthropic",
            model="claude-sonnet-4-5",
            prompt_id="TEST-001",
            latency_ms=100.0,
            input_tokens=50,
            output_tokens=20,
        )
    )
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_prompt_service():
    """Mock PromptService for testing."""
    from gapsense.ai.prompt_service import PromptService, RenderedPrompt

    svc = MagicMock(spec=PromptService)
    svc.render_prompt.return_value = RenderedPrompt(
        prompt_id="TEST-001",
        system_prompt="You are a test assistant.",
        user_template=None,
        model="claude-sonnet-4-5",
        temperature=0.3,
        max_tokens=2048,
        country="GH",
        language="en",
    )
    svc.get_supported_countries.return_value = ["GH", "KE", "NG", "UG"]
    svc.get_supported_languages.return_value = ["en", "tw"]
    svc.list_prompts.return_value = [
        "ACT-001",
        "ANALYSIS-001",
        "ANALYSIS-002",
        "DIAG-001",
        "DIAG-002",
        "DIAG-003",
        "GUARD-001",
        "PARENT-001",
        "PARENT-002",
        "PARENT-003",
        "TEACHER-001",
        "TEACHER-002",
        "TEACHER-003",
    ]
    return svc


@pytest.fixture
def mock_media_service():
    """Mock MediaService for testing."""
    from gapsense.services.media_service import MediaService

    svc = MagicMock(spec=MediaService)
    svc.upload = AsyncMock(return_value="GH/student-1/image/123_test.jpg")
    svc.download = AsyncMock(return_value=b"fake-image-bytes")
    svc.generate_download_url = AsyncMock(return_value="https://s3.example.com/presigned")
    svc.generate_upload_url = AsyncMock(return_value="https://s3.example.com/upload")
    svc.verify_connectivity = AsyncMock(return_value=True)
    return svc


@pytest.fixture
def mock_guard_service():
    """Mock GuardService for testing."""
    from gapsense.services.guard_service import GuardResult, GuardService

    svc = MagicMock(spec=GuardService)
    svc.check = AsyncMock(
        return_value=GuardResult(
            passed=True,
            original_message="test",
            violations=[],
            latency_ms=50.0,
            ai_available=True,
        )
    )
    return svc
