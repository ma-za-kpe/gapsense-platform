"""Tests for manifest-driven, exact curriculum coverage."""

from __future__ import annotations

from pathlib import Path

from tests.curriculum_release import release_record, write_projection, write_release_manifest

from gapsense.curriculum.coverage import (
    build_coverage_report,
    canonical_repository_available,
)
from gapsense.curriculum.release import load_release_manifest


def test_coverage_represents_the_whole_catalog_and_overlays_only_exact_records(
    tmp_path: Path,
) -> None:
    """A shared projection marks two exact cells and leaves all other cells missing."""
    projection = write_projection(tmp_path)
    lower = release_record(projection)
    upper = release_record(
        projection,
        id="gh-primary-upper-primary-mathematics",
        level="upper_primary",
        node_code_prefixes=["B4.", "B5.", "B6."],
    )
    write_release_manifest(tmp_path, [lower, upper])

    report = build_coverage_report(tmp_path)

    assert report.repository_status == "available"
    assert report.complete is False
    assert report.warnings == ("candidate_release",)
    assert report.snapshot.source_version == "curriculum-2026-07-29-candidate.1"
    assert report.snapshot.review_status == "not_verified"
    assert report.catalog is not None
    assert report.catalog.as_of == "2026-07-29"
    assert report.catalog.scope_status == "official_authority_inventory"
    assert report.catalog.represented_cells == 176
    assert report.catalog.total_cells == 176
    assert report.catalog.evidence_cells == 2
    assert [country.code for country in report.countries] == ["GH", "UG"]
    ghana, uganda = report.countries
    assert ghana.availability == "present_unverified"
    assert ghana.repository_file_count == 2
    lower_primary = next(level for level in ghana.levels if level.identifier == "lower_primary")
    assert lower_primary.scope_note == "Official scope statement for Lower Primary."
    assert len(ghana.subjects) == 44
    mathematics = next(
        subject
        for subject in ghana.subjects
        if subject.phase == "primary" and subject.identifier == "mathematics"
    )
    assert mathematics.availability == "present_unverified"
    exact_evidence = [
        (entry.level_identifier, entry.subject_identifier, entry.status, entry.evidence_scope)
        for entry in ghana.coverage_matrix
        if entry.status != "missing"
    ]
    assert exact_evidence == [
        ("lower_primary", "mathematics", "extracted", "level"),
        ("upper_primary", "mathematics", "extracted", "level"),
    ]
    assert len(ghana.coverage_matrix) == 67
    assert all(
        entry.source_url.startswith("https://nacca.gov.gh/") for entry in ghana.coverage_matrix
    )
    assert uganda.availability == "missing"
    assert uganda.repository_file_count == 0
    assert uganda.levels[0].name == "Early Childhood"
    assert uganda.levels[0].scope_note == "Official scope statement for Early Childhood."
    assert len(uganda.coverage_matrix) == 109
    assert all(entry.status == "missing" for entry in uganda.coverage_matrix)


def test_public_fixture_projects_every_pinned_catalog_cell_without_loss() -> None:
    repository_root = Path(__file__).parents[3]
    data_path = repository_root / "fixtures" / "public-data"
    manifest = load_release_manifest(data_path)

    report = build_coverage_report(data_path, manifest=manifest)

    expected_cells = {
        (cell.country, cell.phase, cell.level, cell.subject) for cell in manifest.catalog_cells
    }
    projected_cells = {
        (country.code, entry.phase, entry.level_identifier, entry.subject_identifier)
        for country in report.countries
        for entry in country.coverage_matrix
    }
    expected_notes = {
        (cell.country, cell.level, cell.scope_note) for cell in manifest.catalog_cells
    }
    projected_notes = {
        (country.code, level.identifier, level.scope_note)
        for country in report.countries
        for level in country.levels
    }
    assert len(expected_cells) == 176
    assert projected_cells == expected_cells
    assert projected_notes == expected_notes


def test_coverage_keeps_explicit_missing_records_visible(tmp_path: Path) -> None:
    missing = release_record(
        None,
        id="ug-primary-primary-1-3-mathematics",
        country="UG",
        country_slug="uganda",
        authority="National Curriculum Development Centre (NCDC)",
        level="primary_1_3",
        maturity="missing",
        node_code_prefixes=["P1.", "P2.", "P3."],
    )
    write_release_manifest(tmp_path, [missing])

    report = build_coverage_report(tmp_path)
    uganda = report.countries[1]

    assert uganda.availability == "missing"
    mathematics = next(
        subject
        for subject in uganda.subjects
        if subject.phase == "primary" and subject.identifier == "mathematics"
    )
    assert mathematics.availability == "missing"
    matrix_entry = next(
        entry
        for entry in uganda.coverage_matrix
        if entry.level_identifier == "primary_1_3" and entry.subject_identifier == "mathematics"
    )
    assert matrix_entry.status == "missing"
    assert matrix_entry.evidence_scope == "level"


def test_coverage_fails_closed_for_missing_and_invalid_manifests(tmp_path: Path) -> None:
    missing = build_coverage_report(tmp_path)
    assert missing.repository_status == "missing"
    assert missing.warnings == ("missing_release_manifest",)
    assert missing.snapshot.source_version is None
    assert missing.catalog is None
    assert all(country.subjects == () for country in missing.countries)

    projection = write_projection(tmp_path)
    projection["nodes_sha256"] = "0" * 64
    write_release_manifest(tmp_path, [release_record(projection)])
    invalid = build_coverage_report(tmp_path)
    assert invalid.repository_status == "invalid"
    assert invalid.warnings == ("invalid_release_manifest",)
    assert invalid.snapshot.source_version is None
    assert invalid.catalog is None


def test_explicit_empty_manifest_represents_catalog_without_invented_evidence(
    tmp_path: Path,
) -> None:
    write_release_manifest(
        tmp_path,
        [],
        release_id="curriculum-public-empty-1",
        release_status="empty",
    )

    report = build_coverage_report(tmp_path)

    assert report.repository_status == "available"
    assert report.warnings == ("empty_release",)
    assert report.snapshot.source_version == "curriculum-public-empty-1"
    assert all(country.availability == "missing" for country in report.countries)
    assert report.catalog is not None
    assert report.catalog.represented_cells == 176
    assert report.catalog.evidence_cells == 0
    assert sum(len(country.coverage_matrix) for country in report.countries) == 176
    assert all(
        entry.status == "missing"
        for country in report.countries
        for entry in country.coverage_matrix
    )
    assert canonical_repository_available(tmp_path) is True


def test_readiness_requires_a_valid_byte_pinned_manifest(tmp_path: Path) -> None:
    assert canonical_repository_available(tmp_path) is False

    projection = write_projection(tmp_path)
    write_release_manifest(tmp_path, [release_record(projection)])
    assert canonical_repository_available(tmp_path) is True

    (tmp_path / projection["nodes_path"]).write_text("{}", encoding="utf-8")
    assert canonical_repository_available(tmp_path) is False
