"""Tests for the local web service health contract."""

from pathlib import Path

from httpx import ASGITransport, AsyncClient

from gapsense import __version__
from gapsense.main import create_app


async def test_health_summary_reports_service_identity() -> None:
    """The summary endpoint exposes a stable, non-secret service contract."""
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "gapsense",
        "status": "ok",
        "version": __version__,
    }


async def test_liveness_reports_running_process() -> None:
    """The liveness endpoint only proves that the web process can respond."""
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


async def test_readiness_reports_local_curriculum_data() -> None:
    """The readiness endpoint proves that required local curriculum data is visible."""
    async with AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "checks": {"curriculum_repository": "ok"},
        "status": "ready",
    }


async def test_readiness_fails_closed_when_curriculum_data_is_missing(
    tmp_path: Path,
) -> None:
    """The service must not claim readiness when its curriculum mount is absent."""
    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "checks": {"curriculum_repository": "missing"},
        "status": "not_ready",
    }


async def test_readiness_requires_both_canonical_country_roots(tmp_path: Path) -> None:
    """A legacy graph or one country alone cannot make the platform ready."""
    (tmp_path / "curriculum").mkdir()
    (tmp_path / "curricula" / "ghana").mkdir(parents=True)

    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "checks": {"curriculum_repository": "missing"},
        "status": "not_ready",
    }
