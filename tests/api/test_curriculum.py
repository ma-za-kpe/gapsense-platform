"""
Tests for Curriculum API Endpoints

Following TDD methodology - write tests first, then implement endpoints.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from gapsense.core.database import get_db
from gapsense.core.models import CurriculumNode, CurriculumStrand, CurriculumSubStrand
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
async def sample_curriculum_data(db_session):
    """Create sample curriculum data for testing."""
    # Create strands
    strand1 = CurriculumStrand(
        strand_number=1,
        name="Number",
        color_hex="#2563EB",
        description="Foundation of numeracy",
    )
    strand2 = CurriculumStrand(
        strand_number=2,
        name="Algebra",
        color_hex="#7C3AED",
    )
    db_session.add_all([strand1, strand2])
    await db_session.flush()

    # Create sub-strands
    sub_strand11 = CurriculumSubStrand(
        strand_id=strand1.id,
        sub_strand_number=1,
        phase="B1_B3",
        name="Whole Numbers: Counting",
    )
    sub_strand12 = CurriculumSubStrand(
        strand_id=strand1.id,
        sub_strand_number=2,
        phase="B1_B3",
        name="Whole Numbers: Operations",
    )
    db_session.add_all([sub_strand11, sub_strand12])
    await db_session.flush()

    # Create nodes
    node1 = CurriculumNode(
        code="B1.1.1.1",
        grade="B1",
        strand_id=strand1.id,
        sub_strand_id=sub_strand11.id,
        content_standard_number=1,
        title="Describe numbers 0-100",
        description="Count by 1s, 2s, 10s forwards/backwards 0-100",
        severity=5,
        severity_rationale="Foundation of ALL numeracy",
        questions_required=2,
        confidence_threshold=0.80,
    )
    node2 = CurriculumNode(
        code="B1.1.2.1",
        grade="B1",
        strand_id=strand1.id,
        sub_strand_id=sub_strand12.id,
        content_standard_number=1,
        title="Add numbers within 20",
        description="Use objects, pictures, and equations to add",
        severity=4,
        severity_rationale="Critical for basic computation",
        questions_required=2,
        confidence_threshold=0.80,
    )
    db_session.add_all([node1, node2])
    await db_session.commit()

    return {
        "strands": [strand1, strand2],
        "sub_strands": [sub_strand11, sub_strand12],
        "nodes": [node1, node2],
    }


@pytest.mark.asyncio
class TestCurriculumStrandsAPI:
    """Test curriculum strands endpoints."""

    async def test_list_strands(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/strands returns all strands."""
        response = await client.get("/api/v1/curriculum/strands")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["strand_number"] == 1
        assert data[0]["name"] == "Number"
        assert data[0]["color_hex"] == "#2563EB"
        assert data[1]["strand_number"] == 2
        assert data[1]["name"] == "Algebra"

    async def test_get_strand_by_id(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/strands/{id} returns specific strand."""
        strand_id = sample_curriculum_data["strands"][0].id

        response = await client.get(f"/api/v1/curriculum/strands/{strand_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == strand_id
        assert data["name"] == "Number"
        assert "sub_strands" in data

    async def test_get_strand_not_found(self, client):
        """Test GET /api/v1/curriculum/strands/{id} with invalid ID returns 404."""
        response = await client.get("/api/v1/curriculum/strands/99999")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestCurriculumNodesAPI:
    """Test curriculum nodes endpoints."""

    async def test_list_nodes(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/nodes returns all nodes."""
        response = await client.get("/api/v1/curriculum/nodes")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["code"] == "B1.1.1.1"
        assert data[0]["title"] == "Describe numbers 0-100"
        assert data[0]["severity"] == 5

    async def test_list_nodes_filter_by_grade(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/nodes?grade=B1 filters by grade."""
        response = await client.get("/api/v1/curriculum/nodes?grade=B1")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(node["grade"] == "B1" for node in data)

    async def test_list_nodes_filter_by_severity(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/nodes?min_severity=5 filters by severity."""
        response = await client.get("/api/v1/curriculum/nodes?min_severity=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["severity"] == 5
        assert data[0]["code"] == "B1.1.1.1"

    async def test_get_node_by_code(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/nodes/{code} returns specific node."""
        response = await client.get("/api/v1/curriculum/nodes/B1.1.1.1")

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == "B1.1.1.1"
        assert data["title"] == "Describe numbers 0-100"
        assert data["severity"] == 5
        assert "strand" in data
        assert "sub_strand" in data

    async def test_get_node_not_found(self, client):
        """Test GET /api/v1/curriculum/nodes/{code} with invalid code returns 404."""
        response = await client.get("/api/v1/curriculum/nodes/B9.9.9.9")

        assert response.status_code == 404


@pytest.mark.asyncio
class TestCurriculumGraphAPI:
    """Test curriculum graph/prerequisite endpoints."""

    async def test_get_node_prerequisites(self, client, sample_curriculum_data):
        """Test GET /api/v1/curriculum/nodes/{code}/prerequisites returns prerequisite tree."""
        response = await client.get("/api/v1/curriculum/nodes/B1.1.1.1/prerequisites")

        assert response.status_code == 200
        data = response.json()
        assert "node" in data
        assert "prerequisites" in data
        assert isinstance(data["prerequisites"], list)
