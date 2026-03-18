"""
Property-based tests for PromptService.

# Feature: mvp-core-services, Property 5: Prompt Template Resolution Round-Trip
# Feature: mvp-core-services, Property 6: Unsupported Country/Language Rejection
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock, PropertyMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.ai.prompt_service import (
    CountryConfig,
    L1LanguageContext,
    PromptService,
)

# ---------------------------------------------------------------------------
# Hypothesis strategies
# ---------------------------------------------------------------------------

country_config_strategy = st.builds(
    CountryConfig,
    country_code=st.sampled_from(["GH", "UG", "KE", "NG"]),
    country_name=st.sampled_from(["Ghana", "Uganda", "Kenya", "Nigeria"]),
    curriculum_authority=st.text(
        min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L",))
    ),
    currency=st.text(
        min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=("L", "N", "S"))
    ),
    common_foods=st.lists(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=5,
    ),
    common_names=st.lists(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=5,
    ),
    household_materials=st.lists(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=5,
    ),
    geographic_contexts=st.lists(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=5,
    ),
    supported_languages=st.just(["en", "tw"]),
    timezone=st.just("GMT"),
)

l1_language_strategy = st.builds(
    L1LanguageContext,
    language_code=st.just("tw"),
    language_name=st.just("Twi"),
    greetings=st.lists(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=3,
    ),
    encouragement_phrases=st.lists(
        st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=3,
    ),
    math_vocabulary=st.dictionaries(
        st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=1,
        max_size=3,
    ),
    materials=st.dictionaries(
        st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=0,
        max_size=3,
    ),
    action_verbs=st.dictionaries(
        st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))),
        min_size=0,
        max_size=3,
    ),
)


def _build_prompt_service(
    country_config: CountryConfig,
    l1_context: L1LanguageContext | None = None,
    prompts: dict | None = None,
) -> PromptService:
    """Build a PromptService with injected configs (no filesystem access)."""
    mock_settings = MagicMock()
    type(mock_settings).prompt_library_path = PropertyMock(
        return_value=MagicMock(exists=MagicMock(return_value=False))
    )
    type(mock_settings).curricula_base_path = PropertyMock(
        return_value=MagicMock(exists=MagicMock(return_value=False))
    )
    type(mock_settings).languages_base_path = PropertyMock(
        return_value=MagicMock(exists=MagicMock(return_value=False))
    )

    svc = PromptService.__new__(PromptService)
    svc._settings = mock_settings
    svc._metadata = {"version": "2.0"}

    # Default prompts with all standard placeholders
    if prompts is None:
        prompts = {
            "DIAG-001": {
                "system_prompt": (
                    "You are helping in {{country}}. "
                    "Authority: {{curriculum_authority}}. "
                    "Foods: {{common_foods}}. "
                    "Names: {{common_names}}. "
                    "Materials: {{household_materials}}. "
                    "Currency: {{currency}}. "
                    "Geography: {{geographic_contexts}}."
                ),
                "user_template": None,
                "model": "claude-sonnet-4-5",
                "temperature": 0.3,
                "max_tokens": 2048,
            },
        }
    svc._prompts = prompts

    # Register country config
    country_key = country_config.country_name.lower()
    svc._country_configs = {country_key: country_config}

    # Register language context
    svc._language_contexts = {}
    if l1_context:
        svc._language_contexts[country_key] = {l1_context.language_code: l1_context}

    return svc


# ---------------------------------------------------------------------------
# Property 5: Prompt Template Resolution Round-Trip
# **Validates: Requirements 2.5, 2.6, 2.10**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    config=country_config_strategy,
    l1_ctx=l1_language_strategy,
)
def test_prompt_template_resolution_round_trip(
    config: CountryConfig,
    l1_ctx: L1LanguageContext,
):
    """Property 5: Prompt Template Resolution Round-Trip

    For any valid prompt template and any supported country config
    (with optional language), rendered output has zero unresolved
    {{...}} placeholders.
    """
    svc = _build_prompt_service(config, l1_ctx)

    # Render without language
    rendered = svc.render_prompt("DIAG-001", country=config.country_name)
    unresolved = re.findall(r"\{\{\w+\}\}", rendered.system_prompt)
    assert unresolved == [], f"Unresolved placeholders without language: {unresolved}"

    # Render with language
    rendered_l1 = svc.render_prompt("DIAG-001", country=config.country_name, language="tw")
    unresolved_l1 = re.findall(r"\{\{\w+\}\}", rendered_l1.system_prompt)
    assert unresolved_l1 == [], f"Unresolved placeholders with language: {unresolved_l1}"


# ---------------------------------------------------------------------------
# Property 6: Unsupported Country/Language Rejection
# **Validates: Requirements 2.7, 2.8**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    bad_country=st.text(
        min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))
    ).filter(
        lambda c: c.lower() not in ("ghana", "uganda", "kenya", "nigeria")
        and c.upper() not in ("GH", "UG", "KE", "NG")
    ),
)
def test_unsupported_country_rejection(bad_country: str):
    """Property 6a: Unsupported Country Rejection

    For any country not in supported list, render_prompt raises ValueError
    with valid options.
    """
    config = CountryConfig(
        country_code="GH",
        country_name="Ghana",
        curriculum_authority="NaCCA",
        currency="GH₵",
        common_foods=["fufu"],
        common_names=["Kwame"],
        household_materials=["bottle caps"],
        geographic_contexts=["Accra"],
    )
    svc = _build_prompt_service(config)

    with pytest.raises(ValueError, match="Unsupported country"):
        svc.render_prompt("DIAG-001", country=bad_country)


@settings(max_examples=100, deadline=None)
@given(
    bad_language=st.text(
        min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=("L",))
    ).filter(lambda l: l not in ("en", "tw")),
)
def test_unsupported_language_rejection(bad_language: str):
    """Property 6b: Unsupported Language Rejection

    For any language not in country's supported list, render_prompt raises
    ValueError with valid options.
    """
    config = CountryConfig(
        country_code="GH",
        country_name="Ghana",
        curriculum_authority="NaCCA",
        currency="GH₵",
        common_foods=["fufu"],
        common_names=["Kwame"],
        household_materials=["bottle caps"],
        geographic_contexts=["Accra"],
        supported_languages=["en", "tw"],
    )
    svc = _build_prompt_service(config)

    with pytest.raises(ValueError, match="Unsupported language"):
        svc.render_prompt("DIAG-001", country="ghana", language=bad_language)
