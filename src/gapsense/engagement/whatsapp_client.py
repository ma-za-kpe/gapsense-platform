"""
WhatsApp Cloud API Client

Sends messages to parents via WhatsApp Cloud API (direct integration).
Supports text, buttons, lists, and templates.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from gapsense.config import settings

logger = logging.getLogger(__name__)


class WhatsAppError(Exception):
    """WhatsApp API error."""

    pass


class WhatsAppClient:
    """Client for WhatsApp Cloud API.

    Handles sending messages to parents via WhatsApp.
    Uses Meta's Graph API v21.0.
    """

    def __init__(
        self,
        *,
        api_token: str,
        phone_number_id: str,
        base_url: str = "https://graph.facebook.com/v21.0",
    ):
        """Initialize WhatsApp client.

        Args:
            api_token: WhatsApp Cloud API access token
            phone_number_id: WhatsApp phone number ID (from Meta Business)
            base_url: Graph API base URL (default: v21.0)
        """
        self.api_token = api_token
        self.phone_number_id = phone_number_id
        self.base_url = base_url
        self.endpoint = f"{base_url}/{phone_number_id}/messages"

    @classmethod
    def from_settings(cls) -> WhatsAppClient:
        """Create client from application settings.

        Returns:
            WhatsAppClient instance configured from settings
        """
        return cls(
            api_token=settings.WHATSAPP_API_TOKEN,
            phone_number_id=settings.WHATSAPP_PHONE_NUMBER_ID,
        )

    async def send_text_message(
        self,
        *,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> str:
        """Send a text message.

        Args:
            to: Phone number in international format (e.g., +233501234567)
            text: Message text (max 4096 characters)
            preview_url: Enable link preview (default: False)

        Returns:
            WhatsApp message ID

        Raises:
            WhatsAppError: If API request fails
        """
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
        """Send an interactive button message.

        Args:
            to: Phone number in international format
            body: Message body text
            buttons: List of button dicts with 'id' and 'title' (max 3)
            header: Optional header text
            footer: Optional footer text

        Returns:
            WhatsApp message ID

        Raises:
            ValueError: If more than 3 buttons provided
            WhatsAppError: If API request fails
        """
        if len(buttons) > 3:
            raise ValueError("Maximum 3 buttons allowed")

        interactive = {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["title"],
                        },
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
        """Send an interactive list message.

        Args:
            to: Phone number in international format
            body: Message body text
            button_text: Text for the list button (e.g., "Choose Language")
            sections: List sections with rows (max 10 total rows)
            header: Optional header text
            footer: Optional footer text

        Returns:
            WhatsApp message ID

        Raises:
            ValueError: If more than 10 list items total
            WhatsAppError: If API request fails
        """
        # Count total rows across all sections
        total_rows = sum(len(section.get("rows", [])) for section in sections)
        if total_rows > 10:
            raise ValueError("Maximum 10 list items allowed across all sections")

        interactive = {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text,
                "sections": sections,
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

    async def send_template(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Send a message template.

        Templates must be pre-approved by Meta.
        Used for messages outside the 24-hour session window.

        Args:
            to: Phone number in international format
            template_name: Template name (e.g., "activity_followup")
            language_code: Language code (e.g., "en", "tw")
            parameters: Optional template parameters

        Returns:
            WhatsApp message ID

        Raises:
            WhatsAppError: If API request fails
        """
        template: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language_code},
        }

        if parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": parameters,
                }
            ]

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template,
        }

        return await self._send_request(payload)

    async def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Alias for send_template() for backward compatibility.

        Args:
            to: Phone number in international format
            template_name: Template name (e.g., "gapsense_welcome")
            language_code: Language code (e.g., "en", "tw")
            parameters: Optional template parameters

        Returns:
            WhatsApp message ID

        Raises:
            WhatsAppError: If API request fails
        """
        return await self.send_template(
            to=to,
            template_name=template_name,
            language_code=language_code,
            parameters=parameters,
        )

    async def mark_as_read(self, *, message_id: str) -> bool:
        """Mark a message as read.

        Args:
            message_id: WhatsApp message ID to mark as read

        Returns:
            True if successful

        Raises:
            WhatsAppError: If API request fails
        """
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

    async def _send_request(self, payload: dict[str, Any]) -> str:
        """Send API request to WhatsApp Cloud API.

        Args:
            payload: Request payload

        Returns:
            WhatsApp message ID from response

        Raises:
            WhatsAppError: If API request fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=30.0,
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
                    "WhatsApp response missing message ID", extra={"response": response_data}
                )
                return "unknown"

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending WhatsApp message: {e}")
            raise WhatsAppError(f"HTTP error: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp message: {e}")
            raise WhatsAppError(f"Unexpected error: {e}") from e
