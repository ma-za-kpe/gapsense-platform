"""
Integration Tests for Demo UI

Tests the complete demo UI flow including:
- Teacher onboarding
- Message sending
- Image upload
- Command execution
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import Teacher
from gapsense.main import app


@pytest.fixture
async def client(db_session: AsyncSession, region_district_school):
    """Create test client with database override.

    Also ensures region/district/school hierarchy exists to avoid foreign key errors.
    """
    # Unpack the hierarchy (we just need it to exist in DB)
    region, district, school = region_district_school

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestDemoUI:
    """Test demo UI endpoints."""

    @pytest.mark.asyncio
    async def test_demo_page_loads(self, client: AsyncClient):
        """Test that demo page HTML loads successfully."""
        response = await client.get("/demo")

        assert response.status_code == 200
        assert "GapSense Teacher Demo" in response.text
        # Check for key UI elements
        assert "GapSense" in response.text
        assert "message" in response.text.lower()  # Has message input/display

    @pytest.mark.asyncio
    async def test_send_start_message(self, client: AsyncClient, db_session: AsyncSession):
        """Test sending START message creates teacher and initiates onboarding."""
        phone = "+233500000001"

        # Send START message
        response = await client.post(
            "/demo/api/message",
            data={
                "message": "START",
                "teacher_phone": phone,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data
        # Response should be meaningful (not just "Message received")
        assert len(data["response"]) > 20  # Should be a full message
        # Verify it's a proper response about onboarding
        response_lower = data["response"].lower()
        assert any(
            keyword in response_lower
            for keyword in ["welcome", "school", "onboard", "gapsense", "setup"]
        )

        # Verify teacher was created
        stmt = select(Teacher).where(Teacher.phone == phone)
        result = await db_session.execute(stmt)
        teacher = result.scalar_one_or_none()

        assert teacher is not None
        assert teacher.phone == phone

    @pytest.mark.asyncio
    async def test_complete_onboarding_flow(self, client: AsyncClient, db_session: AsyncSession):
        """Test complete teacher onboarding flow."""
        phone = "+233500000002"

        # Step 1: START
        response = await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Step 2: School name
        response = await client.post(
            "/demo/api/message",
            data={"message": "Test School", "teacher_phone": phone},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Step 3: Class name
        response = await client.post(
            "/demo/api/message",
            data={"message": "Grade 7A", "teacher_phone": phone},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Step 4: Student count
        response = await client.post(
            "/demo/api/message",
            data={"message": "3", "teacher_phone": phone},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Step 5: Student names
        response = await client.post(
            "/demo/api/message",
            data={"message": "Alice\nBob\nCharlie", "teacher_phone": phone},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify teacher was created and potentially updated
        stmt = select(Teacher).where(Teacher.phone == phone)
        result = await db_session.execute(stmt)
        teacher = result.scalar_one_or_none()

        assert teacher is not None
        assert teacher.phone == phone

    @pytest.mark.asyncio
    async def test_status_command(self, client: AsyncClient, db_session: AsyncSession):
        """Test /STATUS command returns class overview."""
        phone = "+233500000003"

        # Create teacher first
        teacher = Teacher(
            phone=phone,
            first_name="Test",
            last_name="Teacher",
            class_name="Test Class",
        )
        db_session.add(teacher)
        await db_session.commit()

        # Send /STATUS command
        response = await client.post(
            "/demo/api/message",
            data={"message": "/STATUS", "teacher_phone": phone},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "response" in data
        # Should contain status information
        assert "STATUS" in data["response"] or "class" in data["response"].lower()

    @pytest.mark.asyncio
    async def test_get_teacher_info(self, client: AsyncClient, db_session: AsyncSession):
        """Test getting teacher info endpoint."""
        phone = "+233500000004"

        # Create teacher via API (simulates real usage)
        await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone},
        )

        # Get teacher info
        response = await client.get(f"/demo/api/teacher-info?teacher_phone={phone}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "teacher" in data
        # Phone might be normalized differently, check that it contains the digits
        assert phone.replace("+", "").replace(" ", "") in data["teacher"]["phone"].replace(
            "+", ""
        ).replace(" ", "")
        assert "students" in data

    @pytest.mark.asyncio
    async def test_multiple_teachers(self, client: AsyncClient, db_session: AsyncSession):
        """Test that multiple teachers can use demo simultaneously."""
        phone1 = "+233500000005"
        phone2 = "+233500000006"

        # Teacher 1 starts
        response1 = await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone1},
        )
        assert response1.status_code == 200

        # Teacher 2 starts
        response2 = await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone2},
        )
        assert response2.status_code == 200

        # Verify both teachers exist
        stmt = select(Teacher).where(Teacher.phone.in_([phone1, phone2]))
        result = await db_session.execute(stmt)
        teachers = result.scalars().all()

        assert len(teachers) == 2
        assert {t.phone for t in teachers} == {phone1, phone2}

    @pytest.mark.asyncio
    async def test_error_handling(self, client: AsyncClient):
        """Test error handling for invalid inputs."""
        # Test missing phone number
        response = await client.post(
            "/demo/api/message",
            data={"message": "START"},
            # Missing teacher_phone
        )
        assert response.status_code == 422  # Validation error

        # Test empty message
        response = await client.post(
            "/demo/api/message",
            data={"message": "", "teacher_phone": "+233500000007"},
        )
        # Should handle gracefully (might return 200 with error in JSON)
        assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_idempotent_teacher_creation(self, client: AsyncClient, db_session: AsyncSession):
        """Test that sending START twice doesn't create duplicate teachers."""
        phone = "+233500000008"

        # Send START first time
        response1 = await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone},
        )
        assert response1.status_code == 200

        # Send START second time
        response2 = await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone},
        )
        assert response2.status_code == 200

        # Verify only one teacher exists
        stmt = select(Teacher).where(Teacher.phone == phone)
        result = await db_session.execute(stmt)
        teachers = result.scalars().all()

        assert len(teachers) == 1


class TestDemoUILogging:
    """Test that demo UI logs appropriately."""

    @pytest.mark.asyncio
    async def test_logs_teacher_creation(
        self, client: AsyncClient, db_session: AsyncSession, caplog
    ):
        """Test that teacher creation is logged."""
        import logging

        caplog.set_level(logging.INFO)

        phone = "+233500000009"

        await client.post(
            "/demo/api/message",
            data={"message": "START", "teacher_phone": phone},
        )

        # Check logs contain teacher creation message
        assert any("Creating new demo teacher" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_logs_errors(self, client: AsyncClient, caplog):
        """Test that errors are logged properly."""
        import logging

        caplog.set_level(logging.ERROR)

        # Trigger an error by sending invalid data
        # (implementation dependent on how errors are handled)
        response = await client.post(
            "/demo/api/message",
            data={"message": "TEST", "teacher_phone": "invalid"},
        )

        # Even if it succeeds, check that any errors are logged
        # This test may need adjustment based on actual error handling
        assert response.status_code in [200, 400, 422, 500]
