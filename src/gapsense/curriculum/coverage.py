"""Manifest-driven curriculum coverage without filesystem inference."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

# FastAPI resolves this nested response type at runtime.
from gapsense.curriculum.inventory import SourceInventoryRecord  # noqa: TC001
from gapsense.curriculum.release import (
    CatalogCell,
    ReleaseManifest,
    ReleaseManifestError,
    ReleaseRecord,
    load_release_manifest,
)

RepositoryStatus = Literal["available", "partial", "missing", "invalid"]
AvailabilityStatus = Literal["present_unverified", "missing"]
ReviewStatus = Literal["not_verified", "human_reviewed"]
CoverageMatrixStatus = Literal[
    "missing",
    "located",
    "extracted",
    "structurally_validated",
    "human_reviewed",
]
EvidenceScope = Literal["level"]


@dataclass(frozen=True, slots=True)
class EducationLevel:
    """One official education level named by the country authority."""

    identifier: str
    name: str
    official_phase: str
    scope_note: str = "Current scope note unavailable until a release catalogue validates."
    review_status: ReviewStatus = "not_verified"


@dataclass(frozen=True, slots=True)
class CurriculumSubject:
    """One subject explicitly named by at least one release record."""

    identifier: str
    name: str
    phase: str
    availability: AvailabilityStatus
    review_status: ReviewStatus


@dataclass(frozen=True, slots=True)
class CoverageMatrixEntry:
    """One exact level/subject claim from the release manifest."""

    level_identifier: str
    level_name: str
    phase: str
    subject_identifier: str
    subject_name: str
    status: CoverageMatrixStatus
    evidence_scope: EvidenceScope
    source_url: str


@dataclass(frozen=True, slots=True)
class CountryDefinition:
    """Stable country and authority metadata controlled by the platform."""

    code: Literal["GH", "UG"]
    slug: Literal["ghana", "uganda"]
    name: Literal["Ghana", "Uganda"]
    authority: str
    authority_url: str
    levels: tuple[EducationLevel, ...]


@dataclass(frozen=True, slots=True)
class CountryCoverage:
    """Manifest evidence for one country."""

    code: Literal["GH", "UG"]
    name: Literal["Ghana", "Uganda"]
    authority: str
    authority_url: str
    availability: AvailabilityStatus
    review_status: ReviewStatus
    repository_file_count: int
    levels: tuple[EducationLevel, ...]
    subjects: tuple[CurriculumSubject, ...]
    coverage_matrix: tuple[CoverageMatrixEntry, ...]


@dataclass(frozen=True, slots=True)
class CoverageSnapshot:
    """The immutable release identity used by this application instance."""

    generated_at: str
    source_version: str | None
    review_status: ReviewStatus


@dataclass(frozen=True, slots=True)
class CatalogCoverage:
    """Representation and evidence counts for the pinned official catalogue."""

    as_of: str
    scope_status: Literal["official_authority_inventory"]
    represented_cells: int
    total_cells: int
    evidence_cells: int


@dataclass(frozen=True, slots=True)
class SourceInventoryCoverage:
    """Every sanitized official-source record pinned by the data release."""

    as_of: str
    total_records: int
    acquired_artifacts: int
    records: tuple[SourceInventoryRecord, ...]


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Deterministic two-country release coverage."""

    repository_status: RepositoryStatus
    complete: Literal[False]
    countries: tuple[CountryCoverage, ...]
    warnings: tuple[str, ...]
    snapshot: CoverageSnapshot
    catalog: CatalogCoverage | None
    source_inventory: SourceInventoryCoverage | None


COUNTRY_DEFINITIONS: tuple[CountryDefinition, ...] = (
    CountryDefinition(
        code="GH",
        slug="ghana",
        name="Ghana",
        authority="National Council for Curriculum and Assessment (NaCCA)",
        authority_url="https://nacca.gov.gh/curriculum/",
        levels=(
            EducationLevel("kindergarten", "Kindergarten", "Key Phase 1"),
            EducationLevel("lower_primary", "Lower Primary", "Key Phase 2 (Basic 1–3)"),
            EducationLevel("upper_primary", "Upper Primary", "Key Phase 3 (Basic 4–6)"),
            EducationLevel("junior_high", "JHS (Basic 7–9)", "Key Phase 4"),
            EducationLevel("senior_high", "SHS", "Key Phase 5"),
        ),
    ),
    CountryDefinition(
        code="UG",
        slug="uganda",
        name="Uganda",
        authority="National Curriculum Development Centre (NCDC)",
        authority_url="https://ncdc.go.ug/directorates/",
        levels=(
            EducationLevel("early_childhood", "Early Childhood", "ECCE"),
            EducationLevel("primary_1_3", "Primary One–Three", "Primary Phase 1"),
            EducationLevel("primary_4", "Primary Four", "Primary Phase 2 transition"),
            EducationLevel("primary_5_7", "Primary Five–Seven", "Primary Phase 3"),
            EducationLevel("lower_secondary", "O-Level (S1–S4)", "UCE cycle"),
            EducationLevel("upper_secondary", "A-Level (S5–S6)", "UACE cycle"),
        ),
    ),
)


def _new_snapshot(source_version: str | None) -> CoverageSnapshot:
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return CoverageSnapshot(
        generated_at=generated_at,
        source_version=source_version,
        review_status="not_verified",
    )


