"""FastAPI application factory."""

from pathlib import Path

from fastapi import FastAPI

from gapsense import __version__
from gapsense.config import settings
from gapsense.web.curriculum import create_curriculum_router
from gapsense.web.health import create_health_router


def create_app(*, data_path: Path | None = None) -> FastAPI:
    """Build an isolated web application for serving and tests."""
    effective_data_path = settings.GAPSENSE_DATA_PATH if data_path is None else data_path
    application = FastAPI(
        title="GapSense",
        version=__version__,
        summary="Curriculum-aligned learning diagnostics for Ghana and Uganda",
    )
    application.include_router(create_health_router(effective_data_path))
    application.include_router(create_curriculum_router(effective_data_path))
    return application
