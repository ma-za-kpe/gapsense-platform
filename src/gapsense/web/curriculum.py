"""Public, non-sensitive curriculum coverage endpoints."""

from pathlib import Path

from fastapi import APIRouter

from gapsense.curriculum.coverage import CoverageReport, build_coverage_report


def create_curriculum_router(data_path: Path) -> APIRouter:
    """Build curriculum routes against a read-only local evidence repository."""
    router = APIRouter(prefix="/v1/curriculum", tags=["curriculum"])
    coverage_snapshot = build_coverage_report(data_path)

    @router.get("/coverage", response_model=CoverageReport)
    async def coverage() -> CoverageReport:
        """Return the immutable application-start coverage snapshot."""
        return coverage_snapshot

    return router
