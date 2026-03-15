"""
Unit tests for CurriculumLoader.

Tests instantiation, directory walking, upsert logic, error resilience,
and path-to-column mapping using tmp_path and mocked database sessions.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from gapsense.services.curriculum_loader import (
    CountrySummary,
    CurriculumLoader,
    LoadSummary,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(tmp_path: Path) -> MagicMock:
    """Create a mock Settings pointing at tmp_path as curricula base."""
    settings = MagicMock()
    settings.curricula_base_path = tmp_path / "curricula"
    return settings


def _write_curriculum_json(
    base: Path,
    country: str,
    level: str,
    subject: str,
    filename: str,
    data: dict,
) -> Path:
    """Write a curriculum JSON file in the expected directory structure."""
    dir_path = base / "curricula" / country / level / subject
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / filename
    file_path.write_text(json.dumps(data))
    return file_path


def _mock_session_no_existing() -> AsyncMock:
    """Return an AsyncMock session where every SELECT returns no existing node."""
    session = AsyncMock()
    # execute() returns a result whose scalar_one_or_none() returns None (no existing)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    session.flush = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCurriculumLoaderInstantiation:
    """Test that CurriculumLoader can be instantiated."""

    def test_instantiation(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        session = AsyncMock()
        loader = CurriculumLoader(db_session=session, settings=settings)
        assert loader.db_session is session
        assert loader.base_path == tmp_path / "curricula"

    def test_instantiation_stores_settings(self, tmp_path: Path) -> None:
        settings = _make_settings(tmp_path)
        session = AsyncMock()
        loader = CurriculumLoader(db_session=session, settings=settings)
        assert loader.settings is settings


class TestLoadFromTempDirectory:
    """Test loading from a temp directory with sample JSON files."""

    @pytest.mark.asyncio
    async def test_load_single_file(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "nodes.json",
            {
                "B2.1.1.1": {
                    "title": "Counting up to 1000",
                    "description": "Count objects up to 1000",
                    "severity": 3,
                },
            },
        )
        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_files == 1
        assert summary.total_nodes_created == 1
        assert summary.total_errors == 0
        assert "GH" in summary.by_country

    @pytest.mark.asyncio
    async def test_load_multiple_files(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "a.json",
            {"B2.1.1.1": {"title": "Node A", "description": "Desc A", "severity": 2}},
        )
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "b.json",
            {"B3.1.1.1": {"title": "Node B", "description": "Desc B", "severity": 4}},
        )
        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_files == 2
        assert summary.total_nodes_created == 2

    @pytest.mark.asyncio
    async def test_load_country_specific(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "nodes.json",
            {"B2.1.1.1": {"title": "GH Node", "description": "Desc", "severity": 3}},
        )
        _write_curriculum_json(
            tmp_path,
            "UG",
            "primary",
            "mathematics",
            "nodes.json",
            {"U2.1.1.1": {"title": "UG Node", "description": "Desc", "severity": 3}},
        )
        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_country("GH")

        assert summary.total_files == 1
        assert summary.total_nodes_created == 1
        assert "GH" in summary.by_country
        assert "UG" not in summary.by_country

    @pytest.mark.asyncio
    async def test_load_missing_base_path(self, tmp_path: Path) -> None:
        """Loading when base path doesn't exist returns empty summary."""
        settings = _make_settings(tmp_path)
        # Don't create the curricula directory
        session = _mock_session_no_existing()
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_files == 0
        assert summary.total_nodes_created == 0

    @pytest.mark.asyncio
    async def test_load_missing_country_dir(self, tmp_path: Path) -> None:
        """Loading a non-existent country returns empty summary."""
        (tmp_path / "curricula").mkdir(parents=True)
        settings = _make_settings(tmp_path)
        session = _mock_session_no_existing()
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_country("XX")

        assert summary.total_files == 0


class TestUpsertLogic:
    """Test that loading same files twice produces updates, not duplicates."""

    @pytest.mark.asyncio
    async def test_upsert_second_load_updates(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "nodes.json",
            {"B2.1.1.1": {"title": "Node", "description": "Desc", "severity": 3}},
        )
        settings = _make_settings(tmp_path)

        # First load: no existing nodes
        session1 = _mock_session_no_existing()
        loader1 = CurriculumLoader(db_session=session1, settings=settings)
        summary1 = await loader1.load_all_countries()
        assert summary1.total_nodes_created == 1
        assert summary1.total_nodes_updated == 0

        # Second load: simulate existing node found
        session2 = AsyncMock()
        existing_node = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_node
        session2.execute.return_value = mock_result
        session2.flush = AsyncMock()

        loader2 = CurriculumLoader(db_session=session2, settings=settings)
        summary2 = await loader2.load_all_countries()
        assert summary2.total_nodes_created == 0
        assert summary2.total_nodes_updated == 1


