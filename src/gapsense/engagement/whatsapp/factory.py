"""
WhatsApp Provider Factory

Creates the appropriate WhatsApp provider based on configuration.
Provides a singleton accessor for the application.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gapsense.config import settings

if TYPE_CHECKING:
    from gapsense.engagement.whatsapp.base import WhatsAppProvider

logger = logging.getLogger(__name__)

_client: WhatsAppProvider | None = None


class WhatsAppProviderFactory:
    """Factory to create WhatsApp provider based on config."""

    @staticmethod
    def create() -> WhatsAppProvider:
        """Create a WhatsApp provider instance based on WHATSAPP_PROVIDER setting.

        Returns:
            Configured WhatsAppProvider instance

        Raises:
            ValueError: If provider type is unknown
        """
        provider_type = settings.WHATSAPP_PROVIDER

        if provider_type == "meta":
            from gapsense.engagement.whatsapp.meta_provider import MetaWhatsAppProvider

            logger.info("Initializing Meta WhatsApp Cloud API provider")
            return MetaWhatsAppProvider(
                api_token=settings.WHATSAPP_API_TOKEN,
                phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
            )

        elif provider_type == "twilio":
            from gapsense.engagement.whatsapp.twilio_provider import TwilioWhatsAppProvider

            # Prefer API Key over Auth Token (more secure)
            if settings.TWILIO_API_KEY_SID and settings.TWILIO_API_KEY_SECRET:
                logger.info("Initializing Twilio WhatsApp provider (API Key auth)")
                return TwilioWhatsAppProvider(
                    account_sid=settings.TWILIO_ACCOUNT_SID,  # Real Account SID for API URL
                    auth_token=settings.TWILIO_API_KEY_SECRET,  # API Key Secret for auth
                    auth_username=settings.TWILIO_API_KEY_SID,  # API Key SID for auth
                    from_number=settings.TWILIO_WHATSAPP_NUMBER,
                )
            else:
                logger.info("Initializing Twilio WhatsApp provider (Auth Token)")
                return TwilioWhatsAppProvider(
                    account_sid=settings.TWILIO_ACCOUNT_SID,
                    auth_token=settings.TWILIO_AUTH_TOKEN,
                    from_number=settings.TWILIO_WHATSAPP_NUMBER,
                    # auth_username defaults to account_sid
                )

        else:
            raise ValueError(
                f"Unknown WhatsApp provider: '{provider_type}'. " "Supported: 'meta', 'twilio'"
            )


def get_whatsapp_client() -> WhatsAppProvider:
    """Get the configured WhatsApp client singleton.

    Returns:
        WhatsAppProvider instance (created on first call, reused after)
    """
    global _client
    if _client is None:
        _client = WhatsAppProviderFactory.create()
    return _client


def reset_whatsapp_client() -> None:
    """Reset the singleton (useful for testing or config changes)."""
    global _client
    _client = None
