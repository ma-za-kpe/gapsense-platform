"""
WhatsApp Provider Abstraction Layer

Supports multiple WhatsApp providers (Meta Cloud API, Twilio) via a common interface.
Use get_whatsapp_client() to get the configured provider singleton.
"""

from gapsense.engagement.whatsapp.base import WhatsAppProvider
from gapsense.engagement.whatsapp.factory import get_whatsapp_client, reset_whatsapp_client

__all__ = ["WhatsAppProvider", "get_whatsapp_client", "reset_whatsapp_client"]
