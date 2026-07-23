"""Truthful curriculum repository metadata without exposing proprietary content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

RepositoryStatus = Literal["available", "partial", "missing", "invalid"]
AvailabilityStatus = Literal["present_unverified", "missing"]
ReviewStatus = Literal["not_verified"]


@dataclass(frozen=True, slots=True)
class EducationLevel:
    """An official education phase whose extraction still needs evidence."""

    identifier: str
    name: str
    official_phase: str
    review_status: ReviewStatus = "not_verified"


@dataclass(frozen=True, slots=True)
class CountryDefinition:
    """Stable country and curriculum-authority metadata."""

    code: Literal["GH", "UG"]
    slug: Literal["ghana", "uganda"]
    name: Literal["Ghana", "Uganda"]
    authority: str
    authority_url: str
    levels: tuple[EducationLevel, ...]


@dataclass(frozen=True, slots=True)
class CountryCoverage:
    """Non-sensitive availability metadata for one country repository."""

    code: Literal["GH", "UG"]
    name: Literal["Ghana", "Uganda"]
    authority: str
    authority_url: str
    availability: AvailabilityStatus
    review_status: ReviewStatus
    repository_file_count: int
    levels: tuple[EducationLevel, ...]


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Deterministic two-country repository report."""

    repository_status: RepositoryStatus
    complete: Literal[False]
    countries: tuple[CountryCoverage, ...]
    warnings: tuple[str, ...]


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
            EducationLevel("junior_high", "Junior High School", "Key Phase 4"),
            EducationLevel("senior_high", "Senior High School", "Key Phase 5"),
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
            EducationLevel("lower_secondary", "Lower Secondary", "UCE cycle"),
            EducationLevel("upper_secondary", "Upper Secondary", "UACE cycle"),
        ),
    ),
)


def _is_safe_directory(path: Path) -> bool:
    """Return whether a repository directory is real and minimally readable."""
    if not path.is_dir() or path.is_symlink():
        return False
    try:
        next(path.iterdir(), None)
    except OSError:
        return False
    return True


def _is_ignored_entry(path: Path) -> bool:
    """Ignore hidden, office-lock, unfinished, and backup files or directories."""
    return path.name.startswith(".") or path.name.endswith((".tmp", "~"))


def _count_repository_files(country_path: Path) -> int:
    """Count regular visible files without following any symlink."""
    file_count = 0
    pending_directories = [country_path]

    while pending_directories:
        current_directory = pending_directories.pop()
        for entry in current_directory.iterdir():
            if _is_ignored_entry(entry) or entry.is_symlink():
                continue
            if entry.is_dir():
                pending_directories.append(entry)
                continue
            if entry.is_file():
                file_count += 1

    return file_count


def canonical_repository_available(data_path: Path) -> bool:
    """Check only the canonical root structure used by service readiness."""
    curricula_path = data_path / "curricula"
    return _is_safe_directory(curricula_path) and all(
        _is_safe_directory(curricula_path / country.slug) for country in COUNTRY_DEFINITIONS
    )


def _missing_report(status: RepositoryStatus, warning: str) -> CoverageReport:
    """Build a report when no country root is safe to inspect."""
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
            )
            for country in COUNTRY_DEFINITIONS
        ),
        warnings=(warning,),
    )


def build_coverage_report(data_path: Path) -> CoverageReport:
    """Inspect canonical Ghana/Uganda roots without inferring extraction completion."""
    curricula_path = data_path / "curricula"
    if not curricula_path.exists():
        return _missing_report("missing", "missing_curricula_root")
    if not _is_safe_directory(curricula_path):
        return _missing_report("invalid", "invalid_curricula_root")

    warnings: list[str] = []
    country_reports: list[CountryCoverage] = []
    safe_country_count = 0

    for country in COUNTRY_DEFINITIONS:
        country_path = curricula_path / country.slug
        if country_path.is_symlink():
            warnings.append(f"unsafe_country_root:{country.slug}")
            file_count = 0
        elif not country_path.exists():
            warnings.append(f"missing_country_root:{country.slug}")
            file_count = 0
        elif not country_path.is_dir():
            warnings.append(f"invalid_country_root:{country.slug}")
            file_count = 0
        else:
            try:
                file_count = _count_repository_files(country_path)
            except OSError:
                warnings.append(f"unreadable_country_root:{country.slug}")
                file_count = 0
            else:
                safe_country_count += 1

        country_reports.append(
            CountryCoverage(
                code=country.code,
                name=country.name,
                authority=country.authority,
                authority_url=country.authority_url,
                availability="present_unverified" if file_count else "missing",
                review_status="not_verified",
                repository_file_count=file_count,
                levels=country.levels,
            )
        )

    expected_root_entries = {
        *(country.slug for country in COUNTRY_DEFINITIONS),
        "README.md",
        "coverage.json",
    }
    if any(
        not _is_ignored_entry(entry) and entry.name not in expected_root_entries
        for entry in curricula_path.iterdir()
    ):
        warnings.append("unexpected_country_entries")

    return CoverageReport(
        repository_status="available"
        if safe_country_count == len(COUNTRY_DEFINITIONS)
        else "partial",
        complete=False,
        countries=tuple(country_reports),
        warnings=tuple(warnings),
    )
