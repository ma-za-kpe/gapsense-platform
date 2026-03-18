"""
Abstract WhatsApp Provider Interface

Defines the contract that all WhatsApp providers must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class WhatsAppError(Exception):
    """WhatsApp API error."""


class WhatsAppProvider(ABC):
    """Abstract interface for WhatsApp message delivery.

    All providers (Meta, Twilio, etc.) must implement these methods.
    """

    @abstractmethod
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
            preview_url: Enable link preview

        Returns:
            Provider message ID
        """
        ...

    @abstractmethod
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
            Provider message ID
        """
        ...

    @abstractmethod
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
            button_text: Text for the list button
            sections: List sections with rows (max 10 total rows)
            header: Optional header text
            footer: Optional footer text

        Returns:
            Provider message ID
        """
        ...

    @abstractmethod
    async def send_template(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Send a message template.

        Args:
            to: Phone number in international format
            template_name: Template name
            language_code: Language code (e.g., "en", "tw")
            parameters: Optional template parameters

        Returns:
            Provider message ID
        """
        ...

    async def send_template_message(
        self,
        *,
        to: str,
        template_name: str,
        language_code: str,
        parameters: list[dict[str, str]] | None = None,
    ) -> str:
        """Alias for send_template() for backward compatibility."""
        return await self.send_template(
            to=to,
            template_name=template_name,
            language_code=language_code,
            parameters=parameters,
        )

    @abstractmethod
    async def mark_as_read(self, *, message_id: str) -> bool:
        """Mark a message as read.

        Args:
            message_id: Provider message ID

        Returns:
            True if successful
        """
        ...

    @abstractmethod
    async def download_media(self, *, media_id: str) -> bytes:
        """Download media file (image, audio, video, document).

        Args:
            media_id: Media ID from webhook message

        Returns:
            Media file content as bytes

        Raises:
            WhatsAppError: If download fails
        """
        ...
