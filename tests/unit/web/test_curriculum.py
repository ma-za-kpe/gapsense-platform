"""Tests for the public curriculum coverage API contract."""

import asyncio
from inspect import iscoroutinefunction
from pathlib import Path

from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch

from gapsense.curriculum.coverage import CoverageReport, build_coverage_report
from gapsense.main import create_app
from gapsense.web.curriculum import create_curriculum_router


def test_coverage_request_uses_the_application_snapshot(
    tmp_path: Path,
) -> None:
    """The request path must not perform filesystem work in a worker thread."""
    router = create_curriculum_router(tmp_path)
    coverage_route = next(
        route
        for route in router.routes
        if isinstance(route, APIRoute) and route.path == "/v1/curriculum/coverage"
    )

    assert iscoroutinefunction(coverage_route.endpoint)


async def test_coverage_snapshot_is_built_once_for_concurrent_requests(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Closed or concurrent pages cannot enqueue duplicate repository scans."""
    calls = 0

    def counted_report(data_path: Path) -> CoverageReport:
        nonlocal calls
        calls += 1
        return build_coverage_report(data_path)

    monkeypatch.setattr(
        "gapsense.web.curriculum.build_coverage_report",
        counted_report,
    )
    application = create_app(data_path=tmp_path)

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        responses = await asyncio.gather(*(client.get("/v1/curriculum/coverage") for _ in range(8)))

    assert calls == 1
    assert {response.status_code for response in responses} == {200}


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
