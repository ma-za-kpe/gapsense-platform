"""Validated, immutable curriculum release contract consumed from gapsense-data."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal, Never, cast

from gapsense.curriculum.inventory import (
    SourceInventory,
    SourceInventoryError,
    load_source_inventory,
)

ReleaseStatus = Literal["candidate", "released", "empty"]
Maturity = Literal[
    "missing",
    "located",
    "extracted",
    "structurally_validated",
    "human_reviewed",
]
ReviewStatus = Literal["not_verified", "human_reviewed"]
PublicationProfile = Literal["local_only", "public"]

_RELEASE_PATH = PurePosixPath("releases/curriculum-release.json")
_CATALOG_PATH = PurePosixPath("catalog/curriculum-catalog.json")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SAFE_IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
_SAFE_NODE_PREFIX = re.compile(r"^[A-Z0-9][A-Z0-9._-]{0,31}$")
_RELEASE_ID = re.compile(r"^curriculum-[a-z0-9][a-z0-9.-]{2,79}$")
_COUNTRY_SLUGS = {"GH": "ghana", "UG": "uganda"}
_COUNTRY_SOURCE_PREFIXES = {
    "GH": "https://nacca.gov.gh/",
    "UG": "https://ncdc.go.ug/",
}
_LEVEL_PHASES = {
    ("GH", "kindergarten"): "primary",
    ("GH", "lower_primary"): "primary",
    ("GH", "upper_primary"): "primary",
    ("GH", "junior_high"): "secondary",
    ("GH", "senior_high"): "secondary",
    ("UG", "early_childhood"): "primary",
    ("UG", "primary_1_3"): "primary",
    ("UG", "primary_4"): "primary",
    ("UG", "primary_5_7"): "primary",
    ("UG", "lower_secondary"): "secondary",
    ("UG", "upper_secondary"): "secondary",
}
_LEVEL_AREA_COUNTS = {
    ("GH", "kindergarten"): 4,
    ("GH", "lower_primary"): 8,
    ("GH", "upper_primary"): 10,
    ("GH", "junior_high"): 12,
    ("GH", "senior_high"): 33,
    ("UG", "early_childhood"): 6,
    ("UG", "primary_1_3"): 8,
    ("UG", "primary_4"): 10,
    ("UG", "primary_5_7"): 10,
    ("UG", "lower_secondary"): 35,
    ("UG", "upper_secondary"): 40,
}
_MATURITY_STATES = {
    "missing",
    "located",
    "extracted",
    "structurally_validated",
    "human_reviewed",
}
_REVIEW_STATES = {"not_verified", "human_reviewed"}


class ReleaseManifestError(ValueError):
    """The release contract cannot be trusted or its pinned bytes changed."""


@dataclass(frozen=True, slots=True)
class ReleaseProjection:
    """Two byte-pinned normalized artifacts used for safe detail projection."""

    nodes_path: Path
    nodes_sha256: str
    graph_path: Path
    graph_sha256: str


@dataclass(frozen=True, slots=True)
class CatalogCell:
    """One official country, phase, level, and curriculum-area catalogue cell."""

    country: Literal["GH", "UG"]
    phase: Literal["primary", "secondary"]
    level: str
    level_name: str
    subject: str
    subject_name: str
    source_url: str
    scope_note: str


@dataclass(frozen=True, slots=True)
class ReleaseRecord:
    """One exact country, phase, level, and subject release claim."""

    identifier: str
    country: Literal["GH", "UG"]
    country_slug: Literal["ghana", "uganda"]
    authority: str
    phase: Literal["primary", "secondary"]
    level: str
    subject: str
    subject_name: str
    source_edition: str
    maturity: Maturity
    review_status: ReviewStatus
    publication_profile: PublicationProfile
    node_code_prefixes: tuple[str, ...]
    projection: ReleaseProjection | None


@dataclass(frozen=True, slots=True)
class ReleaseManifest:
    """The complete immutable contract loaded once by the web application."""

    release_id: str
    release_status: ReleaseStatus
    data_commit_sha: str | None
    complete: Literal[False]
    catalog_as_of: str
    catalog_scope_status: Literal["official_authority_inventory"]
    catalog_cells: tuple[CatalogCell, ...]
    source_inventory: SourceInventory
    records: tuple[ReleaseRecord, ...]


def _fail(message: str) -> Never:
    raise ReleaseManifestError(message)


def _object(value: object, description: str) -> dict[str, object]:
    if not isinstance(value, dict):
        _fail(f"{description} must be a JSON object")
    return value


def _string(record: dict[str, object], field: str, identifier: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        _fail(f"Release record {identifier} field {field} must be a non-empty string")
    return value


def _exact_regular_file(data_path: Path, relative_path: PurePosixPath, description: str) -> Path:
    current = data_path
    for component in relative_path.parts:
        try:
            names = {child.name for child in current.iterdir()}
        except OSError:
            _fail(f"{description} is missing")
        if component not in names:
            if component.casefold() in {name.casefold() for name in names}:
                _fail(f"{description} path must use exact repository case")
            _fail(f"{description} is missing")
        current /= component
        if current.is_symlink():
            _fail(f"{description} must be a regular non-symlink file")
    if not current.is_file():
        _fail(f"{description} is missing")
    return current


def _catalog_pair(value: object, description: str) -> tuple[str, str]:
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not isinstance(value[0], str)
        or not _SAFE_IDENTIFIER.fullmatch(value[0])
        or not isinstance(value[1], str)
        or not value[1].strip()
    ):
        _fail(f"{description} must be a safe [identifier, name] pair")
    return value[0], value[1]


def _load_catalog(
    data_path: Path,
    raw_reference: object,
) -> tuple[str, Literal["official_authority_inventory"], tuple[CatalogCell, ...]]:
    reference = _object(raw_reference, "Curriculum release manifest catalog")
    if reference.get("path") != str(_CATALOG_PATH):
        _fail(f"Curriculum release manifest catalog path must be {_CATALOG_PATH}")
    expected_hash = reference.get("sha256")
    if not isinstance(expected_hash, str) or not _SHA256.fullmatch(expected_hash):
        _fail("Curriculum release manifest catalog sha256 must be lowercase SHA-256")

    catalog_path = _exact_regular_file(data_path, _CATALOG_PATH, "Curriculum catalog")
    try:
        catalog_bytes = catalog_path.read_bytes()
        value: object = json.loads(catalog_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseManifestError("Curriculum catalog contains invalid JSON") from error
    if hashlib.sha256(catalog_bytes).hexdigest() != expected_hash:
        _fail("Curriculum catalog SHA-256 changed")

    catalog = _object(value, "Curriculum catalog")
    if catalog.get("schema_version") != "1.0.0":
        _fail("Curriculum catalog schema_version must be 1.0.0")
    as_of = catalog.get("as_of")
    if not isinstance(as_of, str) or not _ISO_DATE.fullmatch(as_of):
        _fail("Curriculum catalog as_of is invalid")
    if catalog.get("scope_status") != "official_authority_inventory":
        _fail("Curriculum catalog scope_status is invalid")
    if catalog.get("countries") != ["GH", "UG"]:
        _fail("Curriculum catalog countries must be exactly GH and UG")
    raw_scopes = catalog.get("scopes")
    if not isinstance(raw_scopes, list) or not raw_scopes:
        _fail("Curriculum catalog scopes must be a non-empty array")

    cells: list[CatalogCell] = []
    observed_levels: set[tuple[str, str]] = set()
    subject_names: dict[tuple[str, str], str] = {}
    for raw_scope in raw_scopes:
        scope = _object(raw_scope, "Every curriculum catalog scope")
        country = scope.get("country")
        if not isinstance(country, str) or country not in _COUNTRY_SOURCE_PREFIXES:
            _fail("Curriculum catalog scope country must be GH or UG")
        phase = scope.get("phase")
        if not isinstance(phase, str) or phase not in {"primary", "secondary"}:
            _fail("Curriculum catalog scope phase is unsupported")
        source_url = scope.get("source_url")
        if not isinstance(source_url, str) or not source_url.startswith(
            _COUNTRY_SOURCE_PREFIXES[country]
        ):
            _fail(f"Curriculum catalog scope source_url must use the official {country} authority")
        scope_note = scope.get("scope_note")
        if not isinstance(scope_note, str) or not scope_note.strip():
            _fail("Curriculum catalog scope scope_note must be a non-empty string")
        raw_levels = scope.get("levels")
        if not isinstance(raw_levels, list) or not raw_levels:
            _fail("Curriculum catalog scope levels must be a non-empty array")
        raw_areas = scope.get("curriculum_areas")
        if not isinstance(raw_areas, list) or not raw_areas:
            _fail("Curriculum catalog scope curriculum_areas must be a non-empty array")
        areas = tuple(_catalog_pair(area, "Curriculum catalog area") for area in raw_areas)
        if len({identifier for identifier, _ in areas}) != len(areas):
            _fail("Curriculum catalog scope contains duplicate curriculum area identifiers")

        for raw_level in raw_levels:
            level, level_name = _catalog_pair(raw_level, "Curriculum catalog level")
            level_key = (country, level)
            if _LEVEL_PHASES.get(level_key) != phase:
                _fail(f"Curriculum catalog level {country}:{level} does not belong to its phase")
            if level_key in observed_levels:
                _fail(f"Curriculum catalog contains duplicate level: {country}:{level}")
            observed_levels.add(level_key)
            expected_count = _LEVEL_AREA_COUNTS[level_key]
            if len(areas) != expected_count:
                _fail(
                    f"Curriculum catalog level {country}:{level} must declare exactly "
                    f"{expected_count} curriculum areas"
                )
            for subject, subject_name in areas:
                name_key = (country, subject)
                if name_key in subject_names and subject_names[name_key] != subject_name:
                    _fail("Curriculum catalog subject names must be consistent within a country")
                subject_names[name_key] = subject_name
                cells.append(
                    CatalogCell(
                        country=cast(Literal["GH", "UG"], country),
                        phase=cast(Literal["primary", "secondary"], phase),
                        level=level,
                        level_name=level_name,
                        subject=subject,
                        subject_name=subject_name,
                        source_url=source_url,
                        scope_note=scope_note,
                    )
                )

    if observed_levels != set(_LEVEL_PHASES):
        _fail("Curriculum catalog must account for every declared GH and UG level exactly once")
    return as_of, "official_authority_inventory", tuple(cells)


def _safe_projection_path(
    data_path: Path,
    value: object,
    *,
    record: dict[str, object],
    field: str,
) -> Path:
    if not isinstance(value, str):
        _fail(f"Release record projection path {field} must be a string")
    relative_path = PurePosixPath(value)
    expected = PurePosixPath(
        "curricula",
        str(record["country_slug"]),
        str(record["phase"]),
        str(record["subject"]),
    )
    if (
        relative_path.is_absolute()
        or ".." in relative_path.parts
        or relative_path.suffix != ".json"
        or relative_path.parent != expected
    ):
        _fail(f"Release record projection path {field} is outside its subject boundary")

    candidate = data_path.joinpath(*relative_path.parts)
    current = data_path
    for component in relative_path.parts:
        current /= component
        if current.is_symlink():
            _fail(f"Release projection must be a regular non-symlink file: {value}")
    if not candidate.is_file():
        _fail(f"Release projection file is missing: {value}")
    return candidate


def _verified_projection(
    data_path: Path,
    raw_projection: object,
    record: dict[str, object],
) -> ReleaseProjection:
    projection = _object(raw_projection, "Release record projection")
    paths: dict[str, Path] = {}
    hashes: dict[str, str] = {}
    for kind in ("nodes", "graph"):
        path_field = f"{kind}_path"
        hash_field = f"{kind}_sha256"
        paths[kind] = _safe_projection_path(
            data_path,
            projection.get(path_field),
            record=record,
            field=path_field,
        )
        expected_hash = projection.get(hash_field)
        if not isinstance(expected_hash, str) or not _SHA256.fullmatch(expected_hash):
            _fail(f"Release record projection {hash_field} must be lowercase SHA-256")
        hashes[kind] = expected_hash
        actual_hash = hashlib.sha256(paths[kind].read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            _fail(f"Release projection SHA-256 changed: {projection[path_field]}")
    return ReleaseProjection(
        nodes_path=paths["nodes"],
        nodes_sha256=hashes["nodes"],
        graph_path=paths["graph"],
        graph_sha256=hashes["graph"],
    )


def _release_record(
    data_path: Path,
    value: object,
    *,
    manifest_status: ReleaseStatus,
) -> ReleaseRecord:
    record = _object(value, "Every release record")
    identifier_value = record.get("id")
    identifier = identifier_value if isinstance(identifier_value, str) else "<unknown>"
    required_fields = (
        "id",
        "country",
        "country_slug",
        "authority",
        "phase",
        "level",
        "subject",
        "subject_name",
        "source_edition",
        "valid_from",
        "maturity",
        "review_status",
        "licensing_status",
        "publication_profile",
    )
    values = {field: _string(record, field, identifier) for field in required_fields}

    if not _SAFE_IDENTIFIER.fullmatch(values["id"]):
        _fail(f"Release record {identifier} id is unsafe")
    country = values["country"]
    if country not in _COUNTRY_SLUGS:
        _fail(f"Release record {identifier} country must be GH or UG")
    if values["country_slug"] != _COUNTRY_SLUGS[country]:
        _fail(f"Release record {identifier} country_slug does not match country")
    phase = values["phase"]
    if phase not in {"primary", "secondary"}:
        _fail(f"Release record {identifier} phase is unsupported")
    level = values["level"]
    if _LEVEL_PHASES.get((country, level)) != phase:
        _fail(f"Release record {identifier} level does not belong to country and phase")
    if not _SAFE_IDENTIFIER.fullmatch(values["subject"]):
        _fail(f"Release record {identifier} subject is unsafe")
    if not _ISO_DATE.fullmatch(values["valid_from"]):
        _fail(f"Release record {identifier} valid_from is invalid")
    valid_to = record.get("valid_to")
    if valid_to is not None and (
        not isinstance(valid_to, str)
        or not _ISO_DATE.fullmatch(valid_to)
        or valid_to < values["valid_from"]
    ):
        _fail(f"Release record {identifier} valid_to is invalid")

    maturity = values["maturity"]
    if maturity not in _MATURITY_STATES:
        _fail(f"Release record {identifier} maturity is unsupported")
    review_status = values["review_status"]
    if review_status not in _REVIEW_STATES:
        _fail(f"Release record {identifier} review_status is unsupported")
    publication_profile = values["publication_profile"]
    if publication_profile not in {"local_only", "public"}:
        _fail(f"Release record {identifier} publication_profile is unsupported")

    prefixes = record.get("node_code_prefixes")
    if (
        not isinstance(prefixes, list)
        or not prefixes
        or not all(
            isinstance(prefix, str) and _SAFE_NODE_PREFIX.fullmatch(prefix) for prefix in prefixes
        )
    ):
        _fail(f"Release record {identifier} node_code_prefixes are invalid")

    raw_projection = record.get("projection")
    if maturity in {"missing", "located"}:
        if raw_projection is not None:
            _fail(f"Release record {identifier} unextracted records must not declare a projection")
        projection = None
    else:
        if raw_projection is None:
            _fail(f"Release record {identifier} extracted records require a projection")
        projection = _verified_projection(data_path, raw_projection, record)

    if publication_profile == "public":
        if (
            maturity != "human_reviewed"
            or review_status != "human_reviewed"
            or values["licensing_status"] != "approved_for_public_projection"
        ):
            _fail(f"Release record {identifier} public evidence is not reviewed and approved")
        if manifest_status != "released":
            _fail(f"Release record {identifier} public evidence requires a released manifest")

    return ReleaseRecord(
        identifier=values["id"],
        country=cast(Literal["GH", "UG"], country),
        country_slug=cast(Literal["ghana", "uganda"], values["country_slug"]),
        authority=values["authority"],
        phase=cast(Literal["primary", "secondary"], phase),
        level=level,
        subject=values["subject"],
        subject_name=values["subject_name"],
        source_edition=values["source_edition"],
        maturity=cast(Maturity, maturity),
        review_status=cast(ReviewStatus, review_status),
        publication_profile=cast(PublicationProfile, publication_profile),
        node_code_prefixes=tuple(cast(list[str], prefixes)),
        projection=projection,
    )


def load_release_manifest(data_path: Path) -> ReleaseManifest:
    """Load and byte-verify the fixed data release manifest, failing closed."""
    release_path = _exact_regular_file(
        data_path,
        _RELEASE_PATH,
        "Curriculum release manifest",
    )
    try:
        value: object = json.loads(release_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReleaseManifestError("Curriculum release manifest contains invalid JSON") from error
    manifest = _object(value, "Curriculum release manifest")

    if manifest.get("schema_version") != "1.0.0":
        _fail("Curriculum release manifest schema_version must be 1.0.0")
    release_id = manifest.get("release_id")
    if not isinstance(release_id, str) or not _RELEASE_ID.fullmatch(release_id):
        _fail("Curriculum release manifest release_id is invalid")
    release_status_value = manifest.get("release_status")
    if not isinstance(release_status_value, str) or release_status_value not in {
        "candidate",
        "released",
        "empty",
    }:
        _fail("Curriculum release manifest release_status is invalid")
    release_status = cast(ReleaseStatus, release_status_value)
    generated_on = manifest.get("generated_on")
    if not isinstance(generated_on, str) or not _ISO_DATE.fullmatch(generated_on):
        _fail("Curriculum release manifest generated_on is invalid")
    data_commit_sha = manifest.get("data_commit_sha")
    if data_commit_sha is not None and (
        not isinstance(data_commit_sha, str) or not _GIT_SHA.fullmatch(data_commit_sha)
    ):
        _fail("Curriculum release manifest data_commit_sha is invalid")
    if release_status == "released" and data_commit_sha is None:
        _fail("A released curriculum manifest requires data_commit_sha")
    if manifest.get("complete") is not False:
        _fail("Curriculum release manifest complete must remain false")
    if manifest.get("countries") != ["GH", "UG"]:
        _fail("Curriculum release manifest countries must be exactly GH and UG")
    catalog_as_of, catalog_scope_status, catalog_cells = _load_catalog(
        data_path,
        manifest.get("catalog"),
    )
    try:
        source_inventory = load_source_inventory(
            data_path,
            manifest.get("source_catalog"),
        )
    except SourceInventoryError as error:
        raise ReleaseManifestError(str(error)) from error
    if catalog_as_of > generated_on:
        _fail("Curriculum catalog as_of must not follow the release generated_on date")
    if source_inventory.as_of > generated_on:
        _fail("Source inventory as_of must not follow the release generated_on date")

    raw_records = manifest.get("records")
    if not isinstance(raw_records, list):
        _fail("Curriculum release manifest records must be an array")
    if manifest.get("record_count") != len(raw_records):
        _fail("Curriculum release manifest record_count does not match records")
    if release_status == "empty" and raw_records:
        _fail("An empty curriculum release manifest must contain zero records")
    if release_status != "empty" and not raw_records:
        _fail("A non-empty curriculum release manifest must contain records")

    records = tuple(
        _release_record(
            data_path,
            record,
            manifest_status=release_status,
        )
        for record in raw_records
    )
    identifiers: set[str] = set()
    combinations: set[tuple[str, str, str, str]] = set()
    catalog_index = {
        (cell.country, cell.phase, cell.level, cell.subject): cell for cell in catalog_cells
    }
    for record in records:
        if record.identifier in identifiers:
            _fail(f"Curriculum release manifest contains duplicate id: {record.identifier}")
        identifiers.add(record.identifier)
        combination = (record.country, record.phase, record.level, record.subject)
        if combination in combinations:
            _fail("Curriculum release manifest contains duplicate curriculum combination")
        combinations.add(combination)
        catalog_cell = catalog_index.get(combination)
        if catalog_cell is None or catalog_cell.subject_name != record.subject_name:
            _fail(
                f"Release record {record.identifier} must exactly match a curriculum catalog cell"
            )

    return ReleaseManifest(
        release_id=release_id,
        release_status=release_status,
        data_commit_sha=data_commit_sha,
        complete=False,
        catalog_as_of=catalog_as_of,
        catalog_scope_status=catalog_scope_status,
        catalog_cells=catalog_cells,
        source_inventory=source_inventory,
        records=records,
    )
