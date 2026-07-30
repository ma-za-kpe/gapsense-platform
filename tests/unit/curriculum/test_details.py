"""Tests for exact, manifest-pinned curriculum detail projections."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from typing import TYPE_CHECKING

from tests.curriculum_release import release_record, write_projection, write_release_manifest

from gapsense.curriculum.details import build_curriculum_detail
from gapsense.curriculum.release import load_release_manifest

if TYPE_CHECKING:
    from pathlib import Path


def test_detail_merges_pinned_nodes_and_relationships_for_one_exact_level(
    tmp_path: Path,
) -> None:
    projection = write_projection(
        tmp_path,
        nodes={
            "extraction_method": "lossless-page-and-native-heading-projection",
            "nodes_fully_populated": {
                "B1.1.1.1": {
                    "title": "Count",
                    "content_standard": "CS1",
                    "source_locator": {"source_id": "gh-primary-mathematics", "page": 42},
                    "indicators": {
                        "I2": {
                            "code": "I2",
                            "name": "Compare",
                            "difficulty_estimate": 2,
                            "error_patterns": ["one"],
                        },
                        "I1": {
                            "nacca_code": "N.I1",
                            "title": "Count",
                            "diagnostic_question_type": "oral",
                        },
                    },
                },
                "B5.1.1.1": {"title": "Upper-only"},
            },
        },
        graph={
            "strands": {"1": {"name": "Number"}, "bad": "ignored"},
            "sub_strands_by_phase": {
                "B1_B3": {"1.1": "Whole numbers"},
                "bad": "ignored",
            },
            "nodes": {
                "B1.1.1.1": {
                    "strand": 1,
                    "prerequisites": ["B1.1.0.1", 4],
                },
                "B5.1.1.1": {"strand": 1, "prerequisites": []},
            },
        },
    )
    write_release_manifest(tmp_path, [release_record(projection)])

    detail = build_curriculum_detail(
        tmp_path,
        country="ghana",
        phase="primary",
        level="lower_primary",
        subject="mathematics",
    )

    assert detail is not None
    assert detail.release_id == "curriculum-2026-07-29-candidate.1"
    assert detail.evidence_scope == "level"
    assert detail.extraction_status == "extracted"
    assert detail.extraction_method == "lossless-page-and-native-heading-projection"
    assert detail.source_files == (
        "populated_nodes_complete.json",
        "prerequisite_graph_v1.2.json",
    )
    assert detail.curriculum_model == "legacy-strand-projection"
    assert detail.structure_status == "legacy_projection_not_human_verified"
    assert detail.sections == ()
    assert detail.strands[0].sub_strands == ("Whole numbers",)
    assert [node.code for node in detail.nodes] == ["B1.1.1.1"]
    assert detail.nodes[0].record_kind == "curriculum_standard"
    assert detail.nodes[0].prerequisite_status == "projected_relationships"
    assert detail.nodes[0].curriculum_path == ()
    assert detail.nodes[0].section_identifier is None
    assert detail.nodes[0].evidence_items == ()
    assert detail.nodes[0].strand_identifier == "1"
    assert detail.nodes[0].source_id == "gh-primary-mathematics"
    assert detail.nodes[0].source_page == 42
    assert detail.nodes[0].prerequisites == ("B1.1.0.1",)
    assert [indicator.code for indicator in detail.nodes[0].indicators] == ["I2", "N.I1"]
    assert detail.nodes[0].indicators[1].question_type == "oral"
    assert detail.nodes[0].indicators[0].misconception_count == 1


def test_detail_rejects_undeclared_and_arbitrary_combinations(tmp_path: Path) -> None:
    projection = write_projection(tmp_path)
    write_release_manifest(tmp_path, [release_record(projection)])

    requests = [
        {
            "country": "ghana",
            "phase": "primary",
            "level": "not_a_real_level",
            "subject": "mathematics",
        },
        {
            "country": "ghana",
            "phase": "primary",
            "level": "upper_primary",
            "subject": "mathematics",
        },
        {
            "country": "ghana",
            "phase": "secondary",
            "level": "lower_primary",
            "subject": "mathematics",
        },
        {
            "country": "../ghana",
            "phase": "primary",
            "level": "lower_primary",
            "subject": "mathematics",
        },
    ]

    for request in requests:
        assert (
            build_curriculum_detail(
                tmp_path,
                country=request["country"],
                phase=request["phase"],
                level=request["level"],
                subject=request["subject"],
            )
            is None
        )


def test_detail_represents_located_evidence_and_hides_explicit_missing(
    tmp_path: Path,
) -> None:
    located = release_record(None, maturity="located")
    write_release_manifest(tmp_path, [located])
    detail = build_curriculum_detail(
        tmp_path,
        country="ghana",
        phase="primary",
        level="lower_primary",
        subject="mathematics",
    )
    assert detail is not None
    assert detail.extraction_status == "located"
    assert detail.extraction_method == "not_available"
    assert detail.nodes == ()
    assert detail.strands == ()
    assert detail.sections == ()
    assert detail.curriculum_model == "official-catalogue-entry"
    assert detail.structure_status == "source_artifact_not_available"
    assert detail.source_files == ()

    write_release_manifest(tmp_path, [release_record(None, maturity="missing")])
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
        )
        is None
    )


def test_detail_fails_closed_when_the_release_contract_is_invalid(tmp_path: Path) -> None:
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
        )
        is None
    )


def test_detail_rechecks_pinned_bytes_at_consumption_time(tmp_path: Path) -> None:
    projection = write_projection(
        tmp_path,
        nodes={"nodes": {"B1.1": {"title": "Count"}}},
        graph={"nodes": {"B1.1": {}}, "strands": {}},
    )
    write_release_manifest(
        tmp_path,
        [release_record(projection, node_code_prefixes=["B1."])],
    )
    manifest = load_release_manifest(tmp_path)
    nodes_path = tmp_path / projection["nodes_path"]
    graph_path = tmp_path / projection["graph_path"]

    nodes_path.write_text('{"nodes": {}}', encoding="utf-8")
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
            manifest=manifest,
        )
        is None
    )

    nodes_path.write_bytes(b'{"nodes": {"B1.1": {"title": "Count"}}}\n')
    graph_path.write_text('{"nodes": {}}', encoding="utf-8")
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
            manifest=manifest,
        )
        is None
    )

    invalid_json = b"{"
    graph_path.write_bytes(invalid_json)
    record = manifest.records[0]
    assert record.projection is not None
    invalid_projection = replace(
        record.projection,
        graph_sha256=hashlib.sha256(invalid_json).hexdigest(),
    )
    invalid_manifest = replace(
        manifest,
        records=(replace(record, projection=invalid_projection),),
    )
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
            manifest=invalid_manifest,
        )
        is None
    )


def test_detail_exposes_a_lossless_country_native_hierarchy(tmp_path: Path) -> None:
    projection = write_projection(
        tmp_path,
        nodes={
            "curriculum_model": "ghana-standards-based",
            "nodes": {
                "DOC.0001": {
                    "code": "DOC.0001",
                    "title": "BASIC 1",
                    "record_kind": "source_page",
                    "content_standard": "BASIC 1\nSTRAND 1: NUMBER",
                    "curriculum_path": ["SEC.00000", "SEC.00001"],
                    "source_locator": {
                        "source_id": "gh-primary-mathematics",
                        "page": 1,
                    },
                    "evidence_items": [
                        "not-an-object",
                        {"kind": "", "code": 42, "text": ""},
                        {"kind": "grade", "code": None, "text": "BASIC 1"},
                        {
                            "kind": "indicator",
                            "code": "B1.1.1.1.1",
                            "text": "B1.1.1.1.1 Count objects",
                        },
                    ],
                }
            },
        },
        graph={
            "curriculum_model": "ghana-standards-based",
            "structure_status": "machine_extracted_not_human_verified",
            "sections": {
                "SEC.00000": {
                    "identifier": "SEC.00000",
                    "kind": "document",
                    "title": "Mathematics official curriculum",
                    "parent_identifier": None,
                    "source_locator": {
                        "source_id": "gh-primary-mathematics",
                        "page": 1,
                    },
                },
                "SEC.00001": {
                    "identifier": "SEC.00001",
                    "kind": "grade",
                    "title": "BASIC 1",
                    "parent_identifier": "SEC.00000",
                    "source_locator": {
                        "source_id": "gh-primary-mathematics",
                        "page": 1,
                    },
                },
            },
            "nodes": {
                "DOC.0001": {
                    "section_identifier": "SEC.00001",
                    "prerequisite_status": "not_stated_by_authority",
                    "prerequisites": [],
                }
            },
        },
    )
    write_release_manifest(
        tmp_path,
        [release_record(projection, node_code_prefixes=["DOC."])],
    )

    detail = build_curriculum_detail(
        tmp_path,
        country="ghana",
        phase="primary",
        level="lower_primary",
        subject="mathematics",
    )

    assert detail is not None
    assert detail.curriculum_model == "ghana-standards-based"
    assert detail.structure_status == "machine_extracted_not_human_verified"
    assert [section.kind for section in detail.sections] == ["document", "grade"]
    assert detail.sections[1].parent_identifier == "SEC.00000"
    assert detail.nodes[0].record_kind == "source_page"
    assert detail.nodes[0].curriculum_path == ("SEC.00000", "SEC.00001")
    assert detail.nodes[0].section_identifier == "SEC.00001"
    assert detail.nodes[0].prerequisite_status == "not_stated_by_authority"
    assert detail.nodes[0].evidence_items[1].code == "B1.1.1.1.1"


def test_detail_rejects_every_malformed_native_section_boundary(tmp_path: Path) -> None:
    locator = {"source_id": "gh-primary-mathematics", "page": 1}
    root = {
        "identifier": "SEC.00000",
        "kind": "document",
        "title": "Mathematics official curriculum",
        "parent_identifier": None,
        "source_locator": locator,
    }
    invalid_sections = [
        {"SEC.00000": "not-an-object"},
        {"SEC.00000": {**root, "title": ""}},
        {
            "SEC.00000": root,
            "SEC.00001": {
                **root,
                "identifier": "SEC.00000",
                "parent_identifier": "SEC.00000",
            },
        },
        {
            "SEC.00000": root,
            "SEC.00001": {**root, "identifier": "SEC.00001"},
        },
        {
            "SEC.00000": root,
            "SEC.00001": {
                **root,
                "identifier": "SEC.00001",
                "parent_identifier": "SEC.00002",
            },
            "SEC.00002": {
                **root,
                "identifier": "SEC.00002",
                "parent_identifier": "SEC.00001",
            },
        },
    ]
    for sections in invalid_sections:
        projection = write_projection(
            tmp_path,
            nodes={
                "nodes": {
                    "DOC.0001": {
                        "title": "Page",
                        "curriculum_path": ["SEC.00000"],
                    }
                }
            },
            graph={"sections": sections, "nodes": {"DOC.0001": {}}},
        )
        write_release_manifest(
            tmp_path,
            [release_record(projection, node_code_prefixes=["DOC."])],
        )

        assert (
            build_curriculum_detail(
                tmp_path,
                country="ghana",
                phase="primary",
                level="lower_primary",
                subject="mathematics",
            )
            is None
        )


def test_detail_rejects_nodes_detached_from_a_declared_native_hierarchy(tmp_path: Path) -> None:
    projection = write_projection(
        tmp_path,
        nodes={"nodes": {"DOC.0001": {"title": "Detached page"}}},
        graph={
            "sections": {
                "SEC.00000": {
                    "identifier": "SEC.00000",
                    "kind": "document",
                    "title": "Mathematics official curriculum",
                    "parent_identifier": None,
                    "source_locator": {
                        "source_id": "gh-primary-mathematics",
                        "page": 1,
                    },
                }
            },
            "nodes": {"DOC.0001": {}},
        },
    )
    write_release_manifest(
        tmp_path,
        [release_record(projection, node_code_prefixes=["DOC."])],
    )

    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
        )
        is None
    )


def test_detail_normalizes_partial_and_malformed_projection_data(tmp_path: Path) -> None:
    projection = write_projection(
        tmp_path,
        nodes={
            "nodes": {
                "B1.1": {
                    "source_locator": {"source_id": "", "page": True},
                    "indicators": {
                        "ignored": "not-an-object",
                        "fallback": {"difficulty_estimate": "hard"},
                    },
                },
                "B1.2": {"title": "No indicators recorded"},
                "B1.bad": "not-an-object",
                "B5.1": {"title": "Outside exact level"},
            }
        },
        graph={
            "nodes": {"B1.1": {"strand": True, "prerequisites": "unknown"}},
            "strands": {},
            "sub_strands_by_phase": [],
        },
    )
    write_release_manifest(
        tmp_path,
        [release_record(projection, node_code_prefixes=["B1."])],
    )

    detail = build_curriculum_detail(
        tmp_path,
        country="ghana",
        phase="primary",
        level="lower_primary",
        subject="mathematics",
    )

    assert detail is not None
    assert detail.strands == ()
    assert detail.nodes[0].title == "Untitled standard"
    assert detail.nodes[0].strand_identifier is None
    assert detail.nodes[0].source_id is None
    assert detail.nodes[0].source_page is None
    assert detail.nodes[0].prerequisite_status == "not_extracted"
    assert detail.nodes[0].indicators[0].code == "fallback"
    assert detail.nodes[0].indicators[0].title == "Untitled indicator"

    empty_projection = write_projection(
        tmp_path,
        nodes={"other": {}},
        graph={"nodes": {}, "strands": {}},
    )
    write_release_manifest(tmp_path, [release_record(empty_projection)])
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
        )
        is None
    )

    projection = write_projection(tmp_path)
    write_release_manifest(tmp_path, [release_record(projection)])
    (tmp_path / projection["graph_path"]).write_text("{}", encoding="utf-8")
    assert (
        build_curriculum_detail(
            tmp_path,
            country="ghana",
            phase="primary",
            level="lower_primary",
            subject="mathematics",
        )
        is None
    )