class TestErrorResilience:
    """Test that invalid JSON files are skipped and loading continues."""

    @pytest.mark.asyncio
    async def test_invalid_json_skipped(self, tmp_path: Path) -> None:
        # Write a valid file
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "valid.json",
            {"B2.1.1.1": {"title": "Valid", "description": "Desc", "severity": 3}},
        )
        # Write an invalid JSON file
        bad_dir = tmp_path / "curricula" / "GH" / "primary" / "mathematics"
        (bad_dir / "invalid.json").write_text("{bad json content")

        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_files == 2
        assert summary.total_nodes_created == 1
        assert summary.total_errors == 1

    @pytest.mark.asyncio
    async def test_non_dict_json_skipped(self, tmp_path: Path) -> None:
        """A JSON file containing an array instead of object is an error."""
        dir_path = tmp_path / "curricula" / "GH" / "primary" / "mathematics"
        dir_path.mkdir(parents=True)
        (dir_path / "array.json").write_text(json.dumps([1, 2, 3]))

        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_errors == 1
        assert summary.total_nodes_created == 0

    @pytest.mark.asyncio
    async def test_multiple_invalid_files_counted(self, tmp_path: Path) -> None:
        bad_dir = tmp_path / "curricula" / "GH" / "primary" / "mathematics"
        bad_dir.mkdir(parents=True)
        (bad_dir / "bad1.json").write_text("not json")
        (bad_dir / "bad2.json").write_text("{also bad")

        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_errors == 2
        assert summary.total_files == 2


class TestPathToColumnMapping:
    """Test that country, level, subject are extracted from directory path."""

    @pytest.mark.asyncio
    async def test_country_from_path(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "KE",
            "secondary",
            "english",
            "nodes.json",
            {"K1.1.1.1": {"title": "Kenya Node", "description": "Desc", "severity": 2}},
        )
        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        await loader.load_all_countries()

        # Verify the node was added with correct country/level/subject
        # The session.add() call should have been made with a CurriculumNode
        add_call = session.add.call_args
        assert add_call is not None
        node = add_call[0][0]
        assert node.country == "KE"
        assert node.level == "secondary"
        assert node.subject == "english"

    @pytest.mark.asyncio
    async def test_grade_extracted_from_code(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "nodes.json",
            {"B4.2.3.1": {"title": "Grade 4 Node", "description": "Desc", "severity": 3}},
        )
        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        await loader.load_all_countries()

        node = session.add.call_args[0][0]
        assert node.grade == "B4"

    @pytest.mark.asyncio
    async def test_multiple_countries_mapped(self, tmp_path: Path) -> None:
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "n.json",
            {"B1.1.1.1": {"title": "GH", "description": "D", "severity": 1}},
        )
        _write_curriculum_json(
            tmp_path,
            "NG",
            "primary",
            "mathematics",
            "n.json",
            {"N1.1.1.1": {"title": "NG", "description": "D", "severity": 1}},
        )
        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert "GH" in summary.by_country
        assert "NG" in summary.by_country
        assert summary.total_nodes_created == 2


class TestCountryConfig:
    """Test that country_config.json filters active levels and subjects."""

    @pytest.mark.asyncio
    async def test_active_levels_filter(self, tmp_path: Path) -> None:
        """Only active levels from country_config are loaded."""
        # Write country_config with only "primary" active
        config_dir = tmp_path / "curricula" / "GH"
        config_dir.mkdir(parents=True)
        (config_dir / "country_config.json").write_text(
            json.dumps({"active_levels": ["primary"], "active_subjects": {}})
        )
        # Write nodes in primary (should load) and secondary (should skip)
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "n.json",
            {"B1.1.1.1": {"title": "Primary", "description": "D", "severity": 1}},
        )
        _write_curriculum_json(
            tmp_path,
            "GH",
            "secondary",
            "mathematics",
            "n.json",
            {"S1.1.1.1": {"title": "Secondary", "description": "D", "severity": 1}},
        )

        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_files == 1
        assert summary.total_nodes_created == 1

    @pytest.mark.asyncio
    async def test_active_subjects_filter(self, tmp_path: Path) -> None:
        """Only active subjects for a level are loaded."""
        config_dir = tmp_path / "curricula" / "GH"
        config_dir.mkdir(parents=True)
        (config_dir / "country_config.json").write_text(
            json.dumps(
                {
                    "active_levels": ["primary"],
                    "active_subjects": {"primary": ["mathematics"]},
                }
            )
        )
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "mathematics",
            "n.json",
            {"B1.1.1.1": {"title": "Math", "description": "D", "severity": 1}},
        )
        _write_curriculum_json(
            tmp_path,
            "GH",
            "primary",
            "english",
            "n.json",
            {"E1.1.1.1": {"title": "English", "description": "D", "severity": 1}},
        )

        session = _mock_session_no_existing()
        settings = _make_settings(tmp_path)
        loader = CurriculumLoader(db_session=session, settings=settings)

        summary = await loader.load_all_countries()

        assert summary.total_files == 1
        assert summary.by_country["GH"].by_subject.get("mathematics", 0) == 1
        assert summary.by_country["GH"].by_subject.get("english", 0) == 0


class TestLoadSummaryDataclasses:
    """Test dataclass defaults."""

    def test_country_summary_defaults(self) -> None:
        cs = CountrySummary()
        assert cs.files == 0
        assert cs.nodes_created == 0
        assert cs.nodes_updated == 0
        assert cs.errors == 0
        assert cs.by_subject == {}

    def test_load_summary_defaults(self) -> None:
        ls = LoadSummary()
        assert ls.total_files == 0
        assert ls.total_nodes_created == 0
        assert ls.total_nodes_updated == 0
        assert ls.total_errors == 0
        assert ls.by_country == {}
