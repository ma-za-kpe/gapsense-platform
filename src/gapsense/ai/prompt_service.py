"""
Multi-Country Prompt Service with Template Resolution

Loads v2.0 multi-country prompts, resolves country-specific parameters,
injects cultural context and L1 language content, and renders prompt templates.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

import structlog

from gapsense.config import Settings

logger = structlog.get_logger(__name__)


@dataclass
class CountryConfig:
    """Country-specific configuration loaded from prompt library and country_config.json."""

    country_code: str
    country_name: str
    curriculum_authority: str
    currency: str
    common_foods: list[str]
    common_names: list[str]
    household_materials: list[str]
    geographic_contexts: list[str]
    active_levels: list[str] = field(default_factory=lambda: ["primary"])
    active_subjects: dict[str, list[str]] = field(
        default_factory=lambda: {"primary": ["mathematics"]}
    )
    supported_languages: list[str] = field(default_factory=lambda: ["en"])
    timezone: str = "GMT"


@dataclass
class L1LanguageContext:
    """L1 language context loaded from languages/{country}/{language}.json."""

    language_code: str
    language_name: str
    greetings: list[str]
    encouragement_phrases: list[str]
    math_vocabulary: dict[str, str]
    materials: dict[str, str]
    action_verbs: dict[str, str]


@dataclass
class RenderedPrompt:
    """Fully resolved prompt ready for AI client."""

    prompt_id: str
    system_prompt: str
    user_template: str | None
    model: str
    temperature: float
    max_tokens: int
    country: str
    language: str | None


# Mapping from prompt library country keys to country codes
_COUNTRY_KEY_TO_CODE: dict[str, str] = {
    "ghana": "GH",
    "uganda": "UG",
    "kenya": "KE",
    "nigeria": "NG",
}

_COUNTRY_CODE_TO_KEY: dict[str, str] = {v: k for k, v in _COUNTRY_KEY_TO_CODE.items()}

# Mapping from country keys to display names
_COUNTRY_KEY_TO_NAME: dict[str, str] = {
    "ghana": "Ghana",
    "uganda": "Uganda",
    "kenya": "Kenya",
    "nigeria": "Nigeria",
}


class PromptService:
    """Multi-country prompt service with template resolution."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._prompts: dict[str, dict[str, Any]] = {}
        self._metadata: dict[str, Any] = {}
        self._country_configs: dict[str, CountryConfig] = {}
        self._language_contexts: dict[str, dict[str, L1LanguageContext]] = {}

        self._load_prompt_library()
        self._load_country_configs()
        self._load_language_contexts()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render_prompt(
        self,
        prompt_id: str,
        *,
        country: str,
        language: str | None = None,
        extra_context: dict[str, str] | None = None,
    ) -> RenderedPrompt:
        """Load prompt, resolve country placeholders, inject L1 context.

        Args:
            prompt_id: Prompt identifier (e.g. 'DIAG-001').
            country: Country code (e.g. 'GH') or key (e.g. 'ghana').
            language: Optional L1 language code (e.g. 'tw').
            extra_context: Additional key-value pairs to substitute.

        Raises:
            ValueError: If country or language not supported.
            KeyError: If prompt_id not found.
        """
        # Normalize country to key
        country_key = self._normalize_country(country)
        config = self._country_configs.get(country_key)
        if config is None:
            supported = self.get_supported_countries()
            raise ValueError(f"Unsupported country '{country}'. Supported countries: {supported}")

        # Validate language if specified
        if language is not None:
            supported_langs = config.supported_languages
            if language not in supported_langs:
                raise ValueError(
                    f"Unsupported language '{language}' for country '{config.country_name}'. "
                    f"Supported languages: {supported_langs}"
                )

        # Load raw prompt
        if prompt_id not in self._prompts:
            available = sorted(self._prompts.keys())
            raise KeyError(f"Prompt '{prompt_id}' not found. Available prompts: {available}")

        prompt_data = self._prompts[prompt_id]
        system_prompt = prompt_data.get("system_prompt", "")
        user_template = prompt_data.get("user_template")

        # Step 1: Substitute country placeholders
        country_subs = self._build_country_substitutions(config)
        system_prompt = self._substitute(system_prompt, country_subs)
        if user_template:
            user_template = self._substitute(user_template, country_subs)

        # Step 2: Inject L1 language context if specified
        if language is not None:
            lang_subs = self._build_language_substitutions(country_key, language)
            system_prompt = self._substitute(system_prompt, lang_subs)
            if user_template:
                user_template = self._substitute(user_template, lang_subs)

        # Step 3: Substitute extra_context
        if extra_context:
            system_prompt = self._substitute(system_prompt, extra_context)
            if user_template:
                user_template = self._substitute(user_template, extra_context)

        return RenderedPrompt(
            prompt_id=prompt_id,
            system_prompt=system_prompt,
            user_template=user_template,
            model=prompt_data.get("model", "claude-sonnet-4-6"),
            temperature=prompt_data.get("temperature", 0.3),
            max_tokens=prompt_data.get("max_tokens", 2048),
            country=config.country_code,
            language=language,
        )

    def get_supported_countries(self) -> list[str]:
        """Return list of supported country codes."""
        return sorted(c.country_code for c in self._country_configs.values())

    def get_supported_languages(self, country: str) -> list[str]:
        """Return list of supported language codes for a country.

        Raises:
            ValueError: If country not supported.
        """
        country_key = self._normalize_country(country)
        config = self._country_configs.get(country_key)
        if config is None:
            supported = self.get_supported_countries()
            raise ValueError(f"Unsupported country '{country}'. Supported countries: {supported}")
        return list(config.supported_languages)

    def list_prompts(self) -> list[str]:
        """Return sorted list of all prompt IDs."""
        return sorted(self._prompts.keys())

    # ------------------------------------------------------------------
    # Private: Loading
    # ------------------------------------------------------------------

    def _load_prompt_library(self) -> None:
        """Load prompts from v2.0 prompt library JSON."""
        path = self._settings.prompt_library_path
        if not path.exists():
            logger.warning(
                "prompt_library_not_found",
                path=str(path),
                msg="Working with empty prompts — v2.0 library not mounted yet.",
            )
            return

        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            self._metadata = data.get("metadata", {})
            self._prompts = data.get("prompts", {})

            # Also load country_config from prompt library
            raw_country_config = data.get("country_config", {})
            for country_key, cfg_data in raw_country_config.items():
                country_key_lower = country_key.lower()
                self._country_configs[country_key_lower] = self._parse_country_config(
                    country_key_lower, cfg_data
                )

            logger.info(
                "prompt_library_loaded",
                version=self._metadata.get("version"),
                prompt_count=len(self._prompts),
                countries=list(self._country_configs.keys()),
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.error("prompt_library_load_error", path=str(path), error=str(exc))

    def _load_country_configs(self) -> None:
        """Load additional country configs from curricula/{country}/country_config.json."""
        curricula_path = self._settings.curricula_base_path
        if not curricula_path.exists():
            logger.debug("curricula_path_not_found", path=str(curricula_path))
            return

        for country_dir in curricula_path.iterdir():
            if not country_dir.is_dir() or country_dir.name.startswith("."):
                continue

            config_file = country_dir / "country_config.json"
            if not config_file.exists():
                continue

            try:
                with open(config_file, encoding="utf-8") as f:
                    cfg_data = json.load(f)

                country_key = country_dir.name.lower()
                if country_key in self._country_configs:
                    # Merge additional data into existing config
                    self._merge_country_config(country_key, cfg_data)
                else:
                    self._country_configs[country_key] = self._parse_country_config(
                        country_key, cfg_data
                    )

                logger.debug("country_config_loaded", country=country_key)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    "country_config_load_error",
                    path=str(config_file),
                    error=str(exc),
                )

    def _load_language_contexts(self) -> None:
        """Load L1 language files from languages/{country}/{language}.json."""
        languages_path = self._settings.languages_base_path
        if not languages_path.exists():
            logger.debug("languages_path_not_found", path=str(languages_path))
            return

        for country_dir in languages_path.iterdir():
            if not country_dir.is_dir() or country_dir.name.startswith("."):
                continue

            country_key = country_dir.name.lower()
            self._language_contexts.setdefault(country_key, {})

            for lang_file in country_dir.iterdir():
                if lang_file.suffix != ".json":
                    continue

                try:
                    with open(lang_file, encoding="utf-8") as f:
                        lang_data = json.load(f)

                    lang_code = lang_file.stem
                    self._language_contexts[country_key][lang_code] = L1LanguageContext(
                        language_code=lang_data.get("language_code", lang_code),
                        language_name=lang_data.get("language_name", lang_code),
                        greetings=lang_data.get("greetings", []),
                        encouragement_phrases=lang_data.get("encouragement_phrases", []),
                        math_vocabulary=lang_data.get("math_vocabulary", {}),
                        materials=lang_data.get("materials", {}),
                        action_verbs=lang_data.get("action_verbs", {}),
                    )
                    logger.debug(
                        "language_context_loaded",
                        country=country_key,
                        language=lang_code,
                    )
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning(
                        "language_context_load_error",
                        path=str(lang_file),
                        error=str(exc),
                    )

    # ------------------------------------------------------------------
    # Private: Parsing helpers
    # ------------------------------------------------------------------

    def _parse_country_config(self, country_key: str, data: dict[str, Any]) -> CountryConfig:
        """Parse a country config dict into a CountryConfig dataclass."""
        country_code = _COUNTRY_KEY_TO_CODE.get(country_key, country_key.upper()[:2])
        country_name = _COUNTRY_KEY_TO_NAME.get(country_key, country_key.title())

        # Currency can be a string or a dict with major/major_name
        currency_raw = data.get("currency", "")
        if isinstance(currency_raw, dict):
            major = currency_raw.get("major", "")
            major_name = currency_raw.get("major_name", "")
            currency = f"{major} ({major_name})" if major_name else major
        else:
            currency = str(currency_raw)

        # Languages: extract l1_codes from nested structure or flat list
        languages_raw = data.get("languages", {})
        if isinstance(languages_raw, dict):
            supported_languages = ["en"] + languages_raw.get("l1_codes", [])
        elif isinstance(languages_raw, list):
            supported_languages = languages_raw
        else:
            supported_languages = ["en"]

        # Active subjects from active_subjects or default
        active_subjects_raw = data.get("active_subjects", {})
        if not active_subjects_raw:
            active_subjects_raw = {"primary": ["mathematics"]}

        return CountryConfig(
            country_code=country_code,
            country_name=country_name,
            curriculum_authority=data.get("curriculum_authority", ""),
            currency=currency,
            common_foods=data.get("common_foods", []),
            common_names=data.get("common_names", []),
            household_materials=data.get("household_materials", []),
            geographic_contexts=data.get("geographic_contexts", []),
            active_levels=data.get("active_levels", ["primary"]),
            active_subjects=active_subjects_raw,
            supported_languages=supported_languages,
            timezone=data.get("timezone", "GMT"),
        )

    def _merge_country_config(self, country_key: str, data: dict[str, Any]) -> None:
        """Merge additional country config data into an existing CountryConfig."""
        existing = self._country_configs[country_key]

        # Merge lists (extend without duplicates)
        for list_field in (
            "common_foods",
            "common_names",
            "household_materials",
            "geographic_contexts",
        ):
            new_items = data.get(list_field, [])
            current = getattr(existing, list_field)
            for item in new_items:
                if item not in current:
                    current.append(item)

        # Merge active_levels
        for level in data.get("active_levels", []):
            if level not in existing.active_levels:
                existing.active_levels.append(level)

        # Merge active_subjects
        for level, subjects in data.get("active_subjects", {}).items():
            if level not in existing.active_subjects:
                existing.active_subjects[level] = subjects
            else:
                for subj in subjects:
                    if subj not in existing.active_subjects[level]:
                        existing.active_subjects[level].append(subj)

        # Merge supported_languages
        languages_raw = data.get("languages", data.get("supported_languages", []))
        if isinstance(languages_raw, dict):
            new_langs = languages_raw.get("l1_codes", [])
        elif isinstance(languages_raw, list):
            new_langs = languages_raw
        else:
            new_langs = []
        for lang in new_langs:
            if lang not in existing.supported_languages:
                existing.supported_languages.append(lang)

        # Override scalar fields if present
        if "curriculum_authority" in data:
            existing.curriculum_authority = data["curriculum_authority"]
        if "timezone" in data:
            existing.timezone = data["timezone"]

    def _normalize_country(self, country: str) -> str:
        """Normalize country input to lowercase key (e.g. 'GH' -> 'ghana')."""
        lower = country.lower()
        # Already a key?
        if lower in self._country_configs:
            return lower
        # Try code -> key mapping
        return _COUNTRY_CODE_TO_KEY.get(country.upper(), lower)

    # ------------------------------------------------------------------
    # Private: Template substitution
    # ------------------------------------------------------------------

    def _build_country_substitutions(self, config: CountryConfig) -> dict[str, str]:
        """Build substitution dict from CountryConfig."""
        return {
            "country": config.country_name,
            "curriculum_authority": config.curriculum_authority,
            "common_foods": ", ".join(config.common_foods),
            "common_names": ", ".join(config.common_names),
            "household_materials": ", ".join(config.household_materials),
            "currency": config.currency,
            "geographic_contexts": ", ".join(config.geographic_contexts),
        }

    def _build_language_substitutions(self, country_key: str, language: str) -> dict[str, str]:
        """Build substitution dict from L1LanguageContext."""
        lang_ctx = self._language_contexts.get(country_key, {}).get(language)
        if lang_ctx is None:
            return {}

        subs: dict[str, str] = {
            "l1_language_name": lang_ctx.language_name,
            "l1_greetings": ", ".join(lang_ctx.greetings),
            "l1_encouragement": ", ".join(lang_ctx.encouragement_phrases),
        }

        if lang_ctx.math_vocabulary:
            vocab_items = [f"{k}: {v}" for k, v in lang_ctx.math_vocabulary.items()]
            subs["l1_math_vocabulary"] = "; ".join(vocab_items)

        if lang_ctx.materials:
            mat_items = [f"{k}: {v}" for k, v in lang_ctx.materials.items()]
            subs["l1_materials"] = "; ".join(mat_items)

        if lang_ctx.action_verbs:
            verb_items = [f"{k}: {v}" for k, v in lang_ctx.action_verbs.items()]
            subs["l1_action_verbs"] = "; ".join(verb_items)

        return subs

    @staticmethod
    def _substitute(text: str, substitutions: dict[str, str]) -> str:
        """Replace {{key}} placeholders in text with values from substitutions."""
        for key, value in substitutions.items():
            text = text.replace(f"{{{{{key}}}}}", value)
        return text

    @staticmethod
    def _find_unresolved_placeholders(text: str) -> list[str]:
        """Find any remaining {{...}} placeholders in text."""
        return re.findall(r"\{\{(\w+)\}\}", text)