def _subject_records(
    records: tuple[ReleaseRecord, ...],
    cells: tuple[CatalogCell, ...],
) -> tuple[CurriculumSubject, ...]:
    grouped: dict[tuple[str, str], list[CatalogCell]] = {}
    for cell in cells:
        grouped.setdefault((cell.phase, cell.subject), []).append(cell)
    record_groups: dict[tuple[str, str], list[ReleaseRecord]] = {}
    for record in records:
        record_groups.setdefault((record.phase, record.subject), []).append(record)
    subjects = []
    for (phase, identifier), catalog_matches in grouped.items():
        record_matches = record_groups.get((phase, identifier), [])
        subjects.append(
            CurriculumSubject(
                identifier=identifier,
                name=catalog_matches[0].subject_name,
                phase=phase,
                availability=(
                    "present_unverified"
                    if any(record.maturity != "missing" for record in record_matches)
                    else "missing"
                ),
                review_status=(
                    "human_reviewed"
                    if record_matches
                    and all(
                        record.review_status == "human_reviewed"
                        for record in record_matches
                        if record.maturity != "missing"
                    )
                    and any(record.maturity != "missing" for record in record_matches)
                    else "not_verified"
                ),
            )
        )
    return tuple(sorted(subjects, key=lambda subject: (subject.phase, subject.identifier)))


def _country_coverage(
    country: CountryDefinition,
    manifest: ReleaseManifest,
) -> CountryCoverage:
    records = tuple(record for record in manifest.records if record.country == country.code)
    cells = tuple(cell for cell in manifest.catalog_cells if cell.country == country.code)
    record_index = {(record.phase, record.level, record.subject): record for record in records}
    projection_paths = {
        path
        for record in records
        if record.projection is not None
        for path in (record.projection.nodes_path, record.projection.graph_path)
    }
    matrix = tuple(
        CoverageMatrixEntry(
            level_identifier=cell.level,
            level_name=cell.level_name,
            phase=cell.phase,
            subject_identifier=cell.subject,
            subject_name=cell.subject_name,
            status=(
                record_index[(cell.phase, cell.level, cell.subject)].maturity
                if (cell.phase, cell.level, cell.subject) in record_index
                else "missing"
            ),
            evidence_scope="level",
            source_url=cell.source_url,
        )
        for cell in sorted(
            cells,
            key=lambda item: (item.phase, item.level, item.subject),
        )
    )
    available_records = tuple(record for record in records if record.maturity != "missing")
    official_phases = {level.identifier: level.official_phase for level in country.levels}
    observed_levels: set[str] = set()
    catalog_levels = []
    for cell in cells:
        if cell.level in observed_levels:
            continue
        observed_levels.add(cell.level)
        catalog_levels.append(
            EducationLevel(
                identifier=cell.level,
                name=cell.level_name,
                official_phase=official_phases[cell.level],
                scope_note=cell.scope_note,
            )
        )
    return CountryCoverage(
        code=country.code,
        name=country.name,
        authority=country.authority,
        authority_url=country.authority_url,
        availability="present_unverified" if available_records else "missing",
        review_status=(
            "human_reviewed"
            if available_records
            and all(record.review_status == "human_reviewed" for record in available_records)
            else "not_verified"
        ),
        repository_file_count=len(projection_paths),
        levels=tuple(catalog_levels),
        subjects=_subject_records(records, cells),
        coverage_matrix=matrix,
    )


def _unavailable_report(
    status: Literal["missing", "invalid"],
    warning: str,
) -> CoverageReport:
    return CoverageReport(
        repository_status=status,
        complete=False,
        countries=tuple(
            CountryCoverage(
                code=country.code,
                name=country.name,
                authority=country.authority,
                authority_url=country.authority_url,
                availability="missing",
                review_status="not_verified",
                repository_file_count=0,
                levels=country.levels,
                subjects=(),
                coverage_matrix=(),
            )
            for country in COUNTRY_DEFINITIONS
        ),
        warnings=(warning,),
        snapshot=_new_snapshot(None),
        catalog=None,
        source_inventory=None,
    )


def canonical_repository_available(data_path: Path) -> bool:
    """Return whether one explicit release manifest and its pinned bytes validate."""
    try:
        load_release_manifest(data_path)
    except ReleaseManifestError:
        return False
    return True


def build_coverage_report(
    data_path: Path,
    *,
    manifest: ReleaseManifest | None = None,
) -> CoverageReport:
    """Build coverage exclusively from one byte-verified release manifest."""
    if manifest is None:
        release_path = data_path / "releases" / "curriculum-release.json"
        if release_path.is_symlink() or not release_path.is_file():
            return _unavailable_report("missing", "missing_release_manifest")
        try:
            manifest = load_release_manifest(data_path)
        except ReleaseManifestError:
            return _unavailable_report("invalid", "invalid_release_manifest")

    warning = {
        "candidate": "candidate_release",
        "empty": "empty_release",
        "released": None,
    }[manifest.release_status]
    return CoverageReport(
        repository_status="available",
        complete=False,
        countries=tuple(_country_coverage(country, manifest) for country in COUNTRY_DEFINITIONS),
        warnings=(warning,) if warning is not None else (),
        snapshot=_new_snapshot(manifest.release_id),
        catalog=CatalogCoverage(
            as_of=manifest.catalog_as_of,
            scope_status=manifest.catalog_scope_status,
            represented_cells=len(manifest.catalog_cells),
            total_cells=len(manifest.catalog_cells),
            evidence_cells=sum(record.maturity != "missing" for record in manifest.records),
        ),
        source_inventory=SourceInventoryCoverage(
            as_of=manifest.source_inventory.as_of,
            total_records=len(manifest.source_inventory.records),
            acquired_artifacts=sum(
                record.artifact_available for record in manifest.source_inventory.records
            ),
            records=manifest.source_inventory.records,
        ),
    )
