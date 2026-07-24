"""Bounded HTTP adapter for non-identifying product analytics events."""

from typing import Annotated, Literal, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from gapsense.analytics.events import AnalyticsEventName
from gapsense.analytics.sinks import AnalyticsSink

MAX_ANALYTICS_BODY_BYTES = 4096
MAX_ANALYTICS_EVENTS_PER_BATCH = 20
ANALYTICS_EVENTS_PATH = "/v1/analytics/events"


class AnalyticsBodyLimitMiddleware:
    """Limit actual analytics request bytes without trusting Content-Length."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("path") != ANALYTICS_EVENTS_PATH:
            await self._app(scope, receive, send)
            return

        received_bytes = 0

        async def receive_bounded() -> Message:
            nonlocal received_bytes
            message = await receive()
            body = cast(bytes, message.get("body", b""))
            received_bytes += len(body)
            if received_bytes > MAX_ANALYTICS_BODY_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                    detail="Analytics event batch is too large",
                )
            return message

        await self._app(scope, receive_bounded, send)


class AnalyticsEvent(BaseModel):
    """One versioned event with no arbitrary property or identity surface."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    name: AnalyticsEventName


class AnalyticsBatch(BaseModel):
    """A small, non-empty collection accepted by the local aggregate sink."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    events: list[AnalyticsEvent] = Field(
        min_length=1,
        max_length=MAX_ANALYTICS_EVENTS_PER_BATCH,
    )


def require_bounded_json(
    content_length: Annotated[str | None, Header(alias="Content-Length")] = None,
    content_type: Annotated[str | None, Header(alias="Content-Type")] = None,
) -> None:
    """Reject ambiguous or declared oversized bodies before accepting an event batch."""
    media_type = "" if content_type is None else content_type.partition(";")[0].strip().lower()
    if media_type != "application/json":
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Analytics events require application/json",
        )
    if content_length is None or not content_length.isdecimal():
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail="Analytics events require a valid Content-Length",
        )
    declared_bytes = int(content_length)
    if declared_bytes < 1:
        raise HTTPException(
            status_code=status.HTTP_411_LENGTH_REQUIRED,
            detail="Analytics events require a non-empty body",
        )
    if declared_bytes > MAX_ANALYTICS_BODY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Analytics event batch is too large",
        )


def create_analytics_router(sink: AnalyticsSink) -> APIRouter:
    """Build the optional collection route around one aggregate-only sink."""
    router = APIRouter(prefix="/v1/analytics", tags=["analytics"])

    @router.post(
        "/events",
        dependencies=[Depends(require_bounded_json)],
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def collect_events(batch: AnalyticsBatch) -> Response:
        """Count validated names without retaining event bodies or request identity."""
        sink.record(tuple(event.name for event in batch.events))
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return router
