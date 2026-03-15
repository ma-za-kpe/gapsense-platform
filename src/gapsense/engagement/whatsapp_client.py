"""
WhatsApp Client - Backward Compatibility Shim

DEPRECATED: Use gapsense.engagement.whatsapp.get_whatsapp_client() instead.

This module preserves the WhatsAppClient.from_settings() API so existing code
continues to work during migration. New code should use the provider abstraction.
"""

from __future__ import annotations

from gapsense.engagement.whatsapp.base import WhatsAppError, WhatsAppProvider
from gapsense.engagement.whatsapp.factory import get_whatsapp_client

# Re-export WhatsAppError for backward compatibility
__all__ = ["WhatsAppClient", "WhatsAppError"]


class WhatsAppClient:
    """Backward-compatible wrapper that delegates to the configured provider.

    DEPRECATED: Use get_whatsapp_client() from gapsense.engagement.whatsapp instead.
    """

    _instance: WhatsAppProvider | None = None

    @classmethod
    def from_settings(cls) -> WhatsAppProvider:
        """Create client from application settings.

        Returns the configured WhatsApp provider (Meta or Twilio)
        based on the WHATSAPP_PROVIDER setting.
        """
        return get_whatsapp_client()
