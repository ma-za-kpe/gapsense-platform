"""
Tests for Diagnostic API Endpoints

Following TDD methodology - write tests first, then implement endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from gapsense.core.database import get_db
from gapsense.core.models import (
    CurriculumNode,
    CurriculumStrand,
    CurriculumSubStrand,
    DiagnosticSession,
    GapProfile,
    Parent,
    Student,
)
from gapsense.main import app


@pytest.fixture
async def client(db_session):
    """Create test client with database dependency override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def sample_student_data(db_session):
    """Create sample student with parent and curriculum data for testing."""
    # Create parent
    parent = Parent(
        phone="+233244123456",
        first_name="Kwame",
        last_name="Mensah",
        preferred_language="en",
    )
    db_session.add(parent)
    await db_session.flush()

    # Create student
    student = Student(
        first_name="Ama",
        last_name="Mensah",
        current_grade="B3",
        primary_parent_id=parent.id,
    )
    db_session.add(student)
    await db_session.flush()

    # Create curriculum data
    strand = CurriculumStrand(
        strand_number=1,
        name="Number",
        color_hex="#2563EB",
    )
    db_session.add(strand)
    await db_session.flush()

    sub_strand = CurriculumSubStrand(
        strand_id=strand.id,
        sub_strand_number=1,
        phase="B1_B3",
        name="Whole Numbers",
    )
    db_session.add(sub_strand)
    await db_session.flush()

    # Create nodes (B1, B2, B3 levels)
    node_b1 = CurriculumNode(
        code="B1.1.1.1",
        grade="B1",
        strand_id=strand.id,
        sub_strand_id=sub_strand.id,
        content_standard_number=1,
        title="Count to 100",
        description="Count forwards and backwards",
        severity=5,
        questions_required=2,
    )
    node_b2 = CurriculumNode(
        code="B2.1.1.1",
        grade="B2",
        strand_id=strand.id,
        sub_strand_id=sub_strand.id,
        content_standard_number=1,
        title="Count to 1000",
        description="Count forwards and backwards to 1000",
        severity=4,
        questions_required=2,
    )
    node_b3 = CurriculumNode(
        code="B3.1.1.1",
        grade="B3",
        strand_id=strand.id,
        sub_strand_id=sub_strand.id,
        content_standard_number=1,
        title="Count to 10000",
        description="Count in thousands",
        severity=3,
        questions_required=2,
    )
    db_session.add_all([node_b1, node_b2, node_b3])
    await db_session.commit()

    return {
        "parent": parent,
        "student": student,
        "nodes": {"B1": node_b1, "B2": node_b2, "B3": node_b3},
    }


