"""Public, non-sensitive curriculum coverage endpoints."""

from pathlib import Path

from fastapi import APIRouter

from gapsense.curriculum.coverage import CoverageReport, build_coverage_report


def create_curriculum_router(data_path: Path) -> APIRouter:
    """Build curriculum routes against a read-only local evidence repository."""
    router = APIRouter(prefix="/v1/curriculum", tags=["curriculum"])

    @router.get("/coverage", response_model=CoverageReport)
    def coverage() -> CoverageReport:
        """Report repository availability separately from unverified extraction status."""
        return build_coverage_report(data_path)

    return router
