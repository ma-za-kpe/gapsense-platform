"""Tests for fail-closed, type-safe application configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from gapsense.config import Settings


def test_settings_accept_valid_curriculum_repository(tmp_path: Path) -> None:
    """A repository with the required curriculum directory is accepted."""
    (tmp_path / "curriculum").mkdir()

    configured = Settings(GAPSENSE_DATA_PATH=tmp_path)

    assert tmp_path == configured.GAPSENSE_DATA_PATH
    assert configured.prerequisite_graph_path == (
        tmp_path / "curriculum" / "gapsense_prerequisite_graph_v1.2.json"
    )
    assert configured.prompt_library_path == (
        tmp_path / "prompts" / "gapsense_prompt_library_v1.1.json"
    )
    assert configured.is_local is True
    assert configured.is_production is False
    assert str(configured.OLLAMA_BASE_URL) == "http://host.docker.internal:11434/"
    assert configured.OLLAMA_MODEL == "llama3.1:8b"


def test_settings_report_production_environment(tmp_path: Path) -> None:
    """Environment helpers distinguish production from local development."""
    (tmp_path / "curriculum").mkdir()

    configured = Settings(ENVIRONMENT="production", GAPSENSE_DATA_PATH=str(tmp_path))

    assert configured.is_production is True
    assert configured.is_local is False


def test_settings_reject_missing_data_repository(tmp_path: Path) -> None:
    """A missing proprietary-data repository fails configuration immediately."""
    missing = tmp_path / "absent"

    with pytest.raises(ValidationError, match="GAPSENSE_DATA_PATH does not exist"):
        Settings(GAPSENSE_DATA_PATH=missing)


def test_settings_reject_repository_without_curriculum(tmp_path: Path) -> None:
    """An unrelated directory cannot masquerade as the data repository."""
    with pytest.raises(ValidationError, match="missing curriculum/ directory"):
        Settings(GAPSENSE_DATA_PATH=tmp_path)
