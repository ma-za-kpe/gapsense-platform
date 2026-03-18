"""
Tests for Teacher API Endpoints

School-based teacher management.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import School, Student, Teacher
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
async def test_teacher(db_session: AsyncSession, test_school: School) -> Teacher:
    """Create a test teacher."""
    teacher = Teacher(
        school_id=test_school.id,
        first_name="Mr.",
        last_name="Mensah",
        phone="+233501234567",
        grade_taught="B3",
        subjects=["Mathematics", "Science"],
        is_active=True,
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


class TestTeacherCreation:
    """Test teacher creation endpoints."""

    async def test_create_teacher_success(self, client: AsyncClient, test_school: School) -> None:
        """Test successful teacher creation."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Mrs.",
            "last_name": "Owusu",
            "phone": "+233201234567",
            "grade_taught": "B4",
            "subjects": ["English", "Social Studies"],
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == teacher_data["first_name"]
        assert data["last_name"] == teacher_data["last_name"]
        assert data["phone"] == teacher_data["phone"]
        assert data["is_active"] is True

    async def test_create_teacher_school_not_found(self, client: AsyncClient) -> None:
        """Test that creating teacher with invalid school fails."""
        teacher_data = {
            "school_id": "00000000-0000-0000-0000-000000000000",
            "first_name": "Mr.",
            "last_name": "Test",
            "phone": "+233201234567",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 404
        assert "School not found" in response.json()["detail"]

    async def test_create_teacher_duplicate_phone_same_school(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test that duplicate phone at same school is rejected."""
        teacher_data = {
            "school_id": str(test_teacher.school_id),
            "first_name": "Different",
            "last_name": "Teacher",
            "phone": test_teacher.phone,
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestTeacherRetrieval:
    """Test teacher retrieval endpoints."""

    async def test_get_teacher_by_id(self, client: AsyncClient, test_teacher: Teacher) -> None:
        """Test retrieving teacher by ID."""
        response = await client.get(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_teacher.id)
        assert data["first_name"] == test_teacher.first_name
        assert data["last_name"] == test_teacher.last_name

    async def test_get_teacher_not_found(self, client: AsyncClient) -> None:
        """Test 404 for non-existent teacher."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/teachers/{fake_id}")

        assert response.status_code == 404

    async def test_get_deleted_teacher(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test that deleted teachers are not retrievable."""
        # Soft delete the teacher
        from datetime import datetime

        test_teacher.deleted_at = datetime.utcnow()
        await db_session.commit()

        response = await client.get(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 404


class TestTeacherUpdate:
    """Test teacher update endpoints."""

    async def test_update_teacher_name(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test updating teacher's name."""
        update_data = {"first_name": "Dr.", "last_name": "Mensah"}

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Dr."
        assert data["last_name"] == "Mensah"

        # Verify in database
        await db_session.refresh(test_teacher)
        assert test_teacher.first_name == "Dr."

    async def test_update_teacher_grade(self, client: AsyncClient, test_teacher: Teacher) -> None:
        """Test updating teacher's grade taught."""
        update_data = {"grade_taught": "B5"}

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["grade_taught"] == "B5"

    async def test_update_teacher_subjects(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test updating teacher's subjects."""
        update_data = {"subjects": ["Mathematics", "ICT"]}

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert "ICT" in data["subjects"]

    async def test_update_teacher_not_found(self, client: AsyncClient) -> None:
        """Test updating non-existent teacher."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"first_name": "New Name"}

        response = await client.put(f"/api/v1/teachers/{fake_id}", json=update_data)

        assert response.status_code == 404


class TestTeacherStudents:
    """Test teacher-student relationships."""

    async def test_list_teacher_students(
        self,
        client: AsyncClient,
        test_teacher: Teacher,
        test_school: School,
        db_session: AsyncSession,
    ) -> None:
        """Test listing students for a teacher."""
        # Create a parent for students (required field)
        from gapsense.core.models import Parent

        parent = Parent(
            phone="+233999999999",
            opted_in=True,
            is_active=True,
        )
        db_session.add(parent)
        await db_session.flush()

        # Create students assigned to teacher
        student1 = Student(
            school_id=test_school.id,
            teacher_id=test_teacher.id,
            primary_parent_id=parent.id,
            first_name="Kofi",
            current_grade="B3",
        )
        student2 = Student(
            school_id=test_school.id,
            teacher_id=test_teacher.id,
            primary_parent_id=parent.id,
            first_name="Ama",
            current_grade="B3",
        )
        db_session.add_all([student1, student2])
        await db_session.commit()

        response = await client.get(f"/api/v1/teachers/{test_teacher.id}/students")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(s["first_name"] == "Kofi" for s in data)
        assert any(s["first_name"] == "Ama" for s in data)

    async def test_list_students_no_students(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test listing students when teacher has none."""
        response = await client.get(f"/api/v1/teachers/{test_teacher.id}/students")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    async def test_list_students_teacher_not_found(self, client: AsyncClient) -> None:
        """Test listing students for non-existent teacher."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/teachers/{fake_id}/students")

        assert response.status_code == 404


class TestTeacherDeletion:
    """Test teacher soft deletion."""

    async def test_delete_teacher(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test soft deleting a teacher."""
        response = await client.delete(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 204

        # Verify soft delete in database
        await db_session.refresh(test_teacher)
        assert test_teacher.deleted_at is not None
        assert test_teacher.is_active is False

    async def test_delete_teacher_not_found(self, client: AsyncClient) -> None:
        """Test deleting non-existent teacher."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.delete(f"/api/v1/teachers/{fake_id}")

        assert response.status_code == 404

    async def test_delete_already_deleted_teacher(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test deleting already deleted teacher."""
        # First deletion
        await client.delete(f"/api/v1/teachers/{test_teacher.id}")

        # Second deletion attempt
        response = await client.delete(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 404
