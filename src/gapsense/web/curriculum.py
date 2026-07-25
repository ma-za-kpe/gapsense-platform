"""Public, non-sensitive curriculum coverage endpoints."""

from pathlib import Path

from fastapi import APIRouter, HTTPException

from gapsense.curriculum.coverage import CoverageReport, build_coverage_report
from gapsense.curriculum.details import CurriculumDetail, build_curriculum_detail


def create_curriculum_router(data_path: Path) -> APIRouter:
    """Build curriculum routes against a read-only local evidence repository."""
    router = APIRouter(prefix="/v1/curriculum", tags=["curriculum"])
    coverage_snapshot = build_coverage_report(data_path)

    @router.get("/coverage", response_model=CoverageReport)
    async def coverage() -> CoverageReport:
        """Return the immutable application-start coverage snapshot."""
        return coverage_snapshot

    @router.get("/{country}/{phase}/{level}/{subject}", response_model=CurriculumDetail)
    async def detail(country: str, phase: str, level: str, subject: str) -> CurriculumDetail:
        """Return a bounded standards/indicator projection for one local subject."""
        result = build_curriculum_detail(
            data_path,
            country=country,
            phase=phase,
            level=level,
            subject=subject,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="curriculum detail is unavailable")
        return result

    return router
