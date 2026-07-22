"""Health endpoints for local orchestration and operator diagnostics."""

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from gapsense import __version__


class HealthSummary(BaseModel):
    """Stable service identity returned by the health summary endpoint."""

    service: Literal["gapsense"] = "gapsense"
    status: Literal["ok"] = "ok"
    version: str = __version__


class LivenessStatus(BaseModel):
    """Proof that the web process is able to answer requests."""

    status: Literal["alive"] = "alive"


class ReadinessChecks(BaseModel):
    """Local dependencies required by the current web foundation."""

    curriculum_data: Literal["ok", "missing"]


class ReadinessStatus(BaseModel):
    """Proof that dependencies required for local serving are available."""

    checks: ReadinessChecks = Field(default_factory=lambda: ReadinessChecks(curriculum_data="ok"))
    status: Literal["ready", "not_ready"] = "ready"


def create_health_router(data_path: Path) -> APIRouter:
    """Build health routes against the configured curriculum repository."""
    router = APIRouter(prefix="/v1/health", tags=["health"])

    @router.get("", response_model=HealthSummary)
    async def health_summary() -> HealthSummary:
        """Return service identity without leaking configuration or secrets."""
        return HealthSummary()

    @router.get("/live", response_model=LivenessStatus)
    async def liveness() -> LivenessStatus:
        """Return process liveness for Docker health checks."""
        return LivenessStatus()

    @router.get("/ready", response_model=ReadinessStatus)
    async def readiness(response: Response) -> ReadinessStatus:
        """Fail closed when the required curriculum repository is unavailable."""
        if not (data_path / "curriculum").is_dir():
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessStatus(
                checks=ReadinessChecks(curriculum_data="missing"),
                status="not_ready",
            )

        return ReadinessStatus()

    return router
