"""
Unit tests for PromptService.

Tests cover instantiation, template resolution, country/language validation,
and the public API methods.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest

from gapsense.ai.prompt_service import (
    CountryConfig,
    L1LanguageContext,
    PromptService,
    RenderedPrompt,
)
from gapsense.config import Settings

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prompt_library(
    prompts: dict | None = None,
    country_config: dict | None = None,
) -> dict:
    """Build a minimal v2.0 prompt library dict."""
    return {
        "metadata": {"version": "2.0.0", "total_prompts": len(prompts or {})},
        "prompts": prompts or {},
        "country_config": country_config or {},
    }


SAMPLE_COUNTRY_CONFIG = {
    "ghana": {
        "curriculum_authority": "NaCCA",
        "curriculum_name": "Standards-Based Curriculum",
        "currency": {"major": "GH₵", "major_name": "cedis"},
        "common_foods": ["kenkey", "banku"],
        "common_names": ["Kofi", "Ama"],
        "household_materials": ["bottle caps", "stones"],
        "geographic_contexts": ["Accra", "Kumasi"],
        "languages": {"official": "English", "l1_codes": ["tw", "ee"]},
        "timezone": "GMT",
    },
}

SAMPLE_PROMPT = {
    "TEST-001": {
        "id": "TEST-001",
        "name": "Test Prompt",
        "category": "test",
        "version": "2.0.0",
        "model": "claude-sonnet-4-5",
        "temperature": 0.3,
        "max_tokens": 2048,
        "system_prompt": (
            "You are helping a student in {{country}}. "
            "Curriculum: {{curriculum_authority}}. "
            "Foods: {{common_foods}}. "
            "Names: {{common_names}}. "
            "Materials: {{household_materials}}. "
            "Currency: {{currency}}. "
            "Regions: {{geographic_contexts}}."
        ),
        "user_template": "Student from {{country}} needs help.",
    },
}

SAMPLE_PROMPT_NO_PLACEHOLDERS = {
    "SIMPLE-001": {
        "id": "SIMPLE-001",
        "name": "Simple Prompt",
        "category": "test",
        "version": "2.0.0",
        "model": "claude-haiku-4-5",
        "temperature": 0.4,
        "max_tokens": 512,
        "system_prompt": "You are a helpful assistant.",
        "user_template": None,
    },
}


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create a temporary data directory with required structure."""
    (tmp_path / "curricula").mkdir()
    (tmp_path / "cultural_context").mkdir()
    (tmp_path / "languages").mkdir()
    (tmp_path / "prompts").mkdir()
    return tmp_path


@pytest.fixture
def write_prompt_library(tmp_data_dir: Path):
    """Factory fixture to write a prompt library JSON file."""

    def _write(
        prompts: dict | None = None,
        country_config: dict | None = None,
    ) -> Path:
        lib = _make_prompt_library(prompts=prompts, country_config=country_config)
        lib_path = tmp_data_dir / "prompts" / "gapsense_prompt_library_v2.0_multicountry.json"
        lib_path.write_text(json.dumps(lib), encoding="utf-8")
        return lib_path

    return _write


@pytest.fixture
def mock_settings(tmp_data_dir: Path):
    """Return a Settings-like object pointing at the tmp data dir."""
    with patch.object(Settings, "__init__", lambda self: None):
        s = Settings.__new__(Settings)

    # Patch the computed properties to point at tmp_data_dir
    type(s).prompt_library_path = PropertyMock(
        return_value=tmp_data_dir / "prompts" / "gapsense_prompt_library_v2.0_multicountry.json"
    )
    type(s).curricula_base_path = PropertyMock(return_value=tmp_data_dir / "curricula")
    type(s).cultural_context_path = PropertyMock(return_value=tmp_data_dir / "cultural_context")
    type(s).languages_base_path = PropertyMock(return_value=tmp_data_dir / "languages")
    return s


