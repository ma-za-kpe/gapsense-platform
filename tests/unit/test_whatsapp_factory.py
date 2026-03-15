"""
Tests for WhatsApp Provider Factory

Tests factory pattern for creating Meta and Twilio providers based on configuration.
"""

from unittest.mock import patch

import pytest

from gapsense.engagement.whatsapp.factory import (
    WhatsAppProviderFactory,
    get_whatsapp_client,
    reset_whatsapp_client,
)
from gapsense.engagement.whatsapp.meta_provider import MetaWhatsAppProvider
from gapsense.engagement.whatsapp.twilio_provider import TwilioWhatsAppProvider


class TestWhatsAppProviderFactory:
    """Test WhatsAppProviderFactory creation logic."""

    def test_create_meta_provider(self):
        """Test factory creates Meta provider when configured."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"

            provider = WhatsAppProviderFactory.create()

            assert isinstance(provider, MetaWhatsAppProvider)
            assert provider.api_token == "test_token"
            assert provider.phone_number_id == "test_phone_id"

    def test_create_twilio_provider(self):
        """Test factory creates Twilio provider when configured."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "twilio"
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest123"
            mock_settings.TWILIO_AUTH_TOKEN = "test_auth_token"
            mock_settings.TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"
            # Ensure API Key settings are not set (factory prefers API Key over Auth Token)
            mock_settings.TWILIO_API_KEY_SID = None
            mock_settings.TWILIO_API_KEY_SECRET = None

            provider = WhatsAppProviderFactory.create()

            assert isinstance(provider, TwilioWhatsAppProvider)
            assert provider.account_sid == "ACtest123"
            assert provider.auth_token == "test_auth_token"
            assert provider.from_number == "whatsapp:+14155238886"

    def test_create_unknown_provider_raises_error(self):
        """Test factory raises ValueError for unknown provider."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "unknown"

            with pytest.raises(ValueError, match="Unknown WhatsApp provider: 'unknown'"):
                WhatsAppProviderFactory.create()

    def test_create_invalid_provider_shows_supported_list(self):
        """Test error message includes list of supported providers."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "invalid"

            with pytest.raises(ValueError, match="Supported: 'meta', 'twilio'"):
                WhatsAppProviderFactory.create()


class TestGetWhatsAppClient:
    """Test singleton accessor for WhatsApp client."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_whatsapp_client()

    def test_get_whatsapp_client_creates_singleton(self):
        """Test get_whatsapp_client creates provider on first call."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"

            client1 = get_whatsapp_client()
            client2 = get_whatsapp_client()

            assert client1 is client2  # Same instance
            assert isinstance(client1, MetaWhatsAppProvider)

    def test_get_whatsapp_client_reuses_instance(self):
        """Test get_whatsapp_client returns same instance on subsequent calls."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"

            # Call multiple times
            clients = [get_whatsapp_client() for _ in range(5)]

            # All should be the same instance
            assert all(client is clients[0] for client in clients)

    def test_reset_whatsapp_client_clears_singleton(self):
        """Test reset_whatsapp_client allows creating new instance."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "token1"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "phone_id1"

            client1 = get_whatsapp_client()

            # Reset and create new client with different settings
            reset_whatsapp_client()
            mock_settings.WHATSAPP_API_TOKEN = "token2"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "phone_id2"

            client2 = get_whatsapp_client()

            # Should be different instances
            assert client1 is not client2
            assert client1.api_token == "token1"
            assert client2.api_token == "token2"

    def test_get_whatsapp_client_with_twilio(self):
        """Test get_whatsapp_client works with Twilio provider."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "twilio"
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest"
            mock_settings.TWILIO_AUTH_TOKEN = "token"
            mock_settings.TWILIO_WHATSAPP_NUMBER = "whatsapp:+1234567890"

            client = get_whatsapp_client()

            assert isinstance(client, TwilioWhatsAppProvider)
            assert client.account_sid == "ACtest"


class TestBackwardCompatibility:
    """Test backward compatibility with old WhatsAppClient.from_settings()."""

    def setup_method(self):
        """Reset singleton before each test."""
        reset_whatsapp_client()

    def test_whatsapp_client_from_settings_delegates_to_factory(self):
        """Test WhatsAppClient.from_settings() uses factory."""
        from gapsense.engagement.whatsapp_client import WhatsAppClient

        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"

            client = WhatsAppClient.from_settings()

            assert isinstance(client, MetaWhatsAppProvider)
            assert client.api_token == "test_token"
