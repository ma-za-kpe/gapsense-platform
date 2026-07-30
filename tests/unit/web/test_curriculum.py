"""Tests for the public curriculum coverage API contract."""

import asyncio
from inspect import iscoroutinefunction
from pathlib import Path

from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch

from gapsense.curriculum.coverage import CoverageReport, build_coverage_report
from gapsense.curriculum.release import ReleaseManifest, load_release_manifest
from gapsense.main import create_app
from gapsense.web.curriculum import create_curriculum_router
from tests.curriculum_release import release_record, write_projection, write_release_manifest


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


def test_application_validates_a_present_release_only_once(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Health and curriculum routes share one byte-verification pass at startup."""
    projection = write_projection(tmp_path)
    write_release_manifest(tmp_path, [release_record(projection)])
    calls = 0

    def counted_load(data_path: Path) -> ReleaseManifest:
        nonlocal calls
        calls += 1
        return load_release_manifest(data_path)

    monkeypatch.setattr("gapsense.web.app.load_release_manifest", counted_load)

    create_app(data_path=tmp_path)

    assert calls == 1


async def test_coverage_snapshot_is_built_once_for_concurrent_requests(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Closed or concurrent pages cannot enqueue duplicate repository scans."""
    calls = 0

    def counted_report(
        data_path: Path,
        *,
        manifest: ReleaseManifest | None = None,
    ) -> CoverageReport:
        nonlocal calls
        calls += 1
        return build_coverage_report(data_path, manifest=manifest)

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
    projection = write_projection(tmp_path)
    write_release_manifest(tmp_path, [release_record(projection)])

    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/curriculum/coverage")

    payload = response.json()
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert payload["complete"] is False
    assert payload["repository_status"] == "available"
    assert payload["warnings"] == ["candidate_release"]
    assert payload["snapshot"]["generated_at"].endswith("Z")
    assert payload["snapshot"]["source_version"] == "curriculum-2026-07-29-candidate.1"
    assert payload["snapshot"]["review_status"] == "not_verified"
    assert [country["code"] for country in payload["countries"]] == ["GH", "UG"]
    assert payload["catalog"] == {
        "as_of": "2026-07-29",
        "scope_status": "official_authority_inventory",
        "represented_cells": 176,
        "total_cells": 176,
        "evidence_cells": 1,
    }
    assert payload["source_inventory"]["total_records"] == 2
    assert payload["source_inventory"]["acquired_artifacts"] == 1
    assert len(payload["source_inventory"]["records"]) == 2
    assert [record["artifact_pages"] for record in payload["source_inventory"]["records"]] == [
        None,
        48,
    ]
    assert payload["countries"][0]["repository_file_count"] == 2
    assert payload["countries"][0]["levels"][0]["scope_note"] == (
        "Official scope statement for Kindergarten."
    )
    mathematics = next(
        subject
        for subject in payload["countries"][0]["subjects"]
        if subject["identifier"] == "mathematics" and subject["phase"] == "primary"
    )
    assert mathematics["availability"] == "present_unverified"
    assert len(payload["countries"][0]["coverage_matrix"]) == 67
    extracted = [
        entry
        for entry in payload["countries"][0]["coverage_matrix"]
        if entry["status"] == "extracted"
    ]
    assert len(extracted) == 1
    assert extracted[0]["subject_identifier"] == "mathematics"
    assert extracted[0]["evidence_scope"] == "level"
    assert extracted[0]["source_url"].startswith("https://nacca.gov.gh/")
    assert payload["countries"][0]["review_status"] == "not_verified"
    assert payload["countries"][1]["availability"] == "missing"
    assert "/app/" not in response.text.lower()
    assert "c:\\" not in response.text.lower()


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
    assert response.json()["warnings"] == ["missing_release_manifest"]


async def test_curriculum_detail_endpoint_projects_safe_lineage(tmp_path: Path) -> None:
    projection = write_projection(
        tmp_path,
        nodes={
            "extraction_method": "lossless-page-and-native-heading-projection",
            "nodes_fully_populated": {
                "B1.1.1.1": {
                    "title": "Count",
                    "source_locator": {"source_id": "gh-primary-mathematics", "page": 42},
                    "indicators": {"I1": {"title": "Count"}},
                }
            },
        },
        graph={
            "strands": {"1": {"name": "Number"}},
            "nodes": {"B1.1.1.1": {"strand": 1}},
        },
    )
    write_release_manifest(tmp_path, [release_record(projection)])

    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/curriculum/ghana/primary/lower_primary/mathematics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["release_id"] == "curriculum-2026-07-29-candidate.1"
    assert payload["evidence_scope"] == "level"
    assert payload["extraction_method"] == "lossless-page-and-native-heading-projection"
    assert payload["nodes"][0]["code"] == "B1.1.1.1"
    assert payload["nodes"][0]["strand_identifier"] == "1"
    assert payload["nodes"][0]["source_id"] == "gh-primary-mathematics"
    assert payload["nodes"][0]["source_page"] == 42
    assert payload["nodes"][0]["indicators"][0]["title"] == "Count"
    assert "/app/" not in response.text.lower()
    assert "c:\\" not in response.text.lower()


async def test_curriculum_detail_endpoint_fails_closed_for_undeclared_level(tmp_path: Path) -> None:
    projection = write_projection(tmp_path)
    write_release_manifest(tmp_path, [release_record(projection)])
    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.get("/v1/curriculum/ghana/primary/not_a_real_level/mathematics")

    assert response.status_code == 404
