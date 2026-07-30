"""Public, non-sensitive curriculum coverage endpoints."""

import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from fastapi.encoders import jsonable_encoder

from gapsense.curriculum.coverage import CoverageReport, build_coverage_report
from gapsense.curriculum.details import CurriculumDetail, build_curriculum_detail
from gapsense.curriculum.release import (
    ReleaseManifest,
    ReleaseManifestError,
    load_release_manifest,
)


def create_curriculum_router(
    data_path: Path,
    *,
    release_manifest: ReleaseManifest | None = None,
    manifest_preloaded: bool = False,
) -> APIRouter:
    """Build curriculum routes against a read-only local evidence repository."""
    router = APIRouter(prefix="/v1/curriculum", tags=["curriculum"])
    if not manifest_preloaded:
        try:
            release_manifest = load_release_manifest(data_path)
        except ReleaseManifestError:
            release_manifest = None
    if release_manifest is None:
        coverage_snapshot = build_coverage_report(data_path)
    else:
        coverage_snapshot = build_coverage_report(data_path, manifest=release_manifest)
    coverage_bytes = json.dumps(
        jsonable_encoder(coverage_snapshot),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()

    @router.get("/coverage", response_model=CoverageReport)
    async def coverage() -> Response:
        """Return the pre-encoded immutable application-start coverage snapshot."""
        return Response(content=coverage_bytes, media_type="application/json")

    @router.get("/{country}/{phase}/{level}/{subject}", response_model=CurriculumDetail)
    async def detail(country: str, phase: str, level: str, subject: str) -> CurriculumDetail:
        """Return a bounded, source-pinned projection for one curriculum cell."""
        result = (
            build_curriculum_detail(
                data_path,
                country=country,
                phase=phase,
                level=level,
                subject=subject,
                manifest=release_manifest,
            )
            if release_manifest is not None
            else None
        )
        if result is None:
            raise HTTPException(status_code=404, detail="curriculum detail is unavailable")
        return result

    return router
