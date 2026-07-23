"""Tests for the public curriculum coverage API contract."""

from inspect import iscoroutinefunction
from pathlib import Path

from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

from gapsense.main import create_app
from gapsense.web.curriculum import create_curriculum_router


def test_coverage_filesystem_scan_is_delegated_to_a_worker_thread(
    tmp_path: Path,
) -> None:
    """A recursive evidence scan must never block the application's async event loop."""
    router = create_curriculum_router(tmp_path)
    coverage_route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path == "/v1/curriculum/coverage"
    )

    assert not iscoroutinefunction(coverage_route.endpoint)


async def test_coverage_endpoint_exposes_typed_non_sensitive_metadata(
    tmp_path: Path,
) -> None:
    """The API names both countries and authorities without claiming complete coverage."""
    ghana_path = tmp_path / "curricula" / "ghana"
    uganda_path = tmp_path / "curricula" / "uganda"
    ghana_path.mkdir(parents=True)
    uganda_path.mkdir()
    (ghana_path / "evidence.json").write_text("{}", encoding="utf-8")

    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/curriculum/coverage")

    payload = response.json()
    assert response.status_code == 200
    assert payload["complete"] is False
    assert payload["repository_status"] == "available"
    assert payload["warnings"] == []
    assert [country["code"] for country in payload["countries"]] == ["GH", "UG"]
    assert payload["countries"][0]["repository_file_count"] == 1
    assert payload["countries"][0]["review_status"] == "not_verified"
    assert payload["countries"][1]["availability"] == "missing"
    assert "path" not in response.text.lower()


async def test_coverage_endpoint_reports_missing_repository_without_a_server_error(
    tmp_path: Path,
) -> None:
    """Coverage truth remains queryable when the optional local evidence mount is absent."""
    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/curriculum/coverage")

    assert response.status_code == 200
    assert response.json()["repository_status"] == "missing"
    assert response.json()["warnings"] == ["missing_curricula_root"]