def _write_language_file(tmp_data_dir: Path, country: str, lang_code: str, data: dict) -> None:
    lang_dir = tmp_data_dir / "languages" / country
    lang_dir.mkdir(parents=True, exist_ok=True)
    (lang_dir / f"{lang_code}.json").write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPromptServiceInstantiation:
    """Test that PromptService can be created with various data states."""

    def test_instantiation_with_empty_data(self, mock_settings):
        """PromptService works when no prompt library file exists."""
        svc = PromptService(mock_settings)
        assert svc.list_prompts() == []
        assert svc.get_supported_countries() == []

    def test_instantiation_with_prompt_library(self, mock_settings, write_prompt_library):
        """PromptService loads prompts and country configs from library."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        assert "TEST-001" in svc.list_prompts()
        assert "GH" in svc.get_supported_countries()


class TestRenderPrompt:
    """Test render_prompt template resolution."""

    def test_render_resolves_all_country_placeholders(self, mock_settings, write_prompt_library):
        """All {{...}} country placeholders are substituted."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        result = svc.render_prompt("TEST-001", country="GH")

        assert isinstance(result, RenderedPrompt)
        assert result.prompt_id == "TEST-001"
        assert result.country == "GH"
        assert result.language is None

        # No unresolved placeholders
        assert "{{" not in result.system_prompt
        assert "{{" not in (result.user_template or "")

        # Country values present
        assert "Ghana" in result.system_prompt
        assert "NaCCA" in result.system_prompt
        assert "kenkey" in result.system_prompt
        assert "Kofi" in result.system_prompt
        assert "bottle caps" in result.system_prompt
        assert "GH₵" in result.system_prompt
        assert "Accra" in result.system_prompt

    def test_render_with_country_key(self, mock_settings, write_prompt_library):
        """render_prompt accepts country key ('ghana') as well as code ('GH')."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        result = svc.render_prompt("TEST-001", country="ghana")
        assert result.country == "GH"
        assert "{{" not in result.system_prompt

    def test_render_prompt_without_placeholders(self, mock_settings, write_prompt_library):
        """Prompts without placeholders render cleanly."""
        write_prompt_library(
            prompts=SAMPLE_PROMPT_NO_PLACEHOLDERS,
            country_config=SAMPLE_COUNTRY_CONFIG,
        )
        svc = PromptService(mock_settings)
        result = svc.render_prompt("SIMPLE-001", country="GH")
        assert result.system_prompt == "You are a helpful assistant."
        assert result.user_template is None

    def test_render_with_extra_context(self, mock_settings, write_prompt_library):
        """extra_context substitutes additional placeholders."""
        prompts = {
            "CTX-001": {
                "id": "CTX-001",
                "name": "Context Prompt",
                "system_prompt": "Student: {{student_name}} in {{country}}.",
                "model": "claude-sonnet-4-5",
                "temperature": 0.3,
                "max_tokens": 1024,
            }
        }
        write_prompt_library(prompts=prompts, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        result = svc.render_prompt(
            "CTX-001",
            country="GH",
            extra_context={"student_name": "Kwame"},
        )
        assert "Kwame" in result.system_prompt
        assert "Ghana" in result.system_prompt
        assert "{{" not in result.system_prompt

    def test_render_with_language_context(self, mock_settings, write_prompt_library, tmp_data_dir):
        """L1 language context is injected when language is specified."""
        prompts = {
            "LANG-001": {
                "id": "LANG-001",
                "name": "Language Prompt",
                "system_prompt": (
                    "Country: {{country}}. "
                    "Greetings: {{l1_greetings}}. "
                    "Encouragement: {{l1_encouragement}}."
                ),
                "model": "claude-sonnet-4-5",
                "temperature": 0.3,
                "max_tokens": 1024,
            }
        }
        write_prompt_library(prompts=prompts, country_config=SAMPLE_COUNTRY_CONFIG)

        _write_language_file(
            tmp_data_dir,
            "ghana",
            "tw",
            {
                "language_code": "tw",
                "language_name": "Twi (Akan)",
                "greetings": ["Maakye", "Maaha"],
                "encouragement_phrases": ["Yɛ adwuma pa!", "Mo!"],
                "math_vocabulary": {"add": "ka ho"},
                "materials": {},
                "action_verbs": {},
            },
        )

        svc = PromptService(mock_settings)
        result = svc.render_prompt("LANG-001", country="GH", language="tw")

        assert result.language == "tw"
        assert "Maakye" in result.system_prompt
        assert "Yɛ adwuma pa!" in result.system_prompt
        assert "{{" not in result.system_prompt

    def test_render_model_and_config_from_prompt(self, mock_settings, write_prompt_library):
        """RenderedPrompt carries model/temperature/max_tokens from prompt data."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        result = svc.render_prompt("TEST-001", country="GH")
        assert result.model == "claude-sonnet-4-5"
        assert result.temperature == 0.3
        assert result.max_tokens == 2048


