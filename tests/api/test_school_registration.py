"""
Tests for school registration API endpoints.

TDD approach: Tests written first to define expected behavior.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models.schools import GESSchool, School, SchoolInvitation
from gapsense.main import app


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Create test client with database dependency override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_district(db_session: AsyncSession):
    """Create a test district with region for school registration."""
    from gapsense.core.models.schools import District, Region

    # Create region first (don't set id, let DB assign it)
    region = Region(name="Test Region", code="TR")
    db_session.add(region)
    await db_session.flush()

    # Create district
    district = District(region_id=region.id, name="Test District")
    db_session.add(district)
    await db_session.commit()
    await db_session.refresh(district)
    return district


class TestGESSchoolSearch:
    """Tests for GES school autocomplete search."""

    @pytest.mark.asyncio
    async def test_search_schools_by_name(self, db_session: AsyncSession, client: AsyncClient):
        """Search GES schools by name - returns matching schools."""
        # Setup: Create GES schools
        ges_school1 = GESSchool(
            ges_id=1,
            name="St. Mary's JHS",
            region="Greater Accra",
            district="Accra Metro",
            school_type="Junior High School",
        )
        ges_school2 = GESSchool(
            ges_id=2,
            name="Wesley Girls High School",
            region="Central",
            district="Cape Coast",
            school_type="Senior High School",
        )
        db_session.add_all([ges_school1, ges_school2])
        await db_session.commit()

        response = await client.get("/api/schools/search?q=mary")

        assert response.status_code == 200
        data = response.json()
        assert len(data["schools"]) == 1
        assert data["schools"][0]["name"] == "St. Mary's JHS"
        assert data["schools"][0]["ges_id"] == 1

    @pytest.mark.asyncio
    async def test_search_schools_empty_query(self, client: AsyncClient):
        """Return 422 if search query is empty (FastAPI validation)."""
        response = await client.get("/api/schools/search?q=")

        assert response.status_code == 422


class TestSchoolRegistration:
    """Tests for school registration endpoint."""

    @pytest.mark.asyncio
    async def test_register_school_success(
        self, db_session: AsyncSession, client: AsyncClient, test_district
    ):
        """Register school successfully and return invitation code."""
        # Setup: Create GES school
        ges_school = GESSchool(
            ges_id=343,
            name="St. Mary's JHS",
            region="Greater Accra",
            district="Accra Metro",
            school_type="Junior High School",
        )
        db_session.add(ges_school)
        await db_session.commit()

        registration_data = {
            "school_name": "St. Mary's JHS",
            "ges_school_id": 343,
            "headmaster_name": "Mr. John Mensah",
            "phone": "+233244123456",
            "num_teachers": 10,
        }

        response = await client.post("/api/schools/register", json=registration_data)

        assert response.status_code == 201
        data = response.json()

        # Should return invitation code
        assert "invitation_code" in data
        assert data["invitation_code"].startswith("STMARYS-")
        assert len(data["invitation_code"].split("-")[1]) == 6  # XXX123 format

        # Verify school was created in database
        stmt = select(School).where(School.name == "St. Mary's JHS")
        result = await db_session.execute(stmt)
        school = result.scalar_one_or_none()
        assert school is not None
        assert school.ges_school_id == 343
        assert school.registered_by == "Mr. John Mensah"
        assert school.phone == "+233244123456"

        # Verify invitation was created
        stmt = select(SchoolInvitation).where(SchoolInvitation.school_id == school.id)
        result = await db_session.execute(stmt)
        invitation = result.scalar_one_or_none()
        assert invitation is not None
        assert invitation.invitation_code == data["invitation_code"]
        assert invitation.is_active is True
        assert invitation.max_teachers == 10
        assert invitation.teachers_joined == 0

    @pytest.mark.asyncio
    async def test_register_school_missing_required_fields(self, client: AsyncClient):
        """Return 422 if required fields are missing."""
        registration_data = {
            "school_name": "Incomplete School",
            # Missing headmaster_name, phone, num_teachers
        }

        response = await client.post("/api/schools/register", json=registration_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_school_generates_unique_invitation(
        self, client: AsyncClient, test_district
    ):
        """Generate unique invitation code even if school name is similar."""
        registration_data_1 = {
            "school_name": "Wesley Girls High",
            "headmaster_name": "Mr. A",
            "phone": "+233244111111",
            "num_teachers": 10,
        }
        registration_data_2 = {
            "school_name": "Wesley Girls High School",
            "headmaster_name": "Mr. B",
            "phone": "+233244222222",
            "num_teachers": 10,
        }

        response1 = await client.post("/api/schools/register", json=registration_data_1)
        response2 = await client.post("/api/schools/register", json=registration_data_2)

        assert response1.status_code == 201
        assert response2.status_code == 201

        code1 = response1.json()["invitation_code"]
        code2 = response2.json()["invitation_code"]

        # Both should have same prefix but different suffix
        assert code1.split("-")[0] == code2.split("-")[0]  # Same prefix
        assert code1 != code2  # Different codes
