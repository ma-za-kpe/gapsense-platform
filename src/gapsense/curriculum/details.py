"""Safe, bounded curriculum detail projections for the web explorer."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

DetailExtractionStatus = Literal["located", "extracted"]
DetailEvidenceScope = Literal["level", "phase_only"]


@dataclass(frozen=True, slots=True)
class CurriculumIndicatorSummary:
    """A concise indicator projection, never the full source text."""

    code: str
    title: str
    question_type: str | None
    difficulty: int | None
    misconception_count: int


@dataclass(frozen=True, slots=True)
class CurriculumNodeSummary:
    """A standard/content-node projection with indicator lineage."""

    code: str
    title: str
    content_standard: str
    prerequisites: tuple[str, ...]
    indicators: tuple[CurriculumIndicatorSummary, ...]


@dataclass(frozen=True, slots=True)
class CurriculumStrandSummary:
    """A strand and its phase-specific sub-strands."""

    identifier: str
    name: str
    sub_strands: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurriculumDetail:
    """Safe detail response consumed by the browser lineage view."""

    country: str
    phase: str
    level: str
    subject: str
    evidence_scope: DetailEvidenceScope
    extraction_status: DetailExtractionStatus
    source_files: tuple[str, ...]
    strands: tuple[CurriculumStrandSummary, ...]
    nodes: tuple[CurriculumNodeSummary, ...]


_SAFE_PART = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


def _safe_part(value: str) -> bool:
    """Reject traversal and unbounded path components."""
    return bool(_SAFE_PART.fullmatch(value))


def _load_json(path: Path) -> dict[str, object]:
    """Read one local JSON projection, failing closed on malformed evidence."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _node_source(payload: dict[str, object]) -> dict[str, object]:
    """Support the two normalized node container names in current evidence."""
    for key in ("nodes_fully_populated", "nodes"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _indicator_summaries(value: object) -> tuple[CurriculumIndicatorSummary, ...]:
    """Project indicator metadata while excluding raw descriptions and prompts."""
    if not isinstance(value, dict):
        return ()
    indicators: list[CurriculumIndicatorSummary] = []
    for fallback_code, raw in value.items():
        if not isinstance(raw, dict):
            continue
        code = raw.get("nacca_code") or raw.get("code") or fallback_code
        title = raw.get("title") or raw.get("name") or "Untitled indicator"
        question_type = raw.get("diagnostic_question_type")
        difficulty = raw.get("difficulty_estimate")
        errors = raw.get("error_patterns")
        indicators.append(
            CurriculumIndicatorSummary(
                code=str(code),
                title=str(title),
                question_type=question_type if isinstance(question_type, str) else None,
                difficulty=difficulty if isinstance(difficulty, int) else None,
                misconception_count=len(errors) if isinstance(errors, list) else 0,
            )
        )
    return tuple(sorted(indicators, key=lambda item: item.code))


def _node_summaries(payload: dict[str, object]) -> tuple[CurriculumNodeSummary, ...]:
    """Project standards nodes and their indicator lineage."""
    nodes: list[CurriculumNodeSummary] = []
    for fallback_code, raw in _node_source(payload).items():
        if not isinstance(raw, dict):
            continue
        prerequisites = raw.get("prerequisites")
        nodes.append(
            CurriculumNodeSummary(
                code=str(raw.get("code") or fallback_code),
                title=str(raw.get("title") or raw.get("name") or "Untitled standard"),
                content_standard=str(
                    raw.get("nacca_content_standard") or raw.get("content_standard") or ""
                ),
                prerequisites=tuple(str(item) for item in prerequisites if isinstance(item, str))
                if isinstance(prerequisites, list)
                else (),
                indicators=_indicator_summaries(raw.get("indicators")),
            )
        )
    return tuple(sorted(nodes, key=lambda item: item.code))


def _strand_summaries(graph: dict[str, object]) -> tuple[CurriculumStrandSummary, ...]:
    """Project strand names and the available phase sub-strand labels."""
    strands = graph.get("strands")
    if not isinstance(strands, dict):
        return ()
    sub_strands = graph.get("sub_strands_by_phase")
    labels: dict[str, str] = {}
    if isinstance(sub_strands, dict):
        for phase_value in sub_strands.values():
            if isinstance(phase_value, dict):
                labels.update(
                    {
                        str(key): str(value)
                        for key, value in phase_value.items()
                        if isinstance(value, str)
                    }
                )
    result: list[CurriculumStrandSummary] = []
    for identifier, raw in strands.items():
        if not isinstance(raw, dict):
            continue
        prefix = f"{identifier}."
        result.append(
            CurriculumStrandSummary(
                identifier=str(identifier),
                name=str(raw.get("name") or f"Strand {identifier}"),
                sub_strands=tuple(
                    value for key, value in sorted(labels.items()) if key.startswith(prefix)
                ),
            )
        )
    return tuple(sorted(result, key=lambda item: item.identifier))


def build_curriculum_detail(
    data_path: Path,
    *,
    country: str,
    phase: str,
    level: str,
    subject: str,
) -> CurriculumDetail | None:
    """Build a safe detail projection or return ``None`` for unsupported evidence."""
    parts = (country, phase, level, subject)
    if not all(_safe_part(part) for part in parts):
        return None
    country_path = data_path / "curricula" / country
    subject_candidates = (subject, subject.replace("_", "-"))
    subject_path = next(
        (
            country_path / phase / candidate
            for candidate in subject_candidates
            if (country_path / phase / candidate).is_dir()
        ),
        country_path / phase / subject,
    )
    if not subject_path.is_dir() or subject_path.is_symlink():
        return None
    exact_level_path = country_path / phase / level / subject
    evidence_scope: DetailEvidenceScope = "level" if exact_level_path.is_dir() else "phase_only"
    populated = _load_json(subject_path / "populated_nodes_complete.json")
    graph_candidates = sorted(subject_path.glob("prerequisite_graph*.json"))
    graph = _load_json(graph_candidates[0]) if graph_candidates else {}
    nodes = _node_summaries(populated or graph)
    source_files = tuple(
        sorted(
            path.name
            for path in subject_path.iterdir()
            if path.is_file() and path.name not in {"populated_nodes_complete.json"}
        )
    )
    return CurriculumDetail(
        country=country,
        phase=phase,
        level=level,
        subject=subject,
        evidence_scope=evidence_scope,
        extraction_status="extracted" if nodes else "located",
        source_files=source_files,
        strands=_strand_summaries(graph),
        nodes=nodes,
    )