class TestUnsupportedCountryLanguage:
    """Test ValueError raised for unsupported country or language."""

    def test_unsupported_country_raises_valueerror(self, mock_settings, write_prompt_library):
        """ValueError raised with supported countries list."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)

        with pytest.raises(ValueError, match="Unsupported country"):
            svc.render_prompt("TEST-001", country="XX")

    def test_unsupported_country_includes_options(self, mock_settings, write_prompt_library):
        """ValueError message includes the list of supported countries."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)

        with pytest.raises(ValueError, match="GH"):
            svc.render_prompt("TEST-001", country="ZZ")

    def test_unsupported_language_raises_valueerror(self, mock_settings, write_prompt_library):
        """ValueError raised with supported languages list."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)

        with pytest.raises(ValueError, match="Unsupported language"):
            svc.render_prompt("TEST-001", country="GH", language="xx")

    def test_unsupported_language_includes_options(self, mock_settings, write_prompt_library):
        """ValueError message includes the list of supported languages."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)

        with pytest.raises(ValueError, match="tw"):
            svc.render_prompt("TEST-001", country="GH", language="xx")


class TestGetSupportedCountriesAndLanguages:
    """Test get_supported_countries and get_supported_languages."""

    def test_get_supported_countries_empty(self, mock_settings):
        """Returns empty list when no data loaded."""
        svc = PromptService(mock_settings)
        assert svc.get_supported_countries() == []

    def test_get_supported_countries(self, mock_settings, write_prompt_library):
        """Returns sorted country codes."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        assert svc.get_supported_countries() == ["GH"]

    def test_get_supported_languages(self, mock_settings, write_prompt_library):
        """Returns language codes for a country."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        langs = svc.get_supported_languages("GH")
        assert "en" in langs
        assert "tw" in langs
        assert "ee" in langs

    def test_get_supported_languages_unsupported_country(self, mock_settings, write_prompt_library):
        """ValueError raised for unsupported country."""
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)

        with pytest.raises(ValueError, match="Unsupported country"):
            svc.get_supported_languages("XX")


class TestListPrompts:
    """Test list_prompts method."""

    def test_list_prompts_empty(self, mock_settings):
        svc = PromptService(mock_settings)
        assert svc.list_prompts() == []

    def test_list_prompts_sorted(self, mock_settings, write_prompt_library):
        prompts = {
            "DIAG-001": {
                "id": "DIAG-001",
                "system_prompt": "a",
                "model": "m",
                "temperature": 0.3,
                "max_tokens": 100,
            },
            "ACT-001": {
                "id": "ACT-001",
                "system_prompt": "b",
                "model": "m",
                "temperature": 0.3,
                "max_tokens": 100,
            },
            "GUARD-001": {
                "id": "GUARD-001",
                "system_prompt": "c",
                "model": "m",
                "temperature": 0.3,
                "max_tokens": 100,
            },
        }
        write_prompt_library(prompts=prompts, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)
        assert svc.list_prompts() == ["ACT-001", "DIAG-001", "GUARD-001"]


class TestPromptNotFound:
    """Test KeyError raised for unknown prompt_id."""

    def test_unknown_prompt_raises_keyerror(self, mock_settings, write_prompt_library):
        write_prompt_library(prompts=SAMPLE_PROMPT, country_config=SAMPLE_COUNTRY_CONFIG)
        svc = PromptService(mock_settings)

        with pytest.raises(KeyError, match="NONEXISTENT"):
            svc.render_prompt("NONEXISTENT", country="GH")


class TestDataclasses:
    """Test dataclass construction."""

    def test_country_config_creation(self):
        cc = CountryConfig(
            country_code="GH",
            country_name="Ghana",
            curriculum_authority="NaCCA",
            currency="GH₵ (cedis)",
            common_foods=["kenkey"],
            common_names=["Kofi"],
            household_materials=["stones"],
            geographic_contexts=["Accra"],
        )
        assert cc.country_code == "GH"
        assert cc.active_levels == ["primary"]

    def test_l1_language_context_creation(self):
        lc = L1LanguageContext(
            language_code="tw",
            language_name="Twi (Akan)",
            greetings=["Maakye"],
            encouragement_phrases=["Mo!"],
            math_vocabulary={"add": "ka ho"},
            materials={},
            action_verbs={},
        )
        assert lc.language_code == "tw"

    def test_rendered_prompt_creation(self):
        rp = RenderedPrompt(
            prompt_id="TEST-001",
            system_prompt="Hello",
            user_template=None,
            model="claude-sonnet-4-5",
            temperature=0.3,
            max_tokens=2048,
            country="GH",
            language=None,
        )
        assert rp.prompt_id == "TEST-001"
        assert rp.language is None
