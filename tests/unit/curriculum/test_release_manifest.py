"""Tests for the untrusted cross-repository curriculum release boundary."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from typing import TYPE_CHECKING

import pytest
from tests.curriculum_release import (
    curriculum_catalog,
    release_record,
    source_catalog,
    write_catalog,
    write_projection,
    write_release_manifest,
    write_source_catalog,
)

from gapsense.curriculum.release import ReleaseManifestError, load_release_manifest

if TYPE_CHECKING:
    from pathlib import Path


def test_release_manifest_loads_exact_hash_verified_records(tmp_path: Path) -> None:
    projection = write_projection(tmp_path)
    lower = release_record(projection)
    upper = release_record(
        projection,
        id="gh-primary-upper-primary-mathematics",
        level="upper_primary",
        node_code_prefixes=["B4.", "B5.", "B6."],
    )
    write_release_manifest(tmp_path, [lower, upper])

    manifest = load_release_manifest(tmp_path)

    assert manifest.release_id == "curriculum-2026-07-29-candidate.1"
    assert manifest.release_status == "candidate"
    assert manifest.data_commit_sha is None
    assert manifest.complete is False
    assert manifest.catalog_as_of == "2026-07-29"
    assert len(manifest.catalog_cells) == 176
    assert len(manifest.source_inventory.records) == 2
    assert [record.level for record in manifest.records] == [
        "lower_primary",
        "upper_primary",
    ]
    assert manifest.records[0].projection is not None
    assert manifest.records[0].projection.nodes_path == (tmp_path / projection["nodes_path"])
    assert manifest.records[0].projection.nodes_sha256 == projection["nodes_sha256"]


def test_release_manifest_accepts_explicit_missing_and_empty_records(tmp_path: Path) -> None:
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

    manifest = load_release_manifest(tmp_path)

    assert manifest.records[0].projection is None
    assert manifest.records[0].maturity == "missing"

    write_release_manifest(
        tmp_path,
        [],
        release_id="curriculum-public-empty-1",
        release_status="empty",
    )
    assert load_release_manifest(tmp_path).records == ()

    projection = write_projection(tmp_path)
    reviewed = release_record(
        projection,
        maturity="human_reviewed",
        review_status="human_reviewed",
        licensing_status="approved_for_public_projection",
        publication_profile="public",
        valid_to="2024-08-31",
    )
    write_release_manifest(
        tmp_path,
        [reviewed],
        release_id="curriculum-1.0.0",
        release_status="released",
        data_commit_sha="a" * 40,
    )
    released = load_release_manifest(tmp_path)
    assert released.release_status == "released"
    assert released.records[0].publication_profile == "public"


def test_release_manifest_rejects_catalogues_dated_after_the_release(tmp_path: Path) -> None:
    projection = write_projection(tmp_path)
    manifest = write_release_manifest(tmp_path, [release_record(projection)])
    future_catalog = curriculum_catalog()
    future_catalog["as_of"] = "2026-07-30"
    manifest["catalog"] = write_catalog(tmp_path, catalog=future_catalog)
    (tmp_path / "releases" / "curriculum-release.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ReleaseManifestError, match="Curriculum catalog as_of must not follow"):
        load_release_manifest(tmp_path)

    manifest = write_release_manifest(tmp_path, [release_record(projection)])
    source = source_catalog()
    source["as_of"] = "2026-07-30"
    manifest["source_catalog"] = write_source_catalog(tmp_path, catalog=source)
    (tmp_path / "releases" / "curriculum-release.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(ReleaseManifestError, match="Source inventory as_of must not follow"):
        load_release_manifest(tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ({"schema_version": "latest"}, "schema_version"),
        ({"release_id": "latest"}, "release_id"),
        ({"release_status": "draft"}, "release_status"),
        ({"generated_on": "today"}, "generated_on"),
        ({"data_commit_sha": "abc"}, "data_commit_sha"),
        (
            {"release_status": "released", "data_commit_sha": None},
            "requires data_commit_sha",
        ),
        ({"complete": True}, "complete"),
        ({"countries": ["GH"]}, "countries"),
        ({"catalog": None}, "catalog must be a JSON object"),
        (
            {"catalog": {"path": "catalog/latest.json", "sha256": "a" * 64}},
            "catalog path",
        ),
        (
            {
                "catalog": {
                    "path": "catalog/curriculum-catalog.json",
                    "sha256": "ABC",
                }
            },
            "catalog sha256",
        ),
        ({"source_catalog": None}, "source_catalog must be a JSON object"),
        ({"record_count": 2}, "record_count"),
        ({"records": {}}, "records"),
        ({"release_status": "empty"}, "must contain zero records"),
        ({"records": [], "record_count": 0}, "must contain records"),
    ],
)
def test_release_manifest_rejects_invalid_metadata(
    tmp_path: Path,
    mutation: dict[str, object],
    message: str,
) -> None:
    projection = write_projection(tmp_path)
    manifest = write_release_manifest(tmp_path, [release_record(projection)])
    manifest.update(mutation)
    (tmp_path / "releases" / "curriculum-release.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    with pytest.raises(ReleaseManifestError, match=message):
        load_release_manifest(tmp_path)


def test_release_manifest_rejects_missing_malformed_and_duplicate_records(
    tmp_path: Path,
) -> None:
    with pytest.raises(ReleaseManifestError, match="missing"):
        load_release_manifest(tmp_path)
    with pytest.raises(ReleaseManifestError, match="missing"):
        load_release_manifest(tmp_path / "absent")

    release_path = tmp_path / "releases" / "curriculum-release.json"
    release_path.parent.mkdir(parents=True)
    release_path.write_text("{", encoding="utf-8")
    with pytest.raises(ReleaseManifestError, match="invalid JSON"):
        load_release_manifest(tmp_path)

    release_path.write_text("[]", encoding="utf-8")
    with pytest.raises(ReleaseManifestError, match="JSON object"):
        load_release_manifest(tmp_path)

    write_release_manifest(tmp_path, [None])  # type: ignore[list-item]
    with pytest.raises(ReleaseManifestError, match="Every release record"):
        load_release_manifest(tmp_path)

    projection = write_projection(tmp_path)
    record = release_record(projection)
    write_release_manifest(tmp_path, [record, record])
    with pytest.raises(ReleaseManifestError, match="duplicate"):
        load_release_manifest(tmp_path)

    duplicate_combination = release_record(projection, id="different-id")
    write_release_manifest(tmp_path, [record, duplicate_combination])
    with pytest.raises(ReleaseManifestError, match="duplicate curriculum combination"):
        load_release_manifest(tmp_path)

    write_release_manifest(
        tmp_path,
        [release_record(projection, subject_name="Wrong name")],
    )
    with pytest.raises(ReleaseManifestError, match="exactly match"):
        load_release_manifest(tmp_path)


def _catalog_mutation(case: str) -> object:
    catalog = deepcopy(curriculum_catalog())
    scopes = catalog["scopes"]
    assert isinstance(scopes, list)
    if case == "object":
        return []
    if case == "schema":
        catalog["schema_version"] = "latest"
    elif case == "as_of":
        catalog["as_of"] = "today"
    elif case == "scope_status":
        catalog["scope_status"] = "complete"
    elif case == "countries":
        catalog["countries"] = ["GH"]
    elif case == "scopes":
        catalog["scopes"] = []
    elif case == "scope_object":
        catalog["scopes"] = [None]
    elif case == "country":
        assert isinstance(scopes[0], dict)
        scopes[0]["country"] = "KE"
    elif case == "phase":
        assert isinstance(scopes[0], dict)
        scopes[0]["phase"] = "tertiary"
    elif case == "source_url":
        assert isinstance(scopes[0], dict)
        scopes[0]["source_url"] = "https://example.com/"
    elif case == "scope_note":
        assert isinstance(scopes[0], dict)
        scopes[0]["scope_note"] = " "
    elif case == "levels":
        assert isinstance(scopes[0], dict)
        scopes[0]["levels"] = []
    elif case == "areas":
        assert isinstance(scopes[0], dict)
        scopes[0]["curriculum_areas"] = []
    elif case == "area_pair":
        assert isinstance(scopes[0], dict)
        scopes[0]["curriculum_areas"] = [["Unsafe!", ""]]
    elif case == "duplicate_area":
        assert isinstance(scopes[0], dict)
        areas = scopes[0]["curriculum_areas"]
        assert isinstance(areas, list)
        areas[-1] = areas[0]
    elif case == "level_pair":
        assert isinstance(scopes[0], dict)
        scopes[0]["levels"] = [["Unsafe!", ""]]
    elif case == "level_phase":
        assert isinstance(scopes[0], dict)
        scopes[0]["levels"] = [["lower_secondary", "Wrong country"]]
    elif case == "duplicate_level":
        scopes.append(deepcopy(scopes[0]))
    elif case == "area_count":
        assert isinstance(scopes[0], dict)
        areas = scopes[0]["curriculum_areas"]
        assert isinstance(areas, list)
        scopes[0]["curriculum_areas"] = areas[:-1]
    elif case == "subject_name":
        assert isinstance(scopes[2], dict)
        areas = scopes[2]["curriculum_areas"]
        assert isinstance(areas, list)
        assert isinstance(areas[1], list)
        areas[1][1] = "A different name"
    elif case == "missing_level":
        catalog["scopes"] = scopes[1:]
    else:
        raise AssertionError(f"Unhandled catalogue mutation: {case}")
    return catalog


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("object", "must be a JSON object"),
        ("schema", "schema_version"),
        ("as_of", "as_of"),
        ("scope_status", "scope_status"),
        ("countries", "countries"),
        ("scopes", "non-empty array"),
        ("scope_object", "scope must be a JSON object"),
        ("country", "country must be GH or UG"),
        ("phase", "phase is unsupported"),
        ("source_url", "official GH authority"),
        ("scope_note", "scope_note must be a non-empty string"),
        ("levels", "levels must be a non-empty array"),
        ("areas", "curriculum_areas must be a non-empty array"),
        ("area_pair", "area must be a safe"),
        ("duplicate_area", "duplicate curriculum area"),
        ("level_pair", "level must be a safe"),
        ("level_phase", "does not belong to its phase"),
        ("duplicate_level", "duplicate level"),
        ("area_count", "must declare exactly 4"),
        ("subject_name", "subject names must be consistent"),
        ("missing_level", "account for every declared"),
    ],
)
def test_release_manifest_rejects_invalid_catalog_contract(
    tmp_path: Path,
    case: str,
    message: str,
) -> None:
    projection = write_projection(tmp_path)
    manifest = write_release_manifest(tmp_path, [release_record(projection)])
    catalog = _catalog_mutation(case)
    manifest["catalog"] = write_catalog(
        tmp_path,
        catalog=catalog,
    )
    (tmp_path / "releases" / "curriculum-release.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(ReleaseManifestError, match=message):
        load_release_manifest(tmp_path)


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("missing", "Curriculum catalog is missing"),
        ("wrong_case", "exact repository case"),
        ("symlink", "non-symlink"),
        ("non_file", "Curriculum catalog is missing"),
        ("changed", "SHA-256 changed"),
        ("invalid_json", "invalid JSON"),
    ],
)
def test_release_manifest_rejects_unsafe_catalog_artifacts(
    tmp_path: Path,
    case: str,
    message: str,
) -> None:
    projection = write_projection(tmp_path)
    manifest = write_release_manifest(tmp_path, [release_record(projection)])
    catalog_path = tmp_path / "catalog" / "curriculum-catalog.json"
    if case == "missing":
        catalog_path.unlink()
    elif case == "wrong_case":
        catalog_path.parent.rename(tmp_path / "Catalog")
    elif case == "symlink":
        target = catalog_path.parent / "target.json"
        catalog_path.rename(target)
        catalog_path.symlink_to(target)
    elif case == "non_file":
        catalog_path.unlink()
        catalog_path.mkdir()
    elif case == "changed":
        catalog_path.write_text("{}", encoding="utf-8")
    elif case == "invalid_json":
        catalog_bytes = b"\xff"
        catalog_path.write_bytes(catalog_bytes)
        manifest["catalog"] = {
            "path": "catalog/curriculum-catalog.json",
            "sha256": sha256(catalog_bytes).hexdigest(),
        }
    else:
        raise AssertionError(f"Unhandled catalogue artifact case: {case}")
    (tmp_path / "releases" / "curriculum-release.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    with pytest.raises(ReleaseManifestError, match=message):
        load_release_manifest(tmp_path)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"id": "../unsafe"}, "id"),
        ({"subject_name": ""}, "subject_name"),
        ({"country": "KE"}, "country"),
        ({"country_slug": "uganda"}, "country_slug"),
        ({"phase": "tertiary"}, "phase"),
        ({"level": "upper_secondary"}, "level"),
        ({"subject": "../math"}, "subject"),
        ({"valid_from": "2019"}, "valid_from"),
        ({"valid_to": 42}, "valid_to"),
        ({"valid_to": "2019"}, "valid_to"),
        ({"valid_to": "2018-08-31"}, "valid_to"),
        ({"maturity": "complete"}, "maturity"),
        ({"review_status": "approved"}, "review_status"),
        ({"publication_profile": "internet"}, "publication_profile"),
        ({"node_code_prefixes": []}, "node_code_prefixes"),
        ({"node_code_prefixes": "B1."}, "node_code_prefixes"),
        ({"node_code_prefixes": ["../"]}, "node_code_prefixes"),
        ({"maturity": "located"}, "unextracted records"),
        ({"projection": None}, "projection"),
        ({"projection": "not-an-object"}, "projection"),
    ],
)
def test_release_manifest_rejects_unsafe_record_contracts(
    tmp_path: Path,
    overrides: dict[str, object],
    message: str,
) -> None:
    projection = write_projection(tmp_path)
    record_overrides = {key: value for key, value in overrides.items() if key != "projection"}
    record_projection = overrides.get("projection", projection)
    write_release_manifest(
        tmp_path,
        [release_record(record_projection, **record_overrides)],  # type: ignore[arg-type]
    )

    with pytest.raises(ReleaseManifestError, match=message):
        load_release_manifest(tmp_path)


def test_release_manifest_rejects_unpinned_or_unsafe_projection_files(
    tmp_path: Path,
) -> None:
    projection = write_projection(tmp_path)
    projection["nodes_sha256"] = "0" * 64
    write_release_manifest(tmp_path, [release_record(projection)])
    with pytest.raises(ReleaseManifestError, match="SHA-256"):
        load_release_manifest(tmp_path)

    projection = write_projection(tmp_path)
    projection["nodes_sha256"] = "invalid"
    write_release_manifest(tmp_path, [release_record(projection)])
    with pytest.raises(ReleaseManifestError, match="lowercase SHA-256"):
        load_release_manifest(tmp_path)

    projection = write_projection(tmp_path)
    projection["nodes_path"] = 42  # type: ignore[assignment]
    write_release_manifest(tmp_path, [release_record(projection)])
    with pytest.raises(ReleaseManifestError, match="must be a string"):
        load_release_manifest(tmp_path)

    for unsafe_path in (
        "/tmp/nodes.json",
        "curricula/ghana/primary/mathematics/nodes.txt",
        "curricula/ghana/primary/science/nodes.json",
    ):
        projection = write_projection(tmp_path)
        projection["nodes_path"] = unsafe_path
        write_release_manifest(tmp_path, [release_record(projection)])
        with pytest.raises(ReleaseManifestError, match="outside its subject boundary"):
            load_release_manifest(tmp_path)

    projection = write_projection(tmp_path)
    projection["nodes_path"] = "../outside.json"
    write_release_manifest(tmp_path, [release_record(projection)])
    with pytest.raises(ReleaseManifestError, match="projection path"):
        load_release_manifest(tmp_path)

    projection = write_projection(tmp_path)
    nodes_path = tmp_path / projection["nodes_path"]
    nodes_path.unlink()
    nodes_path.symlink_to(tmp_path / projection["graph_path"])
    write_release_manifest(tmp_path, [release_record(projection)])
    with pytest.raises(ReleaseManifestError, match="non-symlink"):
        load_release_manifest(tmp_path)

    projection = write_projection(tmp_path)
    (tmp_path / projection["nodes_path"]).unlink()
    write_release_manifest(tmp_path, [release_record(projection)])
    with pytest.raises(ReleaseManifestError, match="file is missing"):
        load_release_manifest(tmp_path)


def test_release_manifest_enforces_publication_review_and_release_state(
    tmp_path: Path,
) -> None:
    projection = write_projection(tmp_path)
    write_release_manifest(
        tmp_path,
        [release_record(projection, publication_profile="public")],
    )
    with pytest.raises(ReleaseManifestError, match="not reviewed and approved"):
        load_release_manifest(tmp_path)

    reviewed = release_record(
        projection,
        maturity="human_reviewed",
        review_status="human_reviewed",
        licensing_status="approved_for_public_projection",
        publication_profile="public",
    )
    write_release_manifest(tmp_path, [reviewed])
    with pytest.raises(ReleaseManifestError, match="requires a released manifest"):
        load_release_manifest(tmp_path)
