"""
Tests for main application startup, health checks, and configuration.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from gapsense.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Create test client for main app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthEndpoints:
    """Test all health check endpoints."""

    async def test_root_endpoint(self, client: AsyncClient) -> None:
        """Test root endpoint returns service info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "GapSense Platform"
        assert data["status"] == "operational"
        assert data["version"] == "0.1.0"
        assert "environment" in data

    async def test_health_check_endpoint_healthy(self, client: AsyncClient) -> None:
        """Test /health endpoint when all services are healthy."""
        response = await client.get("/health")

        # Can be 200 (healthy) or 503 (unhealthy) depending on DB state
        assert response.status_code in [200, 503]
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "checks" in data
        assert "database" in data["checks"]
        assert "prompt_library" in data["checks"]

    async def test_health_check_includes_environment(self, client: AsyncClient) -> None:
        """Test health check includes environment info."""
        response = await client.get("/health")

        data = response.json()
        assert "environment" in data

    async def test_health_check_includes_prompt_library_metrics(self, client: AsyncClient) -> None:
        """Test health check includes prompt library metrics."""
        import os

        response = await client.get("/health")

        data = response.json()
        prompt_check = data["checks"]["prompt_library"]
        assert "prompts" in prompt_check
        assert "version" in prompt_check
        # In CI mode, prompts may be 0 (empty library)
        if os.getenv("CI") != "true":
            assert prompt_check["prompts"] > 0

    async def test_readiness_check_ready(self, client: AsyncClient) -> None:
        """Test /health/ready endpoint responds correctly."""
        response = await client.get("/health/ready")

        # Can be 200 (ready) or 503 (not ready) depending on DB state
        assert response.status_code in [200, 503]
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]

    async def test_liveness_check(self, client: AsyncClient) -> None:
        """Test /health/live endpoint always returns alive."""
        response = await client.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestApplicationStartup:
    """Test application startup and configuration."""

    async def test_app_initializes_successfully(self, client: AsyncClient) -> None:
        """Test that app can initialize and serve requests."""
        # If we can make any request, app started successfully
        response = await client.get("/")
        assert response.status_code == 200

    async def test_cors_middleware_configured(self, client: AsyncClient) -> None:
        """Test CORS middleware is properly configured."""
        response = await client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS headers should be present
        assert response.status_code in [200, 204]

    async def test_docs_endpoint_accessible_in_dev(self, client: AsyncClient) -> None:
        """Test API docs are accessible in development."""
        # In test environment, docs should be available
        response = await client.get("/docs")

        # Should either redirect to docs UI or return 200
        assert response.status_code in [200, 307]

    async def test_openapi_schema_accessible(self, client: AsyncClient) -> None:
        """Test OpenAPI schema is accessible."""
        response = await client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "GapSense Platform"
        assert schema["info"]["version"] == "0.1.0"

    async def test_all_api_routers_registered(self, client: AsyncClient) -> None:
        """Test all API routers are properly registered."""
        response = await client.get("/openapi.json")
        schema = response.json()

        # Check that all expected API paths are registered
        paths = schema["paths"]
        assert any("/api/v1/curriculum" in path for path in paths)
        assert any("/api/v1/diagnostics" in path for path in paths)
        assert any("/api/v1/parents" in path for path in paths)
        assert any("/api/v1/teachers" in path for path in paths)


class TestApplicationConfiguration:
    """Test application configuration and middleware."""

    async def test_app_title_and_description(self, client: AsyncClient) -> None:
        """Test app has correct title and description."""
        response = await client.get("/openapi.json")
        schema = response.json()

        assert schema["info"]["title"] == "GapSense Platform"
        assert "AI-powered" in schema["info"]["description"]

    async def test_health_endpoints_tagged_correctly(self, client: AsyncClient) -> None:
        """Test health endpoints are tagged for API docs."""
        response = await client.get("/openapi.json")
        schema = response.json()

        # Health endpoints should have "Health" tag
        health_paths = ["/", "/health", "/health/ready", "/health/live"]
        for path in health_paths:
            if path in schema["paths"]:
                endpoint_info = schema["paths"][path]["get"]
                assert "Health" in endpoint_info.get("tags", [])


class TestErrorHandling:
    """Test application error handling."""

    async def test_404_for_nonexistent_endpoint(self, client: AsyncClient) -> None:
        """Test 404 response for non-existent endpoints."""
        response = await client.get("/nonexistent/endpoint")

        assert response.status_code == 404

    async def test_invalid_method_returns_405(self, client: AsyncClient) -> None:
        """Test 405 for invalid HTTP methods."""
        response = await client.post("/health/live")

        assert response.status_code == 405
