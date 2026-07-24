"""Tests for fail-closed, type-safe application configuration."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from gapsense.config import Settings


def test_settings_accept_valid_curriculum_repository(tmp_path: Path) -> None:
    """A repository with the required curriculum directory is accepted."""
    (tmp_path / "curricula" / "ghana").mkdir(parents=True)
    (tmp_path / "curricula" / "uganda").mkdir()

    configured = Settings(GAPSENSE_DATA_PATH=tmp_path)

    assert tmp_path == configured.GAPSENSE_DATA_PATH
    assert configured.curricula_path == tmp_path / "curricula"
    assert configured.prompt_library_path == (
        tmp_path / "prompts" / "gapsense_prompt_library_v2.0_multicountry.json"
    )
    assert configured.is_local is True
    assert configured.is_production is False
    assert configured.ANALYTICS_MODE == "disabled"
    assert str(configured.OLLAMA_BASE_URL) == "http://host.docker.internal:11434/"
    assert configured.OLLAMA_MODEL == "llama3.1:8b"


def test_settings_report_production_environment(tmp_path: Path) -> None:
    """Environment helpers distinguish production from local development."""
    (tmp_path / "curricula" / "ghana").mkdir(parents=True)
    (tmp_path / "curricula" / "uganda").mkdir()

    configured = Settings(
        ENVIRONMENT="production",
        GAPSENSE_DATA_PATH=str(tmp_path),
    )

    assert configured.is_production is True
    assert configured.is_local is False
    assert configured.ANALYTICS_MODE == "disabled"


def test_settings_allow_aggregate_analytics_only_in_local_environment(tmp_path: Path) -> None:
    """The collection route cannot be enabled by staging or production configuration."""
    (tmp_path / "curricula" / "ghana").mkdir(parents=True)
    (tmp_path / "curricula" / "uganda").mkdir()

    local = Settings(
        ENVIRONMENT="local",
        ANALYTICS_MODE="local_aggregate",
        GAPSENSE_DATA_PATH=tmp_path,
    )

    assert local.ANALYTICS_MODE == "local_aggregate"
    for environment in ("staging", "production"):
        with pytest.raises(
            ValidationError,
            match="local_aggregate analytics is restricted to the local environment",
        ):
            Settings(
                ENVIRONMENT=environment,
                ANALYTICS_MODE="local_aggregate",
                GAPSENSE_DATA_PATH=tmp_path,
            )


def test_settings_reject_missing_data_repository(tmp_path: Path) -> None:
    """A missing proprietary-data repository fails configuration immediately."""
    missing = tmp_path / "absent"

    with pytest.raises(ValidationError, match="GAPSENSE_DATA_PATH does not exist"):
        Settings(GAPSENSE_DATA_PATH=missing)


def test_settings_reject_repository_without_curriculum(tmp_path: Path) -> None:
    """An unrelated directory cannot masquerade as the data repository."""
    with pytest.raises(
        ValidationError, match="missing canonical curricula/ghana and curricula/uganda"
    ):
        Settings(GAPSENSE_DATA_PATH=tmp_path)


def test_settings_reject_repository_with_only_one_country(tmp_path: Path) -> None:
    """Ghana-only or Uganda-only data cannot satisfy the two-country runtime contract."""
    (tmp_path / "curricula" / "ghana").mkdir(parents=True)

    with pytest.raises(
        ValidationError, match="missing canonical curricula/ghana and curricula/uganda"
    ):
        Settings(GAPSENSE_DATA_PATH=tmp_path)
