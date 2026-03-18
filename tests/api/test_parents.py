"""
Tests for Parent API Endpoints

Wolf/Aurino dignity-first parent management.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import Parent, School, Student
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
    """Create a test district with region."""
    from gapsense.core.models import District, Region

    # Create region first
    region = Region(name="Test Region", code="TR")
    db_session.add(region)
    await db_session.flush()

    # Create district
    district = District(region_id=region.id, name="Test District")
    db_session.add(district)
    await db_session.commit()
    await db_session.refresh(district)
    return district


@pytest.fixture
async def test_school(db_session: AsyncSession, test_district) -> School:
    """Create a test school."""
    school = School(
        name="Test Primary School",
        district_id=test_district.id,
        school_type="primary",
        is_active=True,
    )
    db_session.add(school)
    await db_session.commit()
    await db_session.refresh(school)
    return school


@pytest.fixture
async def test_parent(db_session: AsyncSession) -> Parent:
    """Create a test parent."""
    parent = Parent(
        phone="+233501234567",
        preferred_name="Auntie Ama",
        preferred_language="tw",
        opted_in=True,
        is_active=True,
    )
    db_session.add(parent)
    await db_session.commit()
    await db_session.refresh(parent)
    return parent


class TestParentCreation:
    """Test parent creation endpoints."""

    async def test_create_parent_success(self, client: AsyncClient) -> None:
        """Test successful parent creation."""
        parent_data = {
            "phone": "+233201234567",
            "preferred_name": "Auntie Akosua",
            "preferred_language": "en",
            "opted_in": True,
        }

        response = await client.post("/api/v1/parents/", json=parent_data)

        assert response.status_code == 201
        data = response.json()
        assert data["phone"] == parent_data["phone"]
        assert data["preferred_name"] == parent_data["preferred_name"]
        assert data["opted_in"] is True
        assert data["is_active"] is True

    async def test_create_parent_duplicate_phone(
        self, client: AsyncClient, test_parent: Parent
    ) -> None:
        """Test that duplicate phone numbers are rejected."""
        parent_data = {
            "phone": test_parent.phone,
            "preferred_name": "Different Name",
            "preferred_language": "en",
            "opted_in": True,
        }

        response = await client.post("/api/v1/parents/", json=parent_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    async def test_create_parent_minimal_data(self, client: AsyncClient) -> None:
        """Test parent creation with minimal required data."""
        parent_data = {
            "phone": "+233301234567",
        }

        response = await client.post("/api/v1/parents/", json=parent_data)

        assert response.status_code == 201
        data = response.json()
        assert data["phone"] == parent_data["phone"]
        assert data["preferred_language"] == "en"  # Default


class TestParentRetrieval:
    """Test parent retrieval endpoints."""

    async def test_get_parent_by_id(self, client: AsyncClient, test_parent: Parent) -> None:
        """Test retrieving parent by ID."""
        response = await client.get(f"/api/v1/parents/{test_parent.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_parent.id)
        assert data["phone"] == test_parent.phone

    async def test_get_parent_not_found(self, client: AsyncClient) -> None:
        """Test 404 for non-existent parent."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/parents/{fake_id}")

        assert response.status_code == 404

    async def test_get_parent_by_phone(self, client: AsyncClient, test_parent: Parent) -> None:
        """Test retrieving parent by phone number."""
        response = await client.get(f"/api/v1/parents/phone/{test_parent.phone}")

        assert response.status_code == 200
        data = response.json()
        assert data["phone"] == test_parent.phone
        assert data["id"] == str(test_parent.id)

    async def test_get_parent_by_phone_not_found(self, client: AsyncClient) -> None:
        """Test 404 for non-existent phone."""
        response = await client.get("/api/v1/parents/phone/+233999999999")

        assert response.status_code == 404


