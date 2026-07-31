"""Tests for the pinned, sanitized source-evidence inventory."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

import pytest
from tests.curriculum_release import source_catalog, write_source_catalog

from gapsense.curriculum.inventory import SourceInventoryError, load_source_inventory

if TYPE_CHECKING:
    from pathlib import Path


def test_source_inventory_loads_every_sanitized_record(tmp_path: Path) -> None:
    reference = write_source_catalog(tmp_path)

    inventory = load_source_inventory(tmp_path, reference)

    assert inventory.as_of == "2026-07-23"
    assert len(inventory.records) == 2
    index_record, artifact_record = inventory.records
    assert index_record.country == "GH"
    assert index_record.phase == "secondary"
    assert index_record.artifact_available is False
    assert index_record.artifact_pages is None
    assert index_record.extraction_status == "index_only"
    assert (
        index_record.license_status
        == "official_index_only_document_not_licensed_for_redistribution"
    )
    assert artifact_record.country == "UG"
    assert artifact_record.phase == "primary"
    assert artifact_record.artifact_available is True
    assert artifact_record.artifact_pages == 48
    assert artifact_record.subject == "mathematics"
    assert artifact_record.extraction_status == "normalized_projection_unverified"


@pytest.mark.parametrize(
    ("reference", "message"),
    [
        (None, "must be a JSON object"),
        (
            {"path": "sources/latest.json", "sha256": "a" * 64},
            "path must be",
        ),
        (
            {
                "path": "sources/official-curriculum-sources.json",
                "sha256": "ABC",
            },
            "lowercase SHA-256",
        ),
    ],
)
def test_source_inventory_rejects_invalid_release_references(
    tmp_path: Path,
    reference: object,
    message: str,
) -> None:
    with pytest.raises(SourceInventoryError, match=message):
        load_source_inventory(tmp_path, reference)


def test_source_inventory_rejects_missing_wrong_case_symlink_and_non_file(
    tmp_path: Path,
) -> None:
    reference = {
        "path": "sources/official-curriculum-sources.json",
        "sha256": "a" * 64,
    }
    with pytest.raises(SourceInventoryError, match="missing"):
        load_source_inventory(tmp_path / "absent", reference)
    with pytest.raises(SourceInventoryError, match="missing"):
        load_source_inventory(tmp_path, reference)

    exact_reference = write_source_catalog(tmp_path)
    sources = tmp_path / "sources"
    sources.rename(tmp_path / "Sources")
    with pytest.raises(SourceInventoryError, match="exact repository case"):
        load_source_inventory(tmp_path, exact_reference)

    wrong_case_sources = tmp_path / "Sources"
    wrong_case_sources.rename(sources)
    source_path = sources / "official-curriculum-sources.json"
    target_path = sources / "target.json"
    source_path.rename(target_path)
    source_path.symlink_to(target_path)
    with pytest.raises(SourceInventoryError, match="non-symlink"):
        load_source_inventory(tmp_path, exact_reference)

    source_path.unlink()
    source_path.mkdir()
    with pytest.raises(SourceInventoryError, match="missing"):
        load_source_inventory(tmp_path, exact_reference)


def test_source_inventory_rejects_changed_and_malformed_bytes(tmp_path: Path) -> None:
    reference = write_source_catalog(tmp_path)
    source_path = tmp_path / reference["path"]
    source_path.write_text("{}", encoding="utf-8")
    with pytest.raises(SourceInventoryError, match="SHA-256 changed"):
        load_source_inventory(tmp_path, reference)

    invalid_bytes = b"\xff"
    source_path.write_bytes(invalid_bytes)
    invalid_reference = {
        **reference,
        "sha256": hashlib.sha256(invalid_bytes).hexdigest(),
    }
    with pytest.raises(SourceInventoryError, match="invalid JSON"):
        load_source_inventory(tmp_path, invalid_reference)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"schema_version": "latest"}, "schema_version"),
        ({"as_of": "today"}, "as_of"),
        ({"records": []}, "non-empty array"),
        ({"records": {}}, "non-empty array"),
    ],
)
def test_source_inventory_rejects_invalid_catalog_metadata(
    tmp_path: Path,
    mutation: dict[str, object],
    message: str,
) -> None:
    catalog = source_catalog()
    catalog.update(mutation)
    reference = write_source_catalog(tmp_path, catalog=catalog)

    with pytest.raises(SourceInventoryError, match=message):
        load_source_inventory(tmp_path, reference)


def test_source_inventory_requires_a_catalog_object(tmp_path: Path) -> None:
    source_path = tmp_path / "sources" / "official-curriculum-sources.json"
    source_path.parent.mkdir(parents=True)
    source_bytes = b"[]"
    source_path.write_bytes(source_bytes)

    with pytest.raises(SourceInventoryError, match="must be a JSON object"):
        load_source_inventory(
            tmp_path,
            {
                "path": "sources/official-curriculum-sources.json",
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
            },
        )


def test_source_inventory_rejects_records_retrieved_after_as_of(tmp_path: Path) -> None:
    catalog = source_catalog()
    catalog["as_of"] = "2026-07-22"
    reference = write_source_catalog(tmp_path, catalog=catalog)

    with pytest.raises(SourceInventoryError, match="must not follow the inventory as_of"):
        load_source_inventory(tmp_path, reference)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (None, "must be a JSON object"),
        ({"id": ""}, "field id"),
        ({"id": "../unsafe"}, "id is unsafe"),
        ({"country": "KE"}, "country must be GH or UG"),
        ({"authority": "Unknown"}, "authority must match its country"),
        ({"phase": "tertiary"}, "phase must be primary or secondary"),
        ({"source_url": "https://example.com/"}, "not an official authority"),
        ({"retrieved_on": "today"}, "retrieved_on"),
        ({"license_status": "public_domain"}, "license_status"),
        ({"extraction_status": "complete"}, "extraction_status"),
        ({"review_status": "approved"}, "review_status"),
        (
            {"artifact_path": None, "checksum_sha256": "a" * 64},
            "absent artifacts require null metadata",
        ),
        (
            {"artifact_path": None, "artifact_pages": 1},
            "absent artifacts require null metadata",
        ),
        ({"artifact_path": 42}, "artifact metadata is invalid"),
        (
            {
                "artifact_path": "../unsafe.pdf",
                "checksum_sha256": "invalid",
                "artifact_bytes": True,
            },
            "artifact metadata is invalid",
        ),
    ],
)
def test_source_inventory_rejects_unsafe_records(
    tmp_path: Path,
    mutation: dict[str, object] | None,
    message: str,
) -> None:
    catalog = source_catalog()
    records = catalog["records"]
    assert isinstance(records, list)
    if mutation is None:
        records[0] = None
    else:
        assert isinstance(records[0], dict)
        records[0].update(mutation)
    reference = write_source_catalog(tmp_path, catalog=catalog)

    with pytest.raises(SourceInventoryError, match=message):
        load_source_inventory(tmp_path, reference)


@pytest.mark.parametrize("artifact_pages", [None, True, 0])
def test_source_inventory_rejects_invalid_artifact_page_counts(
    tmp_path: Path,
    artifact_pages: object,
) -> None:
    catalog = source_catalog()
    records = catalog["records"]
    assert isinstance(records, list)
    assert isinstance(records[1], dict)
    records[1]["artifact_pages"] = artifact_pages
    reference = write_source_catalog(tmp_path, catalog=catalog)

    with pytest.raises(SourceInventoryError, match="artifact metadata is invalid"):
        load_source_inventory(tmp_path, reference)


def test_source_inventory_rejects_duplicate_identifiers(tmp_path: Path) -> None:
    catalog = source_catalog()
    records = catalog["records"]
    assert isinstance(records, list)
    assert isinstance(records[0], dict)
    assert isinstance(records[1], dict)
    records[1]["id"] = records[0]["id"]
    reference = write_source_catalog(tmp_path, catalog=catalog)

    with pytest.raises(SourceInventoryError, match="duplicate id"):
        load_source_inventory(tmp_path, reference)


def test_source_inventory_rejects_invalid_json_text(tmp_path: Path) -> None:
    source_path = tmp_path / "sources" / "official-curriculum-sources.json"
    source_path.parent.mkdir(parents=True)
    source_bytes = b"{"
    source_path.write_bytes(source_bytes)
    reference = {
        "path": "sources/official-curriculum-sources.json",
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
    }

    with pytest.raises(SourceInventoryError, match="invalid JSON"):
        load_source_inventory(tmp_path, reference)


def test_source_inventory_accepts_json_serialized_with_ascii(tmp_path: Path) -> None:
    source_path = tmp_path / "sources" / "official-curriculum-sources.json"
    source_path.parent.mkdir(parents=True)
    source_bytes = json.dumps(source_catalog()).encode()
    source_path.write_bytes(source_bytes)

    inventory = load_source_inventory(
        tmp_path,
        {
            "path": "sources/official-curriculum-sources.json",
            "sha256": hashlib.sha256(source_bytes).hexdigest(),
        },
    )

    assert inventory.records[0].identifier == "gh-jhs-official-index-current"
