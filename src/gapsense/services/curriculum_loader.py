"""
Multi-country Curriculum Loader

Walks the curricula/{country}/{level}/{subject}/ directory tree,
parses object-based JSON files, and upserts CurriculumNode records.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.config import Settings
from gapsense.core.models.curriculum import CurriculumNode

logger = structlog.get_logger(__name__)


@dataclass
class CountrySummary:
    """Per-country loading summary."""

    files: int = 0
    nodes_created: int = 0
    nodes_updated: int = 0
    errors: int = 0
    by_subject: dict[str, int] = field(default_factory=dict)


@dataclass
class LoadSummary:
    """Overall loading summary."""

    total_files: int = 0
    total_nodes_created: int = 0
    total_nodes_updated: int = 0
    total_errors: int = 0
    by_country: dict[str, CountrySummary] = field(default_factory=dict)


class CurriculumLoader:
    """Multi-country curriculum loader with upsert logic."""

    def __init__(self, db_session: AsyncSession, settings: Settings) -> None:
        self.db_session = db_session
        self.settings = settings
        self.base_path: Path = settings.curricula_base_path

    async def load_all_countries(self) -> LoadSummary:
        """Walk curricula/{country}/ and load all countries."""
        summary = LoadSummary()

        if not self.base_path.exists():
            logger.warning("curricula_base_path_missing", path=str(self.base_path))
            return summary

        for country_dir in sorted(self.base_path.iterdir()):
            if not country_dir.is_dir():
                continue
            country_code = country_dir.name
            country_summary = await self._load_country_dir(country_code, country_dir)
            summary.by_country[country_code] = country_summary
            summary.total_files += country_summary.files
            summary.total_nodes_created += country_summary.nodes_created
            summary.total_nodes_updated += country_summary.nodes_updated
            summary.total_errors += country_summary.errors

        logger.info(
            "curriculum_load_complete",
            total_files=summary.total_files,
            total_nodes_created=summary.total_nodes_created,
            total_nodes_updated=summary.total_nodes_updated,
            total_errors=summary.total_errors,
            countries=list(summary.by_country.keys()),
        )
        return summary

    async def load_country(self, country_code: str) -> LoadSummary:
        """Load curriculum for a single country."""
        summary = LoadSummary()
        country_dir = self.base_path / country_code

        if not country_dir.exists():
            logger.warning("country_dir_missing", country=country_code, path=str(country_dir))
            return summary

        country_summary = await self._load_country_dir(country_code, country_dir)
        summary.by_country[country_code] = country_summary
        summary.total_files = country_summary.files
        summary.total_nodes_created = country_summary.nodes_created
        summary.total_nodes_updated = country_summary.nodes_updated
        summary.total_errors = country_summary.errors

        return summary

    async def _load_country_dir(self, country_code: str, country_dir: Path) -> CountrySummary:
        """Load all curriculum files for a single country directory."""
        country_summary = CountrySummary()

        # Read country_config.json if present
        config = self._read_country_config(country_dir)
        active_levels = config.get("active_levels", [])
        active_subjects = config.get("active_subjects", {})

        # Walk {country}/{level}/{subject}/*.json
        for level_dir in sorted(country_dir.iterdir()):
            if not level_dir.is_dir() or level_dir.name == "__pycache__":
                continue
            level = level_dir.name

            # If country_config specifies active_levels, skip inactive ones
            if active_levels and level not in active_levels:
                continue

            level_subjects = active_subjects.get(level, [])

            for subject_dir in sorted(level_dir.iterdir()):
                if not subject_dir.is_dir():
                    continue
                subject = subject_dir.name

                # If country_config specifies active_subjects for this level, skip inactive
                if level_subjects and subject not in level_subjects:
                    continue

                for json_file in sorted(subject_dir.glob("*.json")):
                    # Only load populated_nodes_complete.json - skip all other files
                    if json_file.name != "populated_nodes_complete.json":
                        logger.debug("skipping_non_node_file", file=json_file.name)
                        continue
                    await self._load_file(json_file, country_code, level, subject, country_summary)

        return country_summary

    def _read_country_config(self, country_dir: Path) -> dict:
        """Read country_config.json for active levels and subjects."""
        config_path = country_dir / "country_config.json"
        if not config_path.exists():
            logger.debug("no_country_config", path=str(config_path))
            return {}
        try:
            with open(config_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("country_config_read_error", path=str(config_path), error=str(exc))
            return {}

    async def _load_file(
        self,
        json_file: Path,
        country: str,
        level: str,
        subject: str,
        summary: CountrySummary,
    ) -> None:
        """Parse a single JSON file and upsert nodes."""
        summary.files += 1
        try:
            with open(json_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "invalid_json_file",
                path=str(json_file),
                error=str(exc),
            )
            summary.errors += 1
            return

        if not isinstance(data, dict):
            logger.warning("unexpected_json_format", path=str(json_file), type=type(data).__name__)
            summary.errors += 1
            return

        # Handle multiple JSON formats: "nodes", "nodes_fully_populated", or root-level
        nodes = data.get("nodes") or data.get("nodes_fully_populated") or data
        if not isinstance(nodes, dict):
            logger.warning("no_nodes_found", path=str(json_file))
            summary.errors += 1
            return

        for code, node_data in nodes.items():
            if not isinstance(node_data, dict):
                continue
            try:
                created = await self._upsert_node(code, node_data, country, level, subject)
                if created:
                    summary.nodes_created += 1
                else:
                    summary.nodes_updated += 1
                summary.by_subject[subject] = summary.by_subject.get(subject, 0) + 1
            except Exception as exc:
                logger.warning(
                    "node_upsert_error",
                    code=code,
                    country=country,
                    error=str(exc),
                )
                summary.errors += 1

        await self.db_session.flush()

    async def _upsert_node(
        self,
        code: str,
        node_data: dict,
        country: str,
        level: str,
        subject: str,
    ) -> bool:
        """Upsert a single CurriculumNode. Returns True if created, False if updated."""
        result = await self.db_session.execute(
            select(CurriculumNode).where(
                CurriculumNode.code == code,
                CurriculumNode.country == country,
            )
        )
        existing = result.scalar_one_or_none()

        # Extract grade from code (e.g. "B2.1.1.1" -> "B2")
        grade = self._extract_grade(code)

        # Each curriculum has unique strands - use NULL until we load strand definitions
        strand_id = node_data.get("strand_id")
        sub_strand_id = node_data.get("sub_strand_id")
        content_standard_number = node_data.get("content_standard_number", 1)

        title = node_data.get("title", code)
        description = node_data.get("description", "")
        severity = node_data.get("severity", 3)
        severity_rationale = node_data.get("severity_rationale")
        population_status = node_data.get("population_status", "skeleton")
        ghana_evidence = node_data.get("ghana_evidence")
        questions_required = node_data.get("questions_required", 2)
        confidence_threshold = node_data.get("confidence_threshold", 0.80)

        if existing:
            # Update existing node
            existing.title = title
            existing.description = description
            existing.severity = severity
            existing.severity_rationale = severity_rationale
            existing.population_status = population_status
            existing.ghana_evidence = ghana_evidence
            existing.questions_required = questions_required
            existing.confidence_threshold = confidence_threshold
            existing.level = level
            existing.subject = subject
            existing.grade = grade
            return False
        else:
            # Create new node
            node = CurriculumNode(
                code=code,
                grade=grade,
                country=country,
                subject=subject,
                level=level,
                strand_id=strand_id,
                sub_strand_id=sub_strand_id,
                content_standard_number=content_standard_number,
                title=title,
                description=description,
                severity=severity,
                severity_rationale=severity_rationale,
                population_status=population_status,
                ghana_evidence=ghana_evidence,
                questions_required=questions_required,
                confidence_threshold=confidence_threshold,
            )
            self.db_session.add(node)
            return True

    @staticmethod
    def _extract_grade(code: str) -> str:
        """Extract grade from node code. E.g. 'B2.1.1.1' -> 'B2'."""
        parts = code.split(".")
        if parts:
            return parts[0]
        return code
