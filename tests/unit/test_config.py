"""
Unit Tests for Configuration

Tests for settings and configuration management.
"""

from pathlib import Path

from gapsense.config import Settings


def test_settings_defaults():
    """Test default settings values."""
    settings = Settings()

    assert settings.ENVIRONMENT in ["local", "staging", "production"]
    assert settings.LOG_LEVEL in ["DEBUG", "INFO", "WARNING", "ERROR"]
    assert isinstance(settings.DATABASE_URL, str)


def test_settings_computed_properties():
    """Test computed properties."""
    settings = Settings()

    # Check paths
    assert isinstance(settings.prerequisite_graph_path, Path)
    assert isinstance(settings.prompt_library_path, Path)

    # Check boolean helpers
    assert isinstance(settings.is_production, bool)
    assert isinstance(settings.is_local, bool)


def test_settings_environment_specific():
    """Test environment-specific behavior."""
    # Local environment
    settings_local = Settings(ENVIRONMENT="local")
    assert settings_local.is_local is True
    assert settings_local.is_production is False

    # Production environment
    settings_prod = Settings(ENVIRONMENT="production")
    assert settings_prod.is_local is False
    assert settings_prod.is_production is True
