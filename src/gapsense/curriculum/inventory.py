"""Pinned, sanitized source-evidence inventory from gapsense-data."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Never, cast

SourceExtractionStatus = Literal[
    "index_only",
    "not_extracted",
    "normalized_projection_unverified",
    "text_present_unverified",
]
SourceLicenseStatus = Literal[
    "all_rights_reserved_permission_required",
    "official_index_only_document_not_licensed_for_redistribution",
    "restricted_internal_research_permission_required_for_redistribution",
]
SourceReviewStatus = Literal[
    "legacy_artifact_byte_verified_provenance_reacquisition_pending",
    "official_artifact_byte_verified",
    "official_artifact_byte_verified_document_phase_review_pending",
    "official_document_identity_pending_binary_comparison",
    "official_index_and_framework_verified",
    "official_index_verified",
]

_SOURCE_CATALOG_PATH = PurePosixPath("sources/official-curriculum-sources.json")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,119}$")
_SOURCE_PREFIXES = {
    "GH": "https://nacca.gov.gh/",
    "UG": "https://ncdc.go.ug/",
}
_AUTHORITIES = {
    "GH": "National Council for Curriculum and Assessment (NaCCA)",
    "UG": "National Curriculum Development Centre (NCDC)",
}
_EXTRACTION_STATES = {
    "index_only",
    "not_extracted",
    "normalized_projection_unverified",
    "text_present_unverified",
}
_LICENSE_STATES = {
    "all_rights_reserved_permission_required",
    "official_index_only_document_not_licensed_for_redistribution",
    "restricted_internal_research_permission_required_for_redistribution",
}
_REVIEW_STATES = {
    "legacy_artifact_byte_verified_provenance_reacquisition_pending",
    "official_artifact_byte_verified",
    "official_artifact_byte_verified_document_phase_review_pending",
    "official_document_identity_pending_binary_comparison",
    "official_index_and_framework_verified",
    "official_index_verified",
}


class SourceInventoryError(ValueError):
    """The pinned source inventory is absent, changed, or structurally unsafe."""


@dataclass(frozen=True, slots=True)
class SourceInventoryRecord:
    """One sanitized official-source record safe for public accounting."""

    identifier: str
    country: Literal["GH", "UG"]
    phase: Literal["primary", "secondary"]
    level: str
    subject: str
    edition: str
    source_url: str
    retrieved_on: str
    license_status: SourceLicenseStatus
    artifact_available: bool
    artifact_pages: int | None
    extraction_status: SourceExtractionStatus
    review_status: SourceReviewStatus
    known_gap: str


@dataclass(frozen=True, slots=True)
class SourceInventory:
    """A byte-pinned source snapshot and all of its sanitized records."""

    as_of: str
    records: tuple[SourceInventoryRecord, ...]


def _fail(message: str) -> Never:
    raise SourceInventoryError(message)


def _object(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{description} must be a JSON object")
    return value


def _required_string(record: dict[str, object], field: str, identifier: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"Source inventory record {identifier} field {field} must be a non-empty string")
    return value


def _source_catalog_file(data_path: Path) -> Path:
    current = data_path
    for component in _SOURCE_CATALOG_PATH.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            _fail("Source inventory is missing")
        if component not in names:
            if component.casefold() in {name.casefold() for name in names}:
                _fail("Source inventory path must use exact repository case")
            _fail("Source inventory is missing")
        current /= component
        if current.is_symlink():
            _fail("Source inventory must be a regular non-symlink file")
    if not current.is_file():
        _fail("Source inventory is missing")
    return current


def _artifact_metadata(
    record: dict[str, object],
    identifier: str,
) -> tuple[bool, int | None]:
    artifact_path = record.get("artifact_path")
    checksum = record.get("checksum_sha256")
    artifact_bytes = record.get("artifact_bytes")
    artifact_pages = record.get("artifact_pages")
    if artifact_path is None:
        if checksum is not None or artifact_bytes is not None or artifact_pages is not None:
            _fail(f"Source inventory record {identifier} absent artifacts require null metadata")
        return False, None
    if not isinstance(artifact_path, str):
        _fail(f"Source inventory record {identifier} artifact metadata is invalid")
    relative_path = PurePosixPath(artifact_path)
    if (
        relative_path.is_absolute()
        or relative_path.suffix != ".pdf"
        or not relative_path.parts
        or relative_path.parts[0] not in {"curricula", "sources"}
        or "\\" in artifact_path
        or ".." in relative_path.parts
        or not isinstance(checksum, str)
        or not _SHA256.fullmatch(checksum)
        or not isinstance(artifact_bytes, int)
        or isinstance(artifact_bytes, bool)
        or artifact_bytes <= 0
        or not isinstance(artifact_pages, int)
        or isinstance(artifact_pages, bool)
        or artifact_pages <= 0
    ):
        _fail(f"Source inventory record {identifier} artifact metadata is invalid")
    return True, artifact_pages


def load_source_inventory(data_path: Path, raw_reference: object) -> SourceInventory:
    """Load a fixed, hash-pinned source catalogue and expose sanitized metadata."""
    reference = _object(raw_reference, "Curriculum release manifest source_catalog")
    if reference.get("path") != str(_SOURCE_CATALOG_PATH):
        _fail(f"Source inventory path must be {_SOURCE_CATALOG_PATH}")
    expected_hash = reference.get("sha256")
    if not isinstance(expected_hash, str) or not _SHA256.fullmatch(expected_hash):
        _fail("Source inventory sha256 must be lowercase SHA-256")

    source_path = _source_catalog_file(data_path)
    try:
        source_bytes = source_path.read_bytes()
        value: object = json.loads(source_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SourceInventoryError("Source inventory contains invalid JSON") from error
    if hashlib.sha256(source_bytes).hexdigest() != expected_hash:
        _fail("Source inventory SHA-256 changed")

    catalog = _object(value, "Source inventory")
    if catalog.get("schema_version") != "1.0.0":
        _fail("Source inventory schema_version must be 1.0.0")
    as_of = catalog.get("as_of")
    if not isinstance(as_of, str) or not _ISO_DATE.fullmatch(as_of):
        _fail("Source inventory as_of is invalid")
    raw_records = catalog.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        _fail("Source inventory records must be a non-empty array")

    records: list[SourceInventoryRecord] = []
    identifiers: set[str] = set()
    for raw_record in raw_records:
        record = _object(raw_record, "Every source inventory record")
        raw_identifier = record.get("id")
        identifier = raw_identifier if isinstance(raw_identifier, str) else "<unknown>"
        values = {
            field: _required_string(record, field, identifier)
            for field in (
                "id",
                "country",
                "authority",
                "phase",
                "level",
                "subject",
                "edition",
                "source_url",
                "retrieved_on",
                "license_status",
                "extraction_status",
                "review_status",
                "known_gap",
            )
        }
        if not _SAFE_IDENTIFIER.fullmatch(values["id"]):
            _fail(f"Source inventory record {identifier} id is unsafe")
        if values["id"] in identifiers:
            _fail(f"Source inventory contains duplicate id: {values['id']}")
        identifiers.add(values["id"])
        country = values["country"]
        if country not in _SOURCE_PREFIXES:
            _fail(f"Source inventory record {identifier} country must be GH or UG")
        if values["authority"] != _AUTHORITIES[country]:
            _fail(f"Source inventory record {identifier} authority must match its country")
        phase = values["phase"]
        if phase not in {"primary", "secondary"}:
            _fail(f"Source inventory record {identifier} phase must be primary or secondary")
        if not values["source_url"].startswith(_SOURCE_PREFIXES[country]):
            _fail(f"Source inventory record {identifier} source_url is not an official authority")
        if not _ISO_DATE.fullmatch(values["retrieved_on"]):
            _fail(f"Source inventory record {identifier} retrieved_on is invalid")
        if values["retrieved_on"] > as_of:
            _fail(
                f"Source inventory record {identifier} retrieved_on "
                "must not follow the inventory as_of date"
            )
        license_status = values["license_status"]
        if license_status not in _LICENSE_STATES:
            _fail(f"Source inventory record {identifier} license_status is unsupported")
        extraction_status = values["extraction_status"]
        if extraction_status not in _EXTRACTION_STATES:
            _fail(f"Source inventory record {identifier} extraction_status is unsupported")
        review_status = values["review_status"]
        if review_status not in _REVIEW_STATES:
            _fail(f"Source inventory record {identifier} review_status is unsupported")
        artifact_available, artifact_pages = _artifact_metadata(record, identifier)
        records.append(
            SourceInventoryRecord(
                identifier=values["id"],
                country=cast(Literal["GH", "UG"], country),
                phase=cast(Literal["primary", "secondary"], phase),
                level=values["level"],
                subject=values["subject"],
                edition=values["edition"],
                source_url=values["source_url"],
                retrieved_on=values["retrieved_on"],
                license_status=cast(SourceLicenseStatus, license_status),
                artifact_available=artifact_available,
                artifact_pages=artifact_pages,
                extraction_status=cast(SourceExtractionStatus, extraction_status),
                review_status=cast(SourceReviewStatus, review_status),
                known_gap=values["known_gap"],
            )
        )
    return SourceInventory(as_of=as_of, records=tuple(records))
