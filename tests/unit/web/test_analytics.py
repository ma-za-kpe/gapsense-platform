"""Tests for the bounded, aggregate-only product analytics API."""

from pathlib import Path

import pytest
from fastapi import HTTPException
from httpx import ASGITransport, AsyncClient
from pytest import MonkeyPatch

from gapsense.analytics.sinks import AggregateAnalyticsSink
from gapsense.main import create_app
from gapsense.web.analytics import require_bounded_json


async def test_analytics_route_is_absent_when_collection_is_disabled(tmp_path: Path) -> None:
    """The default local and deployment-hold application exposes no collection surface."""
    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/analytics/events",
            json={"events": [{"schema_version": "1.0.0", "name": "entry_viewed"}]},
        )

    assert response.status_code == 404


async def test_local_aggregate_mode_constructs_the_private_sink(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Explicit local configuration enables collection without an external processor."""
    monkeypatch.setattr("gapsense.web.app.settings.ANALYTICS_MODE", "local_aggregate")

    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path)),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/analytics/events",
            json={"events": [{"schema_version": "1.0.0", "name": "entry_viewed"}]},
        )

    assert response.status_code == 204


async def test_analytics_route_accepts_allowlisted_events_without_identity(
    tmp_path: Path,
) -> None:
    """Accepted events become counters and the response discloses no aggregate state."""
    sink = AggregateAnalyticsSink()
    async with AsyncClient(
        transport=ASGITransport(app=create_app(data_path=tmp_path, analytics_sink=sink)),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/analytics/events",
            json={
                "events": [
                    {"schema_version": "1.0.0", "name": "entry_viewed"},
                    {"schema_version": "1.0.0", "name": "planner_country_selected"},
                ]
            },
        )
        health_response = await client.get("/v1/health/live")

    assert response.status_code == 204
    assert response.content == b""
    assert health_response.status_code == 200
    assert sink.snapshot() == {
        "entry_viewed": 1,
        "planner_country_selected": 1,
    }


async def test_analytics_route_rejects_unapproved_payload_shapes(tmp_path: Path) -> None:
    """Unknown events, identity-like fields, and unbounded batches fail closed."""
    sink = AggregateAnalyticsSink()
    application = create_app(data_path=tmp_path, analytics_sink=sink)
    cases = [
        {"events": []},
        {"events": [{"schema_version": "1.0.0", "name": "learner_name"}]},
        {
            "events": [
                {
                    "schema_version": "1.0.0",
                    "name": "entry_viewed",
                    "user_id": "not-allowed",
                }
            ]
        },
        {"events": [{"schema_version": "1.0.0", "name": "entry_viewed"} for _ in range(21)]},
    ]

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        responses = [await client.post("/v1/analytics/events", json=payload) for payload in cases]

    assert [response.status_code for response in responses] == [422, 422, 422, 422]
    assert sink.snapshot() == {}


async def test_analytics_route_enforces_json_and_bounded_declared_size(tmp_path: Path) -> None:
    """The local boundary rejects ambiguous media types and declared oversized requests."""
    sink = AggregateAnalyticsSink()
    application = create_app(data_path=tmp_path, analytics_sink=sink)
    payload = b'{"events":[{"schema_version":"1.0.0","name":"entry_viewed"}]}'

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        wrong_media_type = await client.post(
            "/v1/analytics/events",
            content=payload,
            headers={"Content-Type": "text/plain"},
        )
        invalid_length = await client.post(
            "/v1/analytics/events",
            content=payload,
            headers={
                "Content-Length": "unknown",
                "Content-Type": "application/json",
            },
        )
        too_large = await client.post(
            "/v1/analytics/events",
            content=payload,
            headers={
                "Content-Length": "4097",
                "Content-Type": "application/json; charset=utf-8",
            },
        )

    assert wrong_media_type.status_code == 415
    assert invalid_length.status_code == 411
    assert too_large.status_code == 413
    assert sink.snapshot() == {}


async def test_analytics_route_enforces_actual_size_when_declared_size_lies(
    tmp_path: Path,
) -> None:
    """The application boundary limits streamed bytes without trusting the client header."""
    sink = AggregateAnalyticsSink()
    application = create_app(data_path=tmp_path, analytics_sink=sink)
    oversized_payload = (
        b'{"events":[{"schema_version":"1.0.0","name":"entry_viewed","padding":"'
        + (b"x" * 4096)
        + b'"}]}'
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/v1/analytics/events",
            content=oversized_payload,
            headers={
                "Content-Length": "1",
                "Content-Type": "application/json",
            },
        )

    assert response.status_code == 413
    assert response.json() == {"detail": "Analytics event batch is too large"}
    assert sink.snapshot() == {}


@pytest.mark.parametrize(
    ("content_length", "content_type", "expected_status"),
    [
        (None, None, 415),
        (None, "application/json", 411),
        ("0", "application/json", 411),
    ],
)
def test_analytics_header_guard_rejects_missing_or_empty_bodies(
    content_length: str | None,
    content_type: str | None,
    expected_status: int,
) -> None:
    """Missing declarations and zero-byte batches never reach the sink."""
    with pytest.raises(HTTPException) as error:
        require_bounded_json(content_length, content_type)

    assert error.value.status_code == expected_status
