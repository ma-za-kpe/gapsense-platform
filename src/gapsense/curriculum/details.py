"""Exact, manifest-pinned curriculum detail projections."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal, cast

if TYPE_CHECKING:
    from pathlib import Path

from gapsense.curriculum.release import (
    ReleaseManifest,
    ReleaseManifestError,
    ReleaseRecord,
    load_release_manifest,
)

DetailExtractionStatus = Literal["located", "extracted"]
DetailEvidenceScope = Literal["level"]
PrerequisiteStatus = Literal[
    "not_stated_by_authority",
    "projected_relationships",
    "not_extracted",
]


@dataclass(frozen=True, slots=True)
class CurriculumIndicatorSummary:
    """A concise indicator projection, never the full source text."""

    code: str
    title: str
    question_type: str | None
    difficulty: int | None
    misconception_count: int


@dataclass(frozen=True, slots=True)
class CurriculumEvidenceItemSummary:
    """One exact native-structure marker retained from an official source page."""

    kind: str
    code: str | None
    text: str


@dataclass(frozen=True, slots=True)
class CurriculumNodeSummary:
    """A lossless page or curated record with explicit source-page lineage."""

    code: str
    title: str
    record_kind: str
    content_standard: str
    source_id: str | None
    source_page: int | None
    curriculum_path: tuple[str, ...]
    section_identifier: str | None
    strand_identifier: str | None
    prerequisite_status: PrerequisiteStatus
    prerequisites: tuple[str, ...]
    evidence_items: tuple[CurriculumEvidenceItemSummary, ...]
    indicators: tuple[CurriculumIndicatorSummary, ...]


@dataclass(frozen=True, slots=True)
class CurriculumSectionSummary:
    """One country-native hierarchy section with source-page lineage."""

    identifier: str
    parent_identifier: str | None
    kind: str
    title: str
    source_id: str
    source_page: int


@dataclass(frozen=True, slots=True)
class CurriculumStrandSummary:
    """A strand and its phase-specific sub-strands."""

    identifier: str
    name: str
    sub_strands: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CurriculumDetail:
    """Safe detail response consumed by the browser lineage view."""

    release_id: str
    country: str
    phase: str
    level: str
    subject: str
    evidence_scope: DetailEvidenceScope
    extraction_status: DetailExtractionStatus
    extraction_method: str
    source_files: tuple[str, ...]
    curriculum_model: str
    structure_status: str
    sections: tuple[CurriculumSectionSummary, ...]
    strands: tuple[CurriculumStrandSummary, ...]
    nodes: tuple[CurriculumNodeSummary, ...]


_SAFE_PART = re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")


def _safe_part(value: str) -> bool:
    return bool(_SAFE_PART.fullmatch(value))


def _load_json_object(path: Path, expected_sha256: str) -> dict[str, object] | None:
    try:
        contents = path.read_bytes()
        if hashlib.sha256(contents).hexdigest() != expected_sha256:
            return None
        value: object = json.loads(contents)
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _node_source(payload: dict[str, object]) -> dict[str, object]:
    for key in ("nodes_fully_populated", "nodes"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _indicator_summaries(value: object) -> tuple[CurriculumIndicatorSummary, ...]:
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


def _source_locator(value: object) -> tuple[str | None, int | None]:
    if not isinstance(value, dict):
        return None, None
    source_id = value.get("source_id")
    page = value.get("page")
    if (
        not isinstance(source_id, str)
        or not source_id
        or not isinstance(page, int)
        or isinstance(page, bool)
        or page <= 0
    ):
        return None, None
    return source_id, page


def _evidence_item_summaries(
    value: object,
) -> tuple[CurriculumEvidenceItemSummary, ...]:
    if not isinstance(value, list):
        return ()
    items: list[CurriculumEvidenceItemSummary] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        kind = raw.get("kind")
        code = raw.get("code")
        text = raw.get("text")
        if (
            not isinstance(kind, str)
            or not kind
            or (code is not None and not isinstance(code, str))
            or not isinstance(text, str)
            or not text
        ):
            continue
        items.append(CurriculumEvidenceItemSummary(kind=kind, code=code, text=text))
    return tuple(items)


def _section_summaries(graph: dict[str, object]) -> tuple[CurriculumSectionSummary, ...]:
    raw_sections = graph.get("sections")
    if not isinstance(raw_sections, dict):
        return ()
    sections: list[CurriculumSectionSummary] = []
    for fallback_identifier, raw in raw_sections.items():
        if not isinstance(raw, dict):
            return ()
        identifier = raw.get("identifier") or fallback_identifier
        parent = raw.get("parent_identifier")
        kind = raw.get("kind")
        title = raw.get("title")
        source_id, source_page = _source_locator(raw.get("source_locator"))
        if (
            not isinstance(identifier, str)
            or not identifier
            or (parent is not None and not isinstance(parent, str))
            or not isinstance(kind, str)
            or not kind
            or not isinstance(title, str)
            or not title
            or source_id is None
            or source_page is None
        ):
            return ()
        sections.append(
            CurriculumSectionSummary(
                identifier=identifier,
                parent_identifier=parent,
                kind=kind,
                title=title,
                source_id=source_id,
                source_page=source_page,
            )
        )
    by_identifier = {section.identifier: section for section in sections}
    if len(by_identifier) != len(sections):
        return ()
    roots = [section for section in sections if section.parent_identifier is None]
    if len(roots) != 1:
        return ()
    for section in sections:
        visited = {section.identifier}
        parent = section.parent_identifier
        while parent is not None:
            if parent in visited or parent not in by_identifier:
                return ()
            visited.add(parent)
            parent = by_identifier[parent].parent_identifier
    return tuple(sections)


def _node_summaries(
    populated: dict[str, object],
    graph: dict[str, object],
    prefixes: tuple[str, ...],
    section_identifiers: set[str],
) -> tuple[CurriculumNodeSummary, ...]:
    populated_nodes = _node_source(populated)
    graph_nodes = _node_source(graph)
    nodes: list[CurriculumNodeSummary] = []
    for fallback_code, raw in populated_nodes.items():
        if not isinstance(raw, dict) or not fallback_code.startswith(prefixes):
            continue
        graph_raw = graph_nodes.get(fallback_code)
        merged = dict(graph_raw) if isinstance(graph_raw, dict) else {}
        merged.update(raw)
        prerequisites = merged.get("prerequisites")
        strand = merged.get("strand")
        source_id, source_page = _source_locator(merged.get("source_locator"))
        raw_path = merged.get("curriculum_path")
        curriculum_path = (
            tuple(
                identifier
                for identifier in raw_path
                if isinstance(identifier, str) and identifier in section_identifiers
            )
            if isinstance(raw_path, list)
            else ()
        )
        raw_section_identifier = merged.get("section_identifier")
        section_identifier = (
            raw_section_identifier
            if isinstance(raw_section_identifier, str)
            and raw_section_identifier in section_identifiers
            else None
        )
        raw_prerequisite_status = merged.get("prerequisite_status")
        valid_prerequisite_statuses: set[str] = {
            "not_stated_by_authority",
            "projected_relationships",
            "not_extracted",
        }
        prerequisite_status: PrerequisiteStatus
        if (
            isinstance(raw_prerequisite_status, str)
            and raw_prerequisite_status in valid_prerequisite_statuses
        ):
            prerequisite_status = cast(PrerequisiteStatus, raw_prerequisite_status)
        elif isinstance(prerequisites, list):
            prerequisite_status = "projected_relationships"
        else:
            prerequisite_status = "not_extracted"
        nodes.append(
            CurriculumNodeSummary(
                code=str(merged.get("code") or fallback_code),
                title=str(merged.get("title") or merged.get("name") or "Untitled standard"),
                record_kind=str(merged.get("record_kind") or "curriculum_standard"),
                content_standard=str(
                    merged.get("nacca_content_standard") or merged.get("content_standard") or ""
                ),
                source_id=source_id,
                source_page=source_page,
                curriculum_path=curriculum_path,
                section_identifier=section_identifier,
                strand_identifier=(
                    str(strand)
                    if isinstance(strand, int | str) and not isinstance(strand, bool)
                    else None
                ),
                prerequisite_status=prerequisite_status,
                prerequisites=(
                    tuple(str(item) for item in prerequisites if isinstance(item, str))
                    if isinstance(prerequisites, list)
                    else ()
                ),
                evidence_items=_evidence_item_summaries(merged.get("evidence_items")),
                indicators=_indicator_summaries(merged.get("indicators")),
            )
        )
    return tuple(sorted(nodes, key=lambda item: item.code))


def _strand_summaries(
    graph: dict[str, object],
    identifiers: set[str],
) -> tuple[CurriculumStrandSummary, ...]:
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
        identifier_text = str(identifier)
        if identifier_text not in identifiers or not isinstance(raw, dict):
            continue
        prefix = f"{identifier_text}."
        result.append(
            CurriculumStrandSummary(
                identifier=identifier_text,
                name=str(raw.get("name") or f"Strand {identifier_text}"),
                sub_strands=tuple(
                    value for key, value in sorted(labels.items()) if key.startswith(prefix)
                ),
            )
        )
    return tuple(sorted(result, key=lambda item: item.identifier))


def _exact_record(
    manifest: ReleaseManifest,
    *,
    country: str,
    phase: str,
    level: str,
    subject: str,
) -> ReleaseRecord | None:
    return next(
        (
            record
            for record in manifest.records
            if (
                record.country_slug,
                record.phase,
                record.level,
                record.subject,
            )
            == (country, phase, level, subject)
        ),
        None,
    )


def build_curriculum_detail(
    data_path: Path,
    *,
    country: str,
    phase: str,
    level: str,
    subject: str,
    manifest: ReleaseManifest | None = None,
) -> CurriculumDetail | None:
    """Project one exact declared combination or fail closed."""
    if not all(_safe_part(part) for part in (country, phase, level, subject)):
        return None
    if manifest is None:
        try:
            manifest = load_release_manifest(data_path)
        except ReleaseManifestError:
            return None
    record = _exact_record(
        manifest,
        country=country,
        phase=phase,
        level=level,
        subject=subject,
    )
    if record is None or record.maturity == "missing":
        return None
    if record.projection is None:
        return CurriculumDetail(
            release_id=manifest.release_id,
            country=country,
            phase=phase,
            level=level,
            subject=subject,
            evidence_scope="level",
            extraction_status="located",
            extraction_method="not_available",
            source_files=(),
            curriculum_model="official-catalogue-entry",
            structure_status="source_artifact_not_available",
            sections=(),
            strands=(),
            nodes=(),
        )

    populated = _load_json_object(
        record.projection.nodes_path,
        record.projection.nodes_sha256,
    )
    graph = _load_json_object(
        record.projection.graph_path,
        record.projection.graph_sha256,
    )
    if populated is None or graph is None:
        return None
    sections = _section_summaries(graph)
    raw_sections = graph.get("sections")
    if isinstance(raw_sections, dict) and not sections:
        return None
    section_identifiers = {section.identifier for section in sections}
    nodes = _node_summaries(
        populated,
        graph,
        record.node_code_prefixes,
        section_identifiers,
    )
    if not nodes:
        return None
    if sections and any(
        node.section_identifier is None
        or not node.curriculum_path
        or node.section_identifier not in node.curriculum_path
        for node in nodes
    ):
        return None
    strand_identifiers = {
        node.strand_identifier for node in nodes if node.strand_identifier is not None
    }
    strands = _strand_summaries(graph, strand_identifiers)
    valid_strand_identifiers = {strand.identifier for strand in strands}
    nodes = tuple(
        replace(node, strand_identifier=None)
        if node.strand_identifier not in valid_strand_identifiers
        else node
        for node in nodes
    )
    raw_model = graph.get("curriculum_model")
    curriculum_model = (
        raw_model if isinstance(raw_model, str) and raw_model else "legacy-strand-projection"
    )
    raw_structure_status = graph.get("structure_status")
    structure_status = (
        raw_structure_status
        if isinstance(raw_structure_status, str) and raw_structure_status
        else "legacy_projection_not_human_verified"
    )
    raw_extraction_method = populated.get("extraction_method")
    extraction_method = (
        raw_extraction_method
        if isinstance(raw_extraction_method, str) and raw_extraction_method
        else "projection_method_not_declared"
    )
    return CurriculumDetail(
        release_id=manifest.release_id,
        country=country,
        phase=phase,
        level=level,
        subject=subject,
        evidence_scope="level",
        extraction_status="extracted",
        extraction_method=extraction_method,
        source_files=(
            record.projection.nodes_path.name,
            record.projection.graph_path.name,
        ),
        curriculum_model=curriculum_model,
        structure_status=structure_status,
        sections=sections,
        strands=strands,
        nodes=nodes,
    )