@pytest.mark.asyncio
class TestDiagnosticSessionsAPI:
    """Test diagnostic session endpoints."""

    async def test_create_session(self, client, sample_student_data):
        """Test POST /api/v1/diagnostics/sessions creates new session."""
        student = sample_student_data["student"]

        response = await client.post(
            "/api/v1/diagnostics/sessions",
            json={
                "student_id": str(student.id),
                "entry_grade": "B3",
                "initiated_by": "parent",
                "channel": "whatsapp",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["student_id"] == str(student.id)
        assert data["entry_grade"] == "B3"
        assert data["status"] == "in_progress"
        assert data["initiated_by"] == "parent"
        assert data["channel"] == "whatsapp"
        assert "id" in data
        assert "started_at" in data

    async def test_create_session_invalid_student(self, client):
        """Test creating session with invalid student ID returns 404."""
        response = await client.post(
            "/api/v1/diagnostics/sessions",
            json={
                "student_id": "00000000-0000-0000-0000-000000000000",
                "entry_grade": "B3",
                "initiated_by": "parent",
                "channel": "whatsapp",
            },
        )

        assert response.status_code == 404
        assert "Student not found" in response.json()["detail"]

    async def test_create_session_invalid_channel(self, client, sample_student_data):
        """Test creating session with invalid channel returns 422."""
        student = sample_student_data["student"]

        response = await client.post(
            "/api/v1/diagnostics/sessions",
            json={
                "student_id": str(student.id),
                "entry_grade": "B3",
                "initiated_by": "parent",
                "channel": "invalid_channel",
            },
        )

        assert response.status_code == 422

    async def test_get_session(self, client, sample_student_data, db_session):
        """Test GET /api/v1/diagnostics/sessions/{id} returns session details."""
        student = sample_student_data["student"]

        # Create session
        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            channel="whatsapp",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(f"/api/v1/diagnostics/sessions/{session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session.id)
        assert data["student_id"] == str(student.id)
        assert data["status"] == "in_progress"

    async def test_get_session_not_found(self, client):
        """Test GET /api/v1/diagnostics/sessions/{id} with invalid ID returns 404."""
        response = await client.get(
            "/api/v1/diagnostics/sessions/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404

    async def test_list_student_sessions(self, client, sample_student_data, db_session):
        """Test GET /api/v1/diagnostics/students/{id}/sessions lists all sessions."""
        student = sample_student_data["student"]

        # Create multiple sessions
        session1 = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            channel="whatsapp",
            status="completed",
        )
        session2 = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="teacher",
            channel="web",
            status="in_progress",
        )
        db_session.add_all([session1, session2])
        await db_session.commit()

        response = await client.get(f"/api/v1/diagnostics/students/{student.id}/sessions")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(s["id"] == str(session1.id) for s in data)
        assert any(s["id"] == str(session2.id) for s in data)


@pytest.mark.asyncio
class TestDiagnosticAnswersAPI:
    """Test diagnostic answer submission endpoints."""

    async def test_submit_answer_correct(self, client, sample_student_data, db_session):
        """Test POST /api/v1/diagnostics/sessions/{id}/answers with correct answer."""
        student = sample_student_data["student"]
        node_b3 = sample_student_data["nodes"]["B3"]

        # Create session
        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            entry_node_id=node_b3.id,
            initiated_by="parent",
            channel="whatsapp",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/diagnostics/sessions/{session.id}/answers",
            json={
                "node_id": str(node_b3.id),
                "student_response": "42",
                "is_correct": True,
                "response_time_seconds": 30,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_correct"] is True
        assert data["student_response"] == "42"
        assert "next_question" in data or "session_completed" in data

    async def test_submit_answer_incorrect(self, client, sample_student_data, db_session):
        """Test POST /api/v1/diagnostics/sessions/{id}/answers with incorrect answer."""
        student = sample_student_data["student"]
        node_b3 = sample_student_data["nodes"]["B3"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            entry_node_id=node_b3.id,
            initiated_by="parent",
            status="in_progress",
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/diagnostics/sessions/{session.id}/answers",
            json={
                "node_id": str(node_b3.id),
                "student_response": "wrong",
                "is_correct": False,
                "response_time_seconds": 45,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["is_correct"] is False
        # Should trigger adaptive questioning to lower level
        assert "next_question" in data

    async def test_submit_answer_session_not_found(self, client):
        """Test submitting answer to non-existent session returns 404."""
        response = await client.post(
            "/api/v1/diagnostics/sessions/00000000-0000-0000-0000-000000000000/answers",
            json={
                "node_id": "00000000-0000-0000-0000-000000000001",
                "student_response": "test",
                "is_correct": True,
            },
        )

        assert response.status_code == 404

    async def test_submit_answer_completed_session(self, client, sample_student_data, db_session):
        """Test submitting answer to completed session returns 400."""
        student = sample_student_data["student"]
        node = sample_student_data["nodes"]["B3"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="completed",  # Already completed
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.post(
            f"/api/v1/diagnostics/sessions/{session.id}/answers",
            json={
                "node_id": str(node.id),
                "student_response": "test",
                "is_correct": True,
            },
        )

        assert response.status_code == 400
        assert "completed" in response.json()["detail"].lower()


@pytest.mark.asyncio
class TestGapProfilesAPI:
    """Test gap profile endpoints."""

    async def test_get_session_results(self, client, sample_student_data, db_session):
        """Test GET /api/v1/diagnostics/sessions/{id}/results returns gap profile."""
        student = sample_student_data["student"]
        node_b1 = sample_student_data["nodes"]["B1"]

        # Create completed session
        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="completed",
            total_questions=5,
            correct_answers=2,
            root_gap_node_id=node_b1.id,
            root_gap_confidence=0.85,
        )
        db_session.add(session)
        await db_session.flush()

        # Create gap profile
        gap_profile = GapProfile(
            student_id=student.id,
            session_id=session.id,
            primary_gap_node=node_b1.id,
            estimated_grade_level="B1",
            grade_gap=2,
            is_current=True,
        )
        db_session.add(gap_profile)
        await db_session.commit()

        response = await client.get(f"/api/v1/diagnostics/sessions/{session.id}/results")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == str(session.id)
        assert data["student_id"] == str(student.id)
        assert data["primary_gap_node"] == str(node_b1.id)
        assert data["estimated_grade_level"] == "B1"
        assert data["grade_gap"] == 2

    async def test_get_results_session_not_completed(self, client, sample_student_data, db_session):
        """Test getting results for in-progress session returns 400."""
        student = sample_student_data["student"]

        session = DiagnosticSession(
            student_id=student.id,
            entry_grade="B3",
            initiated_by="parent",
            status="in_progress",  # Not completed
        )
        db_session.add(session)
        await db_session.commit()

        response = await client.get(f"/api/v1/diagnostics/sessions/{session.id}/results")

        assert response.status_code == 400
        assert "not completed" in response.json()["detail"].lower()

    async def test_list_student_profiles(self, client, sample_student_data, db_session):
        """Test GET /api/v1/diagnostics/students/{id}/profiles lists all gap profiles."""
        student = sample_student_data["student"]

        # Create two sessions with profiles
        session1 = DiagnosticSession(
            student_id=student.id, entry_grade="B3", initiated_by="parent", status="completed"
        )
        session2 = DiagnosticSession(
            student_id=student.id, entry_grade="B3", initiated_by="teacher", status="completed"
        )
        db_session.add_all([session1, session2])
        await db_session.flush()

        profile1 = GapProfile(
            student_id=student.id,
            session_id=session1.id,
            estimated_grade_level="B2",
            is_current=False,
        )
        profile2 = GapProfile(
            student_id=student.id,
            session_id=session2.id,
            estimated_grade_level="B2",
            is_current=True,
        )
        db_session.add_all([profile1, profile2])
        await db_session.commit()

        response = await client.get(f"/api/v1/diagnostics/students/{student.id}/profiles")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        # Most recent (current) should be first
        assert data[0]["is_current"] is True
        assert data[0]["id"] == str(profile2.id)

    async def test_get_current_profile(self, client, sample_student_data, db_session):
        """Test GET /api/v1/diagnostics/students/{id}/profile/current returns latest."""
        student = sample_student_data["student"]
        node_b1 = sample_student_data["nodes"]["B1"]

        session = DiagnosticSession(
            student_id=student.id, entry_grade="B3", initiated_by="parent", status="completed"
        )
        db_session.add(session)
        await db_session.flush()

        profile = GapProfile(
            student_id=student.id,
            session_id=session.id,
            primary_gap_node=node_b1.id,
            estimated_grade_level="B1",
            is_current=True,
        )
        db_session.add(profile)
        await db_session.commit()

        response = await client.get(f"/api/v1/diagnostics/students/{student.id}/profile/current")

        assert response.status_code == 200
        data = response.json()
        assert data["is_current"] is True
        assert data["student_id"] == str(student.id)

    async def test_get_current_profile_none_exists(self, client, sample_student_data):
        """Test getting current profile when none exists returns 404."""
        student = sample_student_data["student"]

        response = await client.get(f"/api/v1/diagnostics/students/{student.id}/profile/current")

        assert response.status_code == 404
