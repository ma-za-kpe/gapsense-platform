"""
Twilio WhatsApp API Provider

Implementation of WhatsAppProvider using Twilio's WhatsApp Business API.
Falls back to numbered lists for interactive buttons/lists since Twilio
doesn't support native WhatsApp interactive messages.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from gapsense.engagement.whatsapp.base import WhatsAppError, WhatsAppProvider

logger = logging.getLogger(__name__)


class TwilioWhatsAppProvider(WhatsAppProvider):
    """Twilio WhatsApp API implementation.

    Key differences from Meta:
    - No native interactive buttons/lists (uses numbered text fallback)
    - Synchronous SDK wrapped in asyncio executor
    - Direct media URLs (no 2-step download)
    - Different webhook format (handled by webhook adapter)
    """

    def __init__(
        self,
        *,
        account_sid: str,
        auth_token: str,
        from_number: str,
        auth_username: str | None = None,
    ):
        """Initialize Twilio WhatsApp provider.

        Args:
            account_sid: Twilio Account SID (AC... for API URL)
            auth_token: Twilio Auth Token or API Key Secret
            from_number: Twilio WhatsApp sender number (e.g., "whatsapp:+14155238886")
            auth_username: HTTP Basic Auth username (defaults to account_sid, or set to API Key SID)
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.auth_username = (
            auth_username or account_sid
        )  # For API Key auth, this is the API Key SID
        self.from_number = from_number
        self.api_url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

    async def send_text_message(
        self,
        *,
        to: str,
        text: str,
        preview_url: bool = False,
    ) -> str:
        return await self._send_message(to=to, body=text)

    async def send_button_message(
        self,
        *,
        to: str,
        body: str,
        buttons: list[dict[str, str]],
        header: str | None = None,
        footer: str | None = None,
    ) -> str:
        """Send button message as numbered list (Twilio doesn't support native buttons)."""
        parts = []
        if header:
            parts.append(header)
            parts.append("")

        parts.append(body)
        parts.append("")

        for i, btn in enumerate(buttons, 1):
            parts.append(f"{i}. {btn['title']}")

        parts.append("")
        parts.append(f"Reply with a number (1-{len(buttons)})")

        if footer:
            parts.append("")
            parts.append(footer)

        return await self._send_message(to=to, body="\n".join(parts))

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
        """Send list message as numbered text (Twilio doesn't support native lists)."""
        parts = []
        if header:
            parts.append(header)
            parts.append("")

        parts.append(body)
        parts.append("")

        idx = 1
        for section in sections:
            section_title = section.get("title")
            if section_title:
                parts.append(f"*{section_title}*")

            for row in section.get("rows", []):
                title = row.get("title", "")
                description = row.get("description", "")
                line = f"{idx}. {title}"
                if description:
                    line += f" - {description}"
                parts.append(line)
                idx += 1

            parts.append("")

        parts.append(f"Reply with a number (1-{idx - 1})")

        if footer:
            parts.append("")
            parts.append(footer)

        return await self._send_message(to=to, body="\n".join(parts))

    async def send_template(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Send template message via Twilio Content API.

        Args:
            to: Phone number in international format
            template_name: Can be either:
                - Content SID (e.g., "HXb5b62575e6e4ff6129ad7c8efe1f983e")
                - Template name (will be sent as plain text fallback)
            language_code: Language code (not used by Twilio, Content SID determines language)
            parameters: Template parameters as [{"text": "value1"}, {"text": "value2"}]

        Returns:
            Twilio Message SID
        """
        # Check if template_name is a Content SID (starts with HX)
        if template_name.startswith("HX"):
            return await self._send_template_with_content_sid(
                to=to, content_sid=template_name, parameters=parameters
            )

        # Fallback: send as plain text
        logger.warning(
            f"Twilio template fallback: {template_name} ({language_code}). "
            "Use Content SID (HX...) for proper template support."
        )
        param_text = ""
        if parameters:
            param_values = [p.get("text", "") for p in parameters]
            param_text = " | ".join(param_values)

        body = f"[Template: {template_name}] {param_text}".strip()
        return await self._send_message(to=to, body=body)

    async def _send_template_with_content_sid(
        self,
        *,
        to: str,
        content_sid: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Send template using Twilio Content API with Content SID.

        Args:
            to: Phone number (will be prefixed with 'whatsapp:' if needed)
            content_sid: Twilio Content SID (e.g., "HXb5b62575e6e4ff6129ad7c8efe1f983e")
            parameters: Template parameters as [{"text": "value1"}, {"text": "value2"}]

        Returns:
            Twilio Message SID
        """
        # Ensure whatsapp: prefix on recipient
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"

        data = {
            "From": self.from_number,
            "To": to,
            "ContentSid": content_sid,
        }

        # Convert parameters to ContentVariables JSON format
        # Meta format: [{"text": "12/1"}, {"text": "3pm"}]
        # Twilio format: {"1": "12/1", "2": "3pm"}
        if parameters:
            import json

            content_variables = {}
            for i, param in enumerate(parameters, 1):
                content_variables[str(i)] = param.get("text", "")
            data["ContentVariables"] = json.dumps(content_variables)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data=data,
                    auth=(self.auth_username, self.auth_token),
                    timeout=30.0,
                )

                if response.status_code not in (200, 201):
                    error_data = response.json()
                    error_message = error_data.get("message", "Unknown error")
                    error_code = error_data.get("code", "unknown")
                    logger.error(
                        f"Twilio Content API error: {error_code} - {error_message}",
                        extra={"to": to, "content_sid": content_sid, "response": error_data},
                    )
                    raise WhatsAppError(f"Twilio Content API error ({error_code}): {error_message}")

                response_data = response.json()
                message_sid = response_data.get("sid", "unknown")
                logger.info(
                    f"Twilio template sent: {message_sid}",
                    extra={
                        "to": to,
                        "content_sid": content_sid,
                        "status": response_data.get("status"),
                    },
                )
                return message_sid

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending Twilio template: {e}")
            raise WhatsAppError(f"HTTP error: {e}") from e
        except WhatsAppError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending Twilio template: {e}")
            raise WhatsAppError(f"Unexpected error: {e}") from e

    async def mark_as_read(self, *, message_id: str) -> bool:
        """Twilio doesn't support marking messages as read via API."""
        logger.debug(f"mark_as_read not supported by Twilio (message_id={message_id})")
        return True

    async def download_media(self, *, media_id: str) -> bytes:
        """Download media from Twilio (direct URL download).

        For Twilio, media_id is actually the full media URL from the webhook.
        We download it with HTTP Basic Auth using Account SID and Auth Token.

        Args:
            media_id: Media URL from Twilio webhook (e.g., https://api.twilio.com/...)

        Returns:
            Media file bytes

        Raises:
            WhatsAppError: If download fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    media_id,
                    auth=(self.auth_username, self.auth_token),
                    timeout=60.0,
                )

                if response.status_code != 200:
                    logger.error(f"Failed to download Twilio media: HTTP {response.status_code}")
                    raise WhatsAppError(f"Failed to download media: HTTP {response.status_code}")

                logger.info(f"Downloaded Twilio media: {len(response.content)} bytes")
                return response.content

        except httpx.HTTPError as e:
            logger.error(f"HTTP error downloading Twilio media: {e}")
            raise WhatsAppError(f"HTTP error: {e}") from e
        except WhatsAppError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading Twilio media: {e}")
            raise WhatsAppError(f"Unexpected error: {e}") from e

    async def _send_message(self, *, to: str, body: str) -> str:
        """Send a message via Twilio REST API.

        Args:
            to: Phone number (will be prefixed with 'whatsapp:' if needed)
            body: Message body text

        Returns:
            Twilio Message SID

        Raises:
            WhatsAppError: If API request fails
        """
        # Ensure whatsapp: prefix on recipient
        if not to.startswith("whatsapp:"):
            to = f"whatsapp:{to}"

        data = {
            "From": self.from_number,
            "To": to,
            "Body": body,
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    data=data,
                    auth=(self.auth_username, self.auth_token),
                    timeout=30.0,
                )

                if response.status_code not in (200, 201):
                    error_data = response.json()
                    error_message = error_data.get("message", "Unknown error")
                    error_code = error_data.get("code", "unknown")
                    logger.error(
                        f"Twilio API error: {error_code} - {error_message}",
                        extra={"to": to, "response": error_data},
                    )
                    raise WhatsAppError(f"Twilio API error ({error_code}): {error_message}")

                response_data = response.json()
                message_sid = response_data.get("sid", "unknown")
                logger.info(
                    f"Twilio message sent: {message_sid}",
                    extra={"to": to, "status": response_data.get("status")},
                )
                return message_sid

        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending Twilio message: {e}")
            raise WhatsAppError(f"HTTP error: {e}") from e
        except WhatsAppError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending Twilio message: {e}")
            raise WhatsAppError(f"Unexpected error: {e}") from e
