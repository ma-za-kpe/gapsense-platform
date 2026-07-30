"""Deterministic curriculum-release fixtures shared by contract tests."""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


_CATALOG_LEVELS = (
    ("GH", "primary", "kindergarten", "Kindergarten", 4),
    ("GH", "primary", "lower_primary", "Lower Primary", 8),
    ("GH", "primary", "upper_primary", "Upper Primary", 10),
    ("GH", "secondary", "junior_high", "Junior High", 12),
    ("GH", "secondary", "senior_high", "Senior High", 33),
    ("UG", "primary", "early_childhood", "Early Childhood", 6),
    ("UG", "primary", "primary_1_3", "Primary One–Three", 8),
    ("UG", "primary", "primary_4", "Primary Four", 10),
    ("UG", "primary", "primary_5_7", "Primary Five–Seven", 10),
    ("UG", "secondary", "lower_secondary", "Lower Secondary", 35),
    ("UG", "secondary", "upper_secondary", "Upper Secondary", 40),
)


def curriculum_catalog() -> dict[str, object]:
    """Build a structurally complete 176-cell official-authority test catalogue."""
    scopes = []
    for country, phase, level, level_name, area_count in _CATALOG_LEVELS:
        areas = []
        for index in range(area_count):
            if level in {"lower_primary", "upper_primary", "primary_1_3"} and index == 0:
                areas.append(["mathematics", "Mathematics"])
            else:
                areas.append([f"area-{index + 1}", f"Area {index + 1}"])
        scopes.append(
            {
                "country": country,
                "phase": phase,
                "levels": [[level, level_name]],
                "source_url": (
                    "https://nacca.gov.gh/curriculum/"
                    if country == "GH"
                    else "https://ncdc.go.ug/directorates/"
                ),
                "scope_note": f"Official scope statement for {level_name}.",
                "curriculum_areas": areas,
            }
        )
    return {
        "schema_version": "1.0.0",
        "as_of": "2026-07-29",
        "scope_status": "official_authority_inventory",
        "countries": ["GH", "UG"],
        "scopes": scopes,
    }


def write_catalog(
    data_path: Path,
    *,
    catalog: object | None = None,
) -> dict[str, str]:
    """Write and pin the fixed curriculum catalogue used by release fixtures."""
    catalog_path = data_path / "catalog" / "curriculum-catalog.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    payload = curriculum_catalog() if catalog is None else catalog
    catalog_bytes = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode()
    catalog_path.write_bytes(catalog_bytes)
    return {
        "path": "catalog/curriculum-catalog.json",
        "sha256": hashlib.sha256(catalog_bytes).hexdigest(),
    }


def source_catalog() -> dict[str, object]:
    """Build a mixed acquired/index-only source inventory for consumer tests."""
    return {
        "schema_version": "1.0.0",
        "as_of": "2026-07-23",
        "records": [
            {
                "id": "gh-jhs-official-index-current",
                "country": "GH",
                "authority": "National Council for Curriculum and Assessment (NaCCA)",
                "phase": "secondary",
                "level": "JHS1-JHS3",
                "subject": "all",
                "edition": "current Common Core Programme index",
                "source_url": "https://nacca.gov.gh/common-core-programme-ccp/",
                "retrieved_on": "2026-07-23",
                "license_status": "official_index_only_document_not_licensed_for_redistribution",
                "checksum_sha256": None,
                "artifact_path": None,
                "artifact_bytes": None,
                "artifact_pages": None,
                "extraction_status": "index_only",
                "review_status": "official_index_verified",
                "known_gap": "Expand the index into document records.",
            },
            {
                "id": "ug-lower-secondary-mathematics",
                "country": "UG",
                "authority": "National Curriculum Development Centre (NCDC)",
                "phase": "primary",
                "level": "P1-P3",
                "subject": "mathematics",
                "edition": "2019",
                "source_url": "https://ncdc.go.ug/resource/lower-secondary-mathematics/",
                "retrieved_on": "2026-07-23",
                "license_status": "all_rights_reserved_permission_required",
                "checksum_sha256": "a" * 64,
                "artifact_path": ("sources/documents/uganda/lower-secondary/2019/mathematics.pdf"),
                "artifact_bytes": 1024,
                "artifact_pages": 48,
                "extraction_status": "normalized_projection_unverified",
                "review_status": "official_artifact_byte_verified",
                "known_gap": "Structured extraction and human review remain.",
            },
        ],
    }


