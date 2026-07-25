"""Tests for the bounded curriculum detail projection."""

import json
from pathlib import Path

from gapsense.curriculum.details import build_curriculum_detail


def _subject_root(tmp_path: Path) -> Path:
    root = tmp_path / "curricula" / "ghana" / "primary" / "mathematics"
    root.mkdir(parents=True)
    return root


def test_detail_projects_standards_indicators_and_strands(tmp_path: Path) -> None:
    root = _subject_root(tmp_path)
    (tmp_path / "curricula" / "ghana" / "primary" / "lower_primary" / "mathematics").mkdir(
        parents=True
    )
    (root / "assessment_framework.json").write_text("{}", encoding="utf-8")
    (root / "source_documents.json").write_text("{}", encoding="utf-8")
    (root / "prerequisite_graph_v1.0.json").write_text(
        json.dumps(
            {
                "strands": {"1": {"name": "Number"}, "bad": "ignored"},
                "sub_strands_by_phase": {"B1_B3": {"1.1": "Whole numbers"}, "bad": "ignored"},
                "nodes": {
                    "B1.1.1.1": {
                        "code": "B1.1.1.1",
                        "title": "Count",
                        "content_standard": "CS1",
                        "prerequisites": ["B1.1.0.1", 4],
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
                            "bad": "ignored",
                        },
                    },
                    "bad": "ignored",
                },
            }
        ),
        encoding="utf-8",
    )

    detail = build_curriculum_detail(
        tmp_path,
        country="ghana",
        phase="primary",
        level="lower_primary",
        subject="mathematics",
    )

    assert detail is not None
    assert detail.evidence_scope == "level"
    assert detail.extraction_status == "extracted"
    assert detail.source_files == (
        "assessment_framework.json",
        "prerequisite_graph_v1.0.json",
        "source_documents.json",
    )
    assert detail.strands[0].sub_strands == ("Whole numbers",)
    assert detail.nodes[0].prerequisites == ("B1.1.0.1",)
    assert [indicator.code for indicator in detail.nodes[0].indicators] == ["I2", "N.I1"]
    assert detail.nodes[0].indicators[1].question_type == "oral"
    assert detail.nodes[0].indicators[0].misconception_count == 1


def test_detail_falls_back_to_graph_nodes_and_fails_closed(tmp_path: Path) -> None:
    root = _subject_root(tmp_path)
    (root / "prerequisite_graph.json").write_text(
        json.dumps({"nodes": {"N1": {"title": "Fallback"}}}), encoding="utf-8"
    )

    detail = build_curriculum_detail(
        tmp_path,
        country="ghana",
        phase="primary",
        level="upper_primary",
        subject="mathematics",
    )
    assert detail is not None
    assert detail.evidence_scope == "phase_only"
    assert detail.extraction_status == "extracted"
    assert detail.nodes[0].title == "Fallback"
    assert detail.strands == ()

    assert (
        build_curriculum_detail(
            tmp_path,
            country="../ghana",
            phase="primary",
            level="upper_primary",
            subject="mathematics",
        )
        is None
    )
    assert (
        build_curriculum_detail(
            tmp_path, country="ghana", phase="primary", level="upper_primary", subject="missing"
        )
        is None
    )


def test_detail_is_located_when_no_normalized_nodes_exist(tmp_path: Path) -> None:
    root = _subject_root(tmp_path)
    (root / "broken.json").write_text("not-json", encoding="utf-8")
    (root / "list.json").write_text("[]", encoding="utf-8")

    detail = build_curriculum_detail(
        tmp_path, country="ghana", phase="primary", level="upper_primary", subject="mathematics"
    )
    assert detail is not None
    assert detail.extraction_status == "located"
    assert detail.nodes == ()