class TestParentUpdate:
    """Test parent update endpoints."""

    async def test_update_parent_name(
        self, client: AsyncClient, test_parent: Parent, db_session: AsyncSession
    ) -> None:
        """Test updating parent's preferred name."""
        update_data = {"preferred_name": "Auntie Abena"}

        response = await client.put(f"/api/v1/parents/{test_parent.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["preferred_name"] == "Auntie Abena"

        # Verify in database
        await db_session.refresh(test_parent)
        assert test_parent.preferred_name == "Auntie Abena"

    async def test_update_parent_language(self, client: AsyncClient, test_parent: Parent) -> None:
        """Test updating parent's language preference."""
        update_data = {"preferred_language": "ee"}

        response = await client.put(f"/api/v1/parents/{test_parent.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["preferred_language"] == "ee"

    async def test_update_parent_literacy_level(
        self, client: AsyncClient, test_parent: Parent
    ) -> None:
        """Test updating parent's literacy level (sensitive field)."""
        update_data = {"literacy_level": "semi_literate"}

        response = await client.put(f"/api/v1/parents/{test_parent.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["literacy_level"] == "semi_literate"

    async def test_update_parent_not_found(self, client: AsyncClient) -> None:
        """Test updating non-existent parent."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"preferred_name": "New Name"}

        response = await client.put(f"/api/v1/parents/{fake_id}", json=update_data)

        assert response.status_code == 404


class TestParentStudents:
    """Test parent-student relationships."""

    async def test_list_parent_students(
        self,
        client: AsyncClient,
        test_parent: Parent,
        test_school: School,
        db_session: AsyncSession,
    ) -> None:
        """Test listing students for a parent."""
        # Create students linked to parent
        student1 = Student(
            school_id=test_school.id,
            first_name="Kwame",
            current_grade="B3",
            primary_parent_id=test_parent.id,
        )
        student2 = Student(
            school_id=test_school.id,
            first_name="Akosua",
            current_grade="B2",
            primary_parent_id=test_parent.id,
        )
        db_session.add_all([student1, student2])
        await db_session.commit()

        response = await client.get(f"/api/v1/parents/{test_parent.id}/students")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(s["first_name"] == "Kwame" for s in data)
        assert any(s["first_name"] == "Akosua" for s in data)

    async def test_list_students_no_students(
        self, client: AsyncClient, test_parent: Parent
    ) -> None:
        """Test listing students when parent has none."""
        response = await client.get(f"/api/v1/parents/{test_parent.id}/students")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_list_students_parent_not_found(self, client: AsyncClient) -> None:
        """Test listing students for non-existent parent."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/parents/{fake_id}/students")

        assert response.status_code == 404


class TestParentOptOut:
    """Test parent opt-out/opt-in (Wolf/Aurino compliance)."""

    async def test_opt_out_parent(
        self, client: AsyncClient, test_parent: Parent, db_session: AsyncSession
    ) -> None:
        """Test parent opt-out from WhatsApp engagement."""
        response = await client.post(f"/api/v1/parents/{test_parent.id}/opt-out")

        assert response.status_code == 200
        data = response.json()
        assert data["opted_out"] is True
        assert data["opted_in"] is False
        assert data["is_active"] is False

        # Verify in database
        await db_session.refresh(test_parent)
        assert test_parent.opted_out is True
        assert test_parent.opted_out_at is not None

    async def test_opt_in_parent(
        self, client: AsyncClient, test_parent: Parent, db_session: AsyncSession
    ) -> None:
        """Test parent re-opt-in to WhatsApp engagement."""
        # First opt out
        await client.post(f"/api/v1/parents/{test_parent.id}/opt-out")

        # Then opt back in
        response = await client.post(f"/api/v1/parents/{test_parent.id}/opt-in")

        assert response.status_code == 200
        data = response.json()
        assert data["opted_in"] is True
        assert data["opted_out"] is False
        assert data["is_active"] is True

        # Verify in database
        await db_session.refresh(test_parent)
        assert test_parent.opted_in is True
        assert test_parent.opted_in_at is not None

    async def test_opt_out_not_found(self, client: AsyncClient) -> None:
        """Test opt-out for non-existent parent."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.post(f"/api/v1/parents/{fake_id}/opt-out")

        assert response.status_code == 404