def write_source_catalog(
    data_path: Path,
    *,
    catalog: dict[str, object] | None = None,
) -> dict[str, str]:
    """Write and pin the sanitized source-evidence inventory fixture."""
    source_path = data_path / "sources" / "official-curriculum-sources.json"
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_bytes = (
        json.dumps(catalog or source_catalog(), ensure_ascii=False, indent=2) + "\n"
    ).encode()
    source_path.write_bytes(source_bytes)
    return {
        "path": "sources/official-curriculum-sources.json",
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
    }


def write_projection(
    data_path: Path,
    *,
    nodes: dict[str, object] | None = None,
    graph: dict[str, object] | None = None,
) -> dict[str, str]:
    """Write one deterministic Ghana Mathematics projection and return its contract."""
    subject_path = data_path / "curricula" / "ghana" / "primary" / "mathematics"
    subject_path.mkdir(parents=True, exist_ok=True)
    nodes_path = subject_path / "populated_nodes_complete.json"
    graph_path = subject_path / "prerequisite_graph_v1.2.json"
    nodes_bytes = (
        json.dumps(nodes or {"nodes_fully_populated": {}}, sort_keys=True) + "\n"
    ).encode()
    graph_bytes = (
        json.dumps(graph or {"nodes": {}, "strands": {}}, sort_keys=True) + "\n"
    ).encode()
    nodes_path.write_bytes(nodes_bytes)
    graph_path.write_bytes(graph_bytes)
    return {
        "nodes_path": "curricula/ghana/primary/mathematics/populated_nodes_complete.json",
        "nodes_sha256": hashlib.sha256(nodes_bytes).hexdigest(),
        "graph_path": "curricula/ghana/primary/mathematics/prerequisite_graph_v1.2.json",
        "graph_sha256": hashlib.sha256(graph_bytes).hexdigest(),
    }


def release_record(
    projection: dict[str, str] | None,
    **overrides: Any,
) -> dict[str, object]:
    """Build one exact local-only candidate record."""
    record: dict[str, object] = {
        "id": "gh-primary-lower-primary-mathematics",
        "country": "GH",
        "country_slug": "ghana",
        "authority": "National Council for Curriculum and Assessment (NaCCA)",
        "phase": "primary",
        "level": "lower_primary",
        "subject": "mathematics",
        "subject_name": "Mathematics",
        "source_edition": "2019",
        "valid_from": "2019-09-01",
        "valid_to": None,
        "maturity": "extracted",
        "review_status": "not_verified",
        "licensing_status": "all_rights_reserved_permission_required",
        "publication_profile": "local_only",
        "node_code_prefixes": ["B1.", "B2.", "B3."],
        "projection": projection,
    }
    record.update(overrides)
    return record


def write_release_manifest(
    data_path: Path,
    records: list[dict[str, object]],
    **overrides: Any,
) -> dict[str, object]:
    """Write the canonical manifest at the fixed consumer path."""
    catalog_reference = write_catalog(data_path)
    source_catalog_reference = write_source_catalog(data_path)
    manifest: dict[str, object] = {
        "schema_version": "1.0.0",
        "release_id": "curriculum-2026-07-29-candidate.1",
        "release_status": "candidate",
        "generated_on": "2026-07-29",
        "data_commit_sha": None,
        "complete": False,
        "countries": ["GH", "UG"],
        "catalog": catalog_reference,
        "source_catalog": source_catalog_reference,
        "record_count": len(records),
        "records": records,
    }
    manifest.update(overrides)
    release_path = data_path / "releases" / "curriculum-release.json"
    release_path.parent.mkdir(parents=True, exist_ok=True)
    release_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
