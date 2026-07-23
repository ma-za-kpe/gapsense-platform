"""Tests for truthful, read-only curriculum repository inventory."""

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from gapsense.curriculum.coverage import (
    build_coverage_report,
    canonical_repository_available,
)


def _create_country_roots(data_path: Path) -> tuple[Path, Path]:
    curricula_path = data_path / "curricula"
    ghana_path = curricula_path / "ghana"
    uganda_path = curricula_path / "uganda"
    ghana_path.mkdir(parents=True)
    uganda_path.mkdir()
    return ghana_path, uganda_path


def test_inventory_reports_presence_without_claiming_completion(tmp_path: Path) -> None:
    """Files prove local availability, never completed extraction or review."""
    ghana_path, uganda_path = _create_country_roots(tmp_path)
    (tmp_path / "curricula" / "README.md").write_text("# Curriculum index", encoding="utf-8")
    (ghana_path / "primary").mkdir()
    (ghana_path / "primary" / "mathematics.json").write_text("{}", encoding="utf-8")
    (uganda_path / "primary").mkdir()
    (uganda_path / "primary" / "mathematics.json").write_text("{}", encoding="utf-8")

    report = build_coverage_report(tmp_path)

    assert report.repository_status == "available"
    assert report.complete is False
    assert report.warnings == ()
    assert [country.code for country in report.countries] == ["GH", "UG"]
    assert [country.repository_file_count for country in report.countries] == [1, 1]
    assert all(country.availability == "present_unverified" for country in report.countries)
    assert all(country.review_status == "not_verified" for country in report.countries)
    assert report.countries[0].authority == (
        "National Council for Curriculum and Assessment (NaCCA)"
    )
    assert report.countries[1].authority == "National Curriculum Development Centre (NCDC)"
    assert [level.identifier for level in report.countries[0].levels] == [
        "kindergarten",
        "lower_primary",
        "upper_primary",
        "junior_high",
        "senior_high",
    ]
    assert [level.identifier for level in report.countries[1].levels] == [
        "early_childhood",
        "primary_1_3",
        "primary_4",
        "primary_5_7",
        "lower_secondary",
        "upper_secondary",
    ]
    assert all(
        level.review_status == "not_verified"
        for country in report.countries
        for level in country.levels
    )


def test_inventory_ignores_hidden_transient_and_symlinked_files(tmp_path: Path) -> None:
    """Untrusted or tool-generated entries cannot inflate availability metadata."""
    ghana_path, uganda_path = _create_country_roots(tmp_path)
    evidence_path = ghana_path / "evidence.json"
    evidence_path.write_text("{}", encoding="utf-8")
    (ghana_path / ".hidden.json").write_text("{}", encoding="utf-8")
    (ghana_path / ".!office-lock.json").write_text("{}", encoding="utf-8")
    (ghana_path / "unfinished.tmp").write_text("{}", encoding="utf-8")
    (ghana_path / "backup.json~").write_text("{}", encoding="utf-8")
    (ghana_path / "linked.json").symlink_to(evidence_path)
    hidden_directory = ghana_path / ".cache"
    hidden_directory.mkdir()
    (hidden_directory / "cached.json").write_text("{}", encoding="utf-8")
    linked_directory = ghana_path / "linked-directory"
    linked_directory.symlink_to(uganda_path, target_is_directory=True)
    os.mkfifo(ghana_path / "named-pipe")

    report = build_coverage_report(tmp_path)

    assert report.countries[0].repository_file_count == 1
    assert report.countries[1].repository_file_count == 0
    assert report.countries[1].availability == "missing"


def test_inventory_fails_closed_for_missing_partial_and_invalid_roots(
    tmp_path: Path,
) -> None:
    """Malformed layouts stay observable without leaking an absolute private path."""
    missing_report = build_coverage_report(tmp_path)

    assert missing_report.repository_status == "missing"
    assert missing_report.warnings == ("missing_curricula_root",)
    assert all(country.availability == "missing" for country in missing_report.countries)

    curricula_path = tmp_path / "curricula"
    curricula_path.write_text("not a directory", encoding="utf-8")
    invalid_report = build_coverage_report(tmp_path)

    assert invalid_report.repository_status == "invalid"
    assert invalid_report.warnings == ("invalid_curricula_root",)
    assert str(tmp_path) not in repr(invalid_report)

    curricula_path.unlink()
    (curricula_path / "ghana").mkdir(parents=True)
    partial_report = build_coverage_report(tmp_path)

    assert partial_report.repository_status == "partial"
    assert partial_report.warnings == ("missing_country_root:uganda",)

    (curricula_path / "uganda").write_text("not a directory", encoding="utf-8")
    malformed_country_report = build_coverage_report(tmp_path)

    assert malformed_country_report.repository_status == "partial"
    assert malformed_country_report.warnings == ("invalid_country_root:uganda",)


def test_inventory_flags_unexpected_and_unsafe_country_entries(tmp_path: Path) -> None:
    """Unexpected countries and symlinked expected roots are static, non-sensitive warnings."""
    curricula_path = tmp_path / "curricula"
    ghana_path = curricula_path / "ghana"
    ghana_path.mkdir(parents=True)
    (curricula_path / "unplanned-country").mkdir()
    (curricula_path / ".hidden-country").mkdir()
    (curricula_path / "uganda").symlink_to(ghana_path, target_is_directory=True)

    report = build_coverage_report(tmp_path)

    assert report.repository_status == "partial"
    assert report.warnings == (
        "unsafe_country_root:uganda",
        "unexpected_country_entries",
    )
    assert report.countries[1].availability == "missing"


def test_inventory_fails_closed_when_a_country_root_cannot_be_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A permissions race cannot escape as a server error or ready status."""
    ghana_path, _uganda_path = _create_country_roots(tmp_path)
    original_iterdir = Path.iterdir

    def guarded_iterdir(path: Path) -> Iterator[Path]:
        if path == ghana_path:
            raise PermissionError("synthetic unreadable directory")
        return original_iterdir(path)

    monkeypatch.setattr(Path, "iterdir", guarded_iterdir)

    assert canonical_repository_available(tmp_path) is False
    report = build_coverage_report(tmp_path)
    assert report.repository_status == "partial"
    assert report.warnings == ("unreadable_country_root:ghana",)
    assert report.countries[0].availability == "missing"
