"""
Meta WhatsApp Cloud API Provider

Implementation of WhatsAppProvider using Meta's Graph API v21.0.
This is the original WhatsAppClient refactored into the provider pattern.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from gapsense.engagement.whatsapp.base import WhatsAppError, WhatsAppProvider

logger = logging.getLogger(__name__)


class MetaWhatsAppProvider(WhatsAppProvider):
    """WhatsApp Cloud API (Meta) implementation.

    Uses Meta's Graph API v21.0 for message delivery.
    Supports native interactive buttons, lists, and templates.
    """

    def __init__(
        self,
        *,
        api_token: str,
        phone_number_id: str,
        base_url: str = "https://graph.facebook.com/v21.0",
    ):
        self.api_token = api_token
        self.phone_number_id = phone_number_id
        self.base_url = base_url
        self.endpoint = f"{base_url}/{phone_number_id}/messages"

    async def send_text_message(
        self,
        *,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> str:
        text_obj: dict[str, Any] = {"body": text}
        if preview_url:
            text_obj["preview_url"] = True

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": text_obj,
        }
        return await self._send_request(payload)

    async def send_button_message(
        self,
        *,
        to: str,
        body: str,
        buttons: list[dict[str, str]],
        header: str | None = None,
        footer: str | None = None,
    ) -> str:
        if len(buttons) > 3:
            raise ValueError("Maximum 3 buttons allowed")

        interactive: dict[str, Any] = {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {"id": btn["id"], "title": btn["title"]},
                    }
                    for btn in buttons
                ]
            },
        }
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._send_request(payload)

    async def send_list_message(
        self,
        *,
        to: str,
        body: str,
        button_text: str,
        sections: list[dict[str, Any]],
        header: str | None = None,
        footer: str | None = None,
    ) -> str:
        total_rows = sum(len(section.get("rows", [])) for section in sections)
        if total_rows > 10:
            raise ValueError("Maximum 10 list items allowed across all sections")

        interactive: dict[str, Any] = {
            "type": "list",
            "body": {"text": body},
            "action": {"button": button_text, "sections": sections},
        }
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "interactive",
            "interactive": interactive,
        }
        return await self._send_request(payload)

    async def send_template(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        template: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }
        if parameters:
            template["components"] = [{"type": "body", "parameters": parameters}]

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template,
        }
        return await self._send_request(payload)

    async def mark_as_read(self, *, message_id: str) -> bool:
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        try:
            await self._send_request(payload)
            return True
        except WhatsAppError:
            return False

    async def download_media(self, *, media_id: str) -> bytes:
        """Download media from Meta WhatsApp (2-step process).

        Step 1: GET /{media_id} to get download URL
        Step 2: GET {url} with auth to download actual file

        Args:
            media_id: Media ID from webhook

        Returns:
            Media file bytes

        Raises:
            WhatsAppError: If download fails
        """
        headers = {"Authorization": f"Bearer {self.api_token}"}

        try:
            async with httpx.AsyncClient() as client:
                # Step 1: Get media URL
                media_url_endpoint = f"{self.base_url}/{media_id}"
                response = await client.get(media_url_endpoint, headers=headers, timeout=30.0)

                if response.status_code != 200:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Unknown error")
                    logger.error(f"Failed to get media URL: {error_msg}")
                    raise WhatsAppError(f"Failed to get media URL: {error_msg}")

                media_data = response.json()
                download_url = media_data.get("url")

                if not download_url:
                    raise WhatsAppError("Media URL not found in response")

                # Step 2: Download actual file
                download_response = await client.get(download_url, headers=headers, timeout=60.0)

                if download_response.status_code != 200:
                    raise WhatsAppError(
                        f"Failed to download media: HTTP {download_response.status_code}"
                    )

                logger.info(
                    f"Downloaded media: {media_id} ({len(download_response.content)} bytes)"
                )
                return download_response.content

        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading media: {e}")
            raise WhatsAppError(f"HTTP error: {e}") from e
        except WhatsAppError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading media: {e}")
            raise WhatsAppError(f"Unexpected error: {e}") from e

    async def _send_request(self, payload: dict[str, Any]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint, json=payload, headers=headers, timeout=30.0
                )
                if response.status_code != 200:
                    error_data = response.json()
                    error_message = error_data.get("error", {}).get("message", "Unknown error")
                    error_code = error_data.get("error", {}).get("code", "unknown")
                    logger.error(
                        f"WhatsApp API error: {error_code} - {error_message}",
                        extra={"payload": payload, "response": error_data},
                    )
                    raise WhatsAppError(f"WhatsApp API error ({error_code}): {error_message}")

                response_data = response.json()
                messages = response_data.get("messages", [])
                if messages:
                    message_id: str = messages[0]["id"]
                    logger.info(
                        f"WhatsApp message sent successfully: {message_id}",
                        extra={"to": payload.get("to"), "type": payload.get("type")},
                    )
                    return message_id

                logger.warning(
                    "WhatsApp response missing message ID",
                    extra={"response": response_data},
                )
                return "unknown"

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending WhatsApp message: {e}")
            raise WhatsAppError(f"HTTP error: {e}") from e
        except WhatsAppError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}")
            raise WhatsAppError(f"Unexpected error: {e}") from e
