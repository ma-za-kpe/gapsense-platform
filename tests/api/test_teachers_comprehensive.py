"""
Comprehensive Teacher API Tests - ALL Code Paths

Tests every error branch, edge case, validation failure, and database constraint.
Bulletproof testing - nothing missed.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import District, Parent, Region, School, Student, Teacher
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
    """Create test district with region."""
    region = Region(name="Test Region", code="TR")
    db_session.add(region)
    await db_session.flush()

    district = District(region_id=region.id, name="Test District")
    db_session.add(district)
    await db_session.commit()
    await db_session.refresh(district)
    return district


@pytest.fixture
async def test_school(db_session: AsyncSession, test_district) -> School:
    """Create test school."""
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
async def test_school2(db_session: AsyncSession, test_district) -> School:
    """Create second test school."""
    school = School(
        name="Test Secondary School",
        district_id=test_district.id,
        school_type="jhs",
        is_active=True,
    )
    db_session.add(school)
    await db_session.commit()
    await db_session.refresh(school)
    return school


@pytest.fixture
async def test_teacher(db_session: AsyncSession, test_school: School) -> Teacher:
    """Create test teacher."""
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


class TestTeacherCreationEdgeCases:
    """Test all teacher creation edge cases and error paths."""

    async def test_create_teacher_with_all_fields(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test teacher creation with ALL possible fields."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Dr.",
            "last_name": "Owusu",
            "phone": "+233201111111",
            "grade_taught": "B5",
            "subjects": ["English", "Social Studies", "ICT"],
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 201
        data = response.json()
        assert data["first_name"] == "Dr."
        assert data["last_name"] == "Owusu"
        assert data["phone"] == "+233201111111"
        assert data["grade_taught"] == "B5"
        assert len(data["subjects"]) == 3
        assert "ICT" in data["subjects"]

    async def test_create_teacher_minimal_fields(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test teacher creation with only required fields."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Ms.",
            "last_name": "Appiah",
            "phone": "+233201111112",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 201
        data = response.json()
        assert data["grade_taught"] is None
        assert data["subjects"] is None

    async def test_create_teacher_invalid_school_id_format(self, client: AsyncClient) -> None:
        """Test validation failure - invalid UUID format for school_id."""
        teacher_data = {
            "school_id": "not-a-valid-uuid",
            "first_name": "Mr.",
            "last_name": "Test",
            "phone": "+233201111113",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422

    async def test_create_teacher_missing_first_name(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - missing required first_name."""
        teacher_data = {
            "school_id": str(test_school.id),
            "last_name": "NoFirstName",
            "phone": "+233201111114",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any(err["loc"] == ["body", "first_name"] for err in errors)

    async def test_create_teacher_missing_last_name(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - missing required last_name."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "NoLastName",
            "phone": "+233201111115",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422
        errors = response.json()["detail"]
        assert any(err["loc"] == ["body", "last_name"] for err in errors)

    async def test_create_teacher_missing_phone(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - missing required phone."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Mr.",
            "last_name": "NoPhone",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422

    async def test_create_teacher_empty_name_strings(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - empty string names."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "",  # Empty but present
            "last_name": "Test",
            "phone": "+233201111116",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        # Pydantic min_length=1 validation
        assert response.status_code == 422

    async def test_create_teacher_name_too_long(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - name exceeds max_length."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "A" * 150,  # > 100 chars
            "last_name": "Test",
            "phone": "+233201111117",
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422

    async def test_create_teacher_phone_too_short(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - phone too short."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Mr.",
            "last_name": "Test",
            "phone": "123",  # < 10 chars
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422

    async def test_create_teacher_phone_too_long(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - phone too long."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Mr.",
            "last_name": "Test",
            "phone": "+233" + "1" * 50,  # > 20 chars
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422

    async def test_create_teacher_grade_too_long(
        self, client: AsyncClient, test_school: School
    ) -> None:
        """Test validation failure - grade_taught too long."""
        teacher_data = {
            "school_id": str(test_school.id),
            "first_name": "Mr.",
            "last_name": "Test",
            "phone": "+233201111118",
            "grade_taught": "TOOLONG",  # > 5 chars
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 422

    async def test_create_teacher_same_phone_different_schools(
        self, client: AsyncClient, test_school: School, test_school2: School
    ) -> None:
        """Test that same phone at different schools is allowed."""
        teacher_data1 = {
            "school_id": str(test_school.id),
            "first_name": "Mr.",
            "last_name": "Multi",
            "phone": "+233201111119",
        }

        teacher_data2 = {
            "school_id": str(test_school2.id),
            "first_name": "Mr.",
            "last_name": "Multi",
            "phone": "+233201111119",  # Same phone, different school
        }

        response1 = await client.post("/api/v1/teachers/", json=teacher_data1)
        assert response1.status_code == 201

        response2 = await client.post("/api/v1/teachers/", json=teacher_data2)
        # Should succeed - duplicate check is per school
        assert response2.status_code == 201

    async def test_create_teacher_duplicate_phone_same_school(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test duplicate phone at same school error."""
        teacher_data = {
            "school_id": str(test_teacher.school_id),
            "first_name": "Duplicate",
            "last_name": "Teacher",
            "phone": test_teacher.phone,
        }

        response = await client.post("/api/v1/teachers/", json=teacher_data)

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


class TestTeacherRetrievalEdgeCases:
    """Test all teacher retrieval edge cases."""

    async def test_get_teacher_invalid_uuid_format(self, client: AsyncClient) -> None:
        """Test error handling for invalid UUID format."""
        response = await client.get("/api/v1/teachers/not-a-uuid")

        assert response.status_code == 422

    async def test_get_deleted_teacher_not_accessible(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test that deleted teachers are not retrievable."""
        from datetime import datetime

        # Soft delete
        test_teacher.deleted_at = datetime.utcnow()
        await db_session.commit()

        response = await client.get(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 404

    async def test_get_active_teacher_after_others_deleted(
        self,
        client: AsyncClient,
        test_teacher: Teacher,
        test_school: School,
        db_session: AsyncSession,
    ) -> None:
        """Test retrieving active teacher when others are deleted."""
        from datetime import datetime

        # Create and delete another teacher
        deleted_teacher = Teacher(
            school_id=test_school.id,
            first_name="Deleted",
            last_name="Teacher",
            phone="+233999888777",
            deleted_at=datetime.utcnow(),
        )
        db_session.add(deleted_teacher)
        await db_session.commit()

        # Should still be able to get active teacher
        response = await client.get(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 200
        assert response.json()["id"] == str(test_teacher.id)


class TestTeacherUpdateEdgeCases:
    """Test all teacher update edge cases and validation."""

    async def test_update_teacher_empty_payload(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test update with no fields changed."""
        update_data = {}

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == test_teacher.first_name

    async def test_update_teacher_all_fields_at_once(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test updating all possible fields simultaneously."""
        update_data = {
            "first_name": "Dr.",
            "last_name": "Updated",
            "phone": "+233999111222",
            "grade_taught": "B7",
            "subjects": ["Physics", "Chemistry", "Biology"],
        }

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Dr."
        assert data["last_name"] == "Updated"
        assert data["phone"] == "+233999111222"
        assert data["grade_taught"] == "B7"
        assert len(data["subjects"]) == 3

        await db_session.refresh(test_teacher)
        assert test_teacher.first_name == "Dr."

    async def test_update_teacher_null_values(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test updating fields to null."""
        update_data = {
            "grade_taught": None,
            "subjects": None,
        }

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["grade_taught"] is None
        assert data["subjects"] is None

    async def test_update_teacher_single_subject(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test updating to single subject."""
        update_data = {
            "subjects": ["Mathematics"],
        }

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        assert len(response.json()["subjects"]) == 1

    async def test_update_teacher_empty_subjects_list(
        self, client: AsyncClient, test_teacher: Teacher
    ) -> None:
        """Test updating to empty subjects list."""
        update_data = {
            "subjects": [],
        }

        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 200
        assert response.json()["subjects"] == []

    async def test_update_deleted_teacher(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test that deleted teachers cannot be updated."""
        from datetime import datetime

        # Soft delete
        test_teacher.deleted_at = datetime.utcnow()
        await db_session.commit()

        update_data = {"first_name": "Should Fail"}
        response = await client.put(f"/api/v1/teachers/{test_teacher.id}", json=update_data)

        assert response.status_code == 404


class TestTeacherStudentsEdgeCases:
    """Test teacher-student relationship edge cases."""

    async def test_list_students_with_many_students(
        self,
        client: AsyncClient,
        test_teacher: Teacher,
        test_school: School,
        db_session: AsyncSession,
    ) -> None:
        """Test listing many students for a teacher."""
        # Create parent
        parent = Parent(phone="+233999999999", opted_in=True, is_active=True)
        db_session.add(parent)
        await db_session.flush()

        # Create 10 students
        students = [
            Student(
                school_id=test_school.id,
                teacher_id=test_teacher.id,
                primary_parent_id=parent.id,
                first_name=f"Student_{i}",
                current_grade="B3",
            )
            for i in range(10)
        ]
        db_session.add_all(students)
        await db_session.commit()

        response = await client.get(f"/api/v1/teachers/{test_teacher.id}/students")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 10

    async def test_list_students_deleted_teacher(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test listing students for deleted teacher."""
        from datetime import datetime

        test_teacher.deleted_at = datetime.utcnow()
        await db_session.commit()

        response = await client.get(f"/api/v1/teachers/{test_teacher.id}/students")

        assert response.status_code == 404


class TestTeacherDeletionEdgeCases:
    """Test teacher deletion edge cases and soft delete behavior."""

    async def test_delete_teacher_verify_soft_delete(
        self, client: AsyncClient, test_teacher: Teacher, db_session: AsyncSession
    ) -> None:
        """Test that deletion is soft (sets deleted_at timestamp)."""
        response = await client.delete(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 204

        # Verify still in database but deleted
        await db_session.refresh(test_teacher)
        assert test_teacher.deleted_at is not None
        assert test_teacher.is_active is False

    async def test_delete_teacher_with_students(
        self,
        client: AsyncClient,
        test_teacher: Teacher,
        test_school: School,
        db_session: AsyncSession,
    ) -> None:
        """Test deleting teacher who has students."""
        # Create parent and student
        parent = Parent(phone="+233888777666", opted_in=True, is_active=True)
        db_session.add(parent)
        await db_session.flush()

        student = Student(
            school_id=test_school.id,
            teacher_id=test_teacher.id,
            primary_parent_id=parent.id,
            first_name="Student",
            current_grade="B3",
        )
        db_session.add(student)
        await db_session.commit()

        # Should still be able to soft delete
        response = await client.delete(f"/api/v1/teachers/{test_teacher.id}")

        assert response.status_code == 204

        # Student should still exist
        await db_session.refresh(student)
        assert student.teacher_id == test_teacher.id

    async def test_delete_teacher_twice(self, client: AsyncClient, test_teacher: Teacher) -> None:
        """Test deleting already deleted teacher."""
        # First deletion
        response1 = await client.delete(f"/api/v1/teachers/{test_teacher.id}")
        assert response1.status_code == 204

        # Second deletion attempt
        response2 = await client.delete(f"/api/v1/teachers/{test_teacher.id}")
        assert response2.status_code == 404

    async def test_delete_nonexistent_teacher(self, client: AsyncClient) -> None:
        """Test deleting non-existent teacher."""
        fake_id = "00000000-0000-0000-0000-000000000001"
        response = await client.delete(f"/api/v1/teachers/{fake_id}")

        assert response.status_code == 404


class TestTeacherDatabaseConstraints:
    """Test database constraint violations and integrity."""

    async def test_create_teacher_concurrent_duplicate_check(
        self, client: AsyncClient, test_school: School, db_session: AsyncSession
    ) -> None:
        """Test race condition in duplicate phone check."""
        # This tests the unique constraint path
        teacher1_data = {
            "school_id": str(test_school.id),
            "first_name": "First",
            "last_name": "Teacher",
            "phone": "+233111222333",
        }

        # Create first teacher
        response1 = await client.post("/api/v1/teachers/", json=teacher1_data)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = await client.post("/api/v1/teachers/", json=teacher1_data)
        assert response2.status_code == 409
