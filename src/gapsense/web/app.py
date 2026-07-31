"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI

from gapsense import __version__
from gapsense.analytics.sinks import AggregateAnalyticsSink, AnalyticsSink
from gapsense.config import settings
from gapsense.curriculum.release import ReleaseManifestError, load_release_manifest
from gapsense.web.analytics import AnalyticsBodyLimitMiddleware, create_analytics_router
from gapsense.web.curriculum import create_curriculum_router
from gapsense.web.health import create_health_router


def create_app(
    *,
    data_path: Path | None = None,
    analytics_sink: AnalyticsSink | None = None,
) -> FastAPI:
    """Build an isolated web application for serving and tests."""
    effective_data_path = settings.GAPSENSE_DATA_PATH if data_path is None else data_path
    effective_analytics_sink = analytics_sink
    if effective_analytics_sink is None and settings.ANALYTICS_MODE == "local_aggregate":
        effective_analytics_sink = AggregateAnalyticsSink()
    application = FastAPI(
        title="GapSense",
        version=__version__,
        summary="Curriculum-aligned learning diagnostics for Ghana and Uganda",
    )
    try:
        release_manifest = load_release_manifest(effective_data_path)
    except ReleaseManifestError:
        release_manifest = None
    application.include_router(
        create_health_router(
            effective_data_path,
            repository_available=release_manifest is not None,
        )
    )
    application.include_router(
        create_curriculum_router(
            effective_data_path,
            release_manifest=release_manifest,
            manifest_preloaded=True,
        )
    )
    if effective_analytics_sink is not None:
        application.include_router(create_analytics_router(effective_analytics_sink))
        application.add_middleware(AnalyticsBodyLimitMiddleware)
    return application
