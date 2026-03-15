"""
Mock WhatsApp Client for Demo UI

Captures messages that would be sent via WhatsApp so they can be displayed in the demo UI.
"""

from __future__ import annotations

from typing import Any


class MockWhatsAppClient:
    """Mock WhatsApp client that captures messages instead of sending them."""

    def __init__(self):
        self.messages: list[dict[str, Any]] = []
        self.last_message: str | None = None

    async def send_text_message(self, to: str, text: str, preview_url: bool = True) -> str:
        """Capture text message instead of sending it."""
        message_id = f"mock_{len(self.messages)}"
        self.messages.append(
            {
                "id": message_id,
                "to": to,
                "text": text,
                "type": "text",
            }
        )
        self.last_message = text
        return message_id

    async def send_button_message(
        self,
        *,
        to: str,
        body: str,
        buttons: list[dict[str, str]],
        header: str | None = None,
        footer: str | None = None,
    ) -> str:
        """Capture button message instead of sending it."""
        message_id = f"mock_{len(self.messages)}"
        self.messages.append(
            {
                "id": message_id,
                "to": to,
                "body": body,
                "buttons": buttons,
                "header": header,
                "footer": footer,
                "type": "buttons",
            }
        )
        # Format for display
        message_text = ""
        if header:
            message_text += f"**{header}**\n\n"
        message_text += body
        if footer:
            message_text += f"\n\n_{footer}_"
        if buttons:
            message_text += "\n\n" + "\n".join(
                [f"• {btn.get('title', 'Button')}" for btn in buttons]
            )
        self.last_message = message_text
        return message_id

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
        """Capture list message instead of sending it."""
        message_id = f"mock_{len(self.messages)}"
        self.messages.append(
            {
                "id": message_id,
                "to": to,
                "body": body,
                "button_text": button_text,
                "sections": sections,
                "header": header,
                "footer": footer,
                "type": "list",
            }
        )
        # Format for display
        message_text = ""
        if header:
            message_text += f"**{header}**\n\n"
        message_text += body
        if sections:
            message_text += "\n\n"
            for section in sections:
                if "title" in section:
                    message_text += f"**{section['title']}**\n"
                for row in section.get("rows", []):
                    message_text += f"• {row.get('title', 'Item')}\n"
        if footer:
            message_text += f"\n_{footer}_"
        self.last_message = message_text
        return message_id

    async def send_template(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Capture template message instead of sending it."""
        message_id = f"mock_{len(self.messages)}"
        self.messages.append(
            {
                "id": message_id,
                "to": to,
                "template_name": template_name,
                "language_code": language_code,
                "parameters": parameters or [],
                "type": "template",
            }
        )
        # For demo, convert template to text representation
        self.last_message = f"[Template: {template_name}]"
        return message_id

    async def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str = "en",
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Alias for send_template() for backward compatibility."""
        return await self.send_template(
            to=to,
            template_name=template_name,
            language_code=language_code,
            parameters=parameters,
        )

    async def send_interactive_message(
        self,
        to: str,
        body_text: str,
        buttons: list[dict[str, str]] | None = None,
    ) -> str:
        """Capture interactive message instead of sending it."""
        message_id = f"mock_{len(self.messages)}"
        self.messages.append(
            {
                "id": message_id,
                "to": to,
                "body_text": body_text,
                "buttons": buttons or [],
                "type": "interactive",
            }
        )
        self.last_message = body_text
        if buttons:
            self.last_message += "\n\n" + "\n".join(
                [f"• {btn.get('title', 'Button')}" for btn in buttons]
            )
        return message_id

    async def download_media(self, media_id: str) -> bytes:
        """Mock media download - returns empty bytes for demo."""
        return b""

    def get_last_message(self) -> str | None:
        """Get the last message text that was captured."""
        return self.last_message

    def clear(self):
        """Clear all captured messages."""
        self.messages = []
        self.last_message = None
