"""
Unit Tests for Settings v2.0 Configuration

Tests for the updated Settings class with multi-country data path properties.
Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7
"""

import pytest

from gapsense.config import Settings


class TestSettingsDefaults:
    """Test default settings values."""

    def test_settings_defaults(self, monkeypatch):
        monkeypatch.setenv("CI", "true")
        s = Settings()
        assert s.ENVIRONMENT in ("local", "staging", "production")
        assert s.LOG_LEVEL in ("DEBUG", "INFO", "WARNING", "ERROR")
        assert isinstance(s.DATABASE_URL, str)

    def test_environment_local(self, monkeypatch):
        monkeypatch.setenv("CI", "true")
        s = Settings(ENVIRONMENT="local")
        assert s.is_local is True
        assert s.is_production is False

    def test_environment_production(self, monkeypatch):
        monkeypatch.setenv("CI", "true")
        s = Settings(ENVIRONMENT="production")
        assert s.is_local is False
        assert s.is_production is True


class TestV20PathProperties:
    """Test all four new v2.0 data path properties resolve correctly.

    Validates: Requirements 3.1, 3.2, 3.3, 3.4
    """

    def test_prompt_library_path(self, tmp_path, monkeypatch):
        """Req 3.1: prompt_library_path resolves to prompts/gapsense_prompt_library_v2.0_multicountry.json."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        expected = tmp_path / "prompts" / "gapsense_prompt_library_v2.0_multicountry.json"
        assert s.prompt_library_path == expected

    def test_curricula_base_path(self, tmp_path, monkeypatch):
        """Req 3.2: curricula_base_path resolves to curricula/."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        expected = tmp_path / "curricula"
        assert s.curricula_base_path == expected

    def test_cultural_context_path(self, tmp_path, monkeypatch):
        """Req 3.3: cultural_context_path resolves to cultural_context/."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        expected = tmp_path / "cultural_context"
        assert s.cultural_context_path == expected

    def test_languages_base_path(self, tmp_path, monkeypatch):
        """Req 3.4: languages_base_path resolves to languages/."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        expected = tmp_path / "languages"
        assert s.languages_base_path == expected

    def test_all_paths_relative_to_data_path(self, tmp_path, monkeypatch):
        """All v2.0 paths are children of GAPSENSE_DATA_PATH."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        for prop in (
            s.prompt_library_path,
            s.curricula_base_path,
            s.cultural_context_path,
            s.languages_base_path,
        ):
            assert str(prop).startswith(str(tmp_path))


class TestValidateDataPath:
    """Test the validate_data_path validator.

    Validates: Requirements 3.5, 3.7
    """

    def test_validator_raises_when_curricula_missing(self, tmp_path, monkeypatch):
        """Req 3.5 / 3.7: ValueError when curricula/ directory does not exist."""
        # tmp_path exists but has no curricula/ subdirectory
        monkeypatch.delenv("CI", raising=False)
        with pytest.raises(ValueError, match="curricula"):
            Settings(GAPSENSE_DATA_PATH=tmp_path)

    def test_validator_raises_when_path_does_not_exist(self, tmp_path, monkeypatch):
        """ValueError when GAPSENSE_DATA_PATH itself does not exist."""
        monkeypatch.delenv("CI", raising=False)
        nonexistent = tmp_path / "does_not_exist"
        with pytest.raises(ValueError, match="does not exist"):
            Settings(GAPSENSE_DATA_PATH=nonexistent)

    def test_validator_passes_with_curricula_dir(self, tmp_path, monkeypatch):
        """Validator succeeds when curricula/ directory exists."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        assert tmp_path == s.GAPSENSE_DATA_PATH

    def test_validator_skipped_in_ci(self, tmp_path, monkeypatch):
        """Validator is skipped when CI=true env var is set."""
        monkeypatch.setenv("CI", "true")
        # No curricula/ dir, but CI=true should bypass validation
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        assert tmp_path == s.GAPSENSE_DATA_PATH


class TestBackwardCompatibility:
    """Test backward compatibility of prerequisite_graph_path.

    Validates: Requirement 3.6
    """

    def test_prerequisite_graph_path(self, tmp_path, monkeypatch):
        """Req 3.6: prerequisite_graph_path still points to curriculum/ (singular) v1.2 file."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        expected = tmp_path / "curriculum" / "gapsense_prerequisite_graph_v1.2.json"
        assert s.prerequisite_graph_path == expected

    def test_prerequisite_graph_path_uses_singular_curriculum(self, tmp_path, monkeypatch):
        """prerequisite_graph_path uses 'curriculum' (singular), not 'curricula' (plural)."""
        (tmp_path / "curricula").mkdir()
        monkeypatch.setenv("GAPSENSE_DATA_PATH", str(tmp_path))
        s = Settings(GAPSENSE_DATA_PATH=tmp_path)
        assert "curriculum" in s.prerequisite_graph_path.parts
        assert "curricula" not in s.prerequisite_graph_path.parts
