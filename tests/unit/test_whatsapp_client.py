"""
Tests for WhatsApp Provider Abstraction

Tests Meta provider, Twilio provider, factory, and backward compatibility.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gapsense.engagement.whatsapp.base import WhatsAppError
from gapsense.engagement.whatsapp.meta_provider import MetaWhatsAppProvider
from gapsense.engagement.whatsapp.twilio_provider import TwilioWhatsAppProvider


class TestMetaProviderInitialization:
    """Test MetaWhatsAppProvider initialization."""

    def test_provider_initialization_with_credentials(self):
        """Test provider initializes with API credentials."""
        provider = MetaWhatsAppProvider(
            api_token="test_token",
            phone_number_id="test_phone_id",
        )

        assert provider.api_token == "test_token"
        assert provider.phone_number_id == "test_phone_id"
        assert provider.base_url == "https://graph.facebook.com/v21.0"


class TestMetaSendTextMessage:
    """Test Meta provider sending text messages."""

    @pytest.mark.asyncio
    async def test_send_text_message_success(self):
        """Test sending a simple text message."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "233501234567", "wa_id": "233501234567"}],
                "messages": [{"id": "wamid.test123"}],
            }
            mock_post.return_value = mock_response

            message_id = await provider.send_text_message(
                to="+233501234567",
                text="Hello from GapSense!",
            )

            assert message_id == "wamid.test123"
            mock_post.assert_called_once()

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["messaging_product"] == "whatsapp"
            assert call_kwargs["json"]["to"] == "+233501234567"
            assert call_kwargs["json"]["type"] == "text"
            assert call_kwargs["json"]["text"]["body"] == "Hello from GapSense!"

    @pytest.mark.asyncio
    async def test_send_text_message_with_preview(self):
        """Test sending text message with link preview enabled."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            await provider.send_text_message(
                to="+233501234567",
                text="Check this out: https://gapsense.app",
                preview_url=True,
            )

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["text"]["preview_url"] is True

    @pytest.mark.asyncio
    async def test_send_text_message_api_error(self):
        """Test handling API error when sending text."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": {"message": "Invalid phone number", "code": 100}
            }
            mock_post.return_value = mock_response

            with pytest.raises(WhatsAppError) as exc_info:
                await provider.send_text_message(to="invalid_number", text="Test")

            assert "Invalid phone number" in str(exc_info.value)


class TestMetaSendButtonMessage:
    """Test Meta provider sending interactive button messages."""

    @pytest.mark.asyncio
    async def test_send_button_message_success(self):
        """Test sending button message with up to 3 buttons."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            buttons = [
                {"id": "btn_yes", "title": "Yes"},
                {"id": "btn_no", "title": "No"},
            ]

            message_id = await provider.send_button_message(
                to="+233501234567",
                body="Would you like to continue?",
                buttons=buttons,
            )

            assert message_id == "wamid.test123"

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["type"] == "interactive"
            assert call_kwargs["json"]["interactive"]["type"] == "button"
            assert (
                call_kwargs["json"]["interactive"]["body"]["text"] == "Would you like to continue?"
            )
            assert len(call_kwargs["json"]["interactive"]["action"]["buttons"]) == 2

    @pytest.mark.asyncio
    async def test_send_button_message_too_many_buttons(self):
        """Test error when sending more than 3 buttons."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        buttons = [{"id": f"btn_{i}", "title": f"Button {i}"} for i in range(4)]

        with pytest.raises(ValueError, match="Maximum 3 buttons allowed"):
            await provider.send_button_message(
                to="+233501234567", body="Choose an option", buttons=buttons
            )


class TestMetaSendListMessage:
    """Test Meta provider sending interactive list messages."""

    @pytest.mark.asyncio
    async def test_send_list_message_success(self):
        """Test sending list message with sections."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            sections = [
                {
                    "title": "Languages",
                    "rows": [
                        {"id": "lang_twi", "title": "Twi", "description": "Akan/Twi language"},
                        {"id": "lang_eng", "title": "English", "description": "English language"},
                    ],
                }
            ]

            message_id = await provider.send_list_message(
                to="+233501234567",
                body="Please select your preferred language",
                button_text="Choose Language",
                sections=sections,
            )

            assert message_id == "wamid.test123"

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["type"] == "interactive"
            assert call_kwargs["json"]["interactive"]["type"] == "list"
            assert call_kwargs["json"]["interactive"]["action"]["button"] == "Choose Language"

    @pytest.mark.asyncio
    async def test_send_list_message_too_many_items(self):
        """Test error when sending more than 10 list items."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        sections = [
            {
                "title": "Options",
                "rows": [{"id": f"opt_{i}", "title": f"Option {i}"} for i in range(11)],
            }
        ]

        with pytest.raises(ValueError, match="Maximum 10 list items allowed"):
            await provider.send_list_message(
                to="+233501234567", body="Choose", button_text="Select", sections=sections
            )


class TestMetaSendTemplate:
    """Test Meta provider sending WhatsApp message templates."""

    @pytest.mark.asyncio
    async def test_send_template_success(self):
        """Test sending a message template."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            message_id = await provider.send_template(
                to="+233501234567",
                template_name="activity_followup",
                language_code="en",
                parameters=[
                    {"type": "text", "text": "Auntie Ama"},
                    {"type": "text", "text": "counting practice"},
                ],
            )

            assert message_id == "wamid.test123"

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["type"] == "template"
            assert call_kwargs["json"]["template"]["name"] == "activity_followup"
            assert call_kwargs["json"]["template"]["language"]["code"] == "en"

    @pytest.mark.asyncio
    async def test_send_template_no_parameters(self):
        """Test sending template without parameters."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            await provider.send_template(
                to="+233501234567", template_name="simple_greeting", language_code="tw"
            )

            call_kwargs = mock_post.call_args.kwargs
            assert "components" not in call_kwargs["json"]["template"]


class TestMetaMarkAsRead:
    """Test Meta provider marking messages as read."""

    @pytest.mark.asyncio
    async def test_mark_message_as_read(self):
        """Test marking a message as read."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            success = await provider.mark_as_read(message_id="wamid.test123")

            assert success is True

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["messaging_product"] == "whatsapp"
            assert call_kwargs["json"]["status"] == "read"
            assert call_kwargs["json"]["message_id"] == "wamid.test123"


class TestMetaErrorHandling:
    """Test Meta provider error handling."""

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self):
        """Test handling rate limit errors (429)."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.json.return_value = {
                "error": {"message": "Rate limit exceeded", "code": 80007}
            }
            mock_post.return_value = mock_response

            with pytest.raises(WhatsAppError, match="Rate limit exceeded"):
                await provider.send_text_message(to="+233501234567", text="Test")

    @pytest.mark.asyncio
    async def test_handle_network_error(self):
        """Test handling network errors."""
        provider = MetaWhatsAppProvider(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            with pytest.raises(WhatsAppError, match="Connection timeout"):
                await provider.send_text_message(to="+233501234567", text="Test")


class TestTwilioProvider:
    """Test TwilioWhatsAppProvider."""

    @pytest.mark.asyncio
    async def test_send_text_message(self):
        """Test Twilio sends text via REST API."""
        provider = TwilioWhatsAppProvider(
            account_sid="ACtest", auth_token="test_token", from_number="whatsapp:+14155238886"
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"sid": "SMtest123", "status": "queued"}
            mock_post.return_value = mock_response

            message_id = await provider.send_text_message(to="+233501234567", text="Hello!")

            assert message_id == "SMtest123"
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["data"]["To"] == "whatsapp:+233501234567"
            assert call_kwargs["data"]["From"] == "whatsapp:+14155238886"
            assert call_kwargs["data"]["Body"] == "Hello!"

    @pytest.mark.asyncio
    async def test_send_button_message_as_numbered_list(self):
        """Test Twilio falls back to numbered list for buttons."""
        provider = TwilioWhatsAppProvider(
            account_sid="ACtest", auth_token="test_token", from_number="whatsapp:+14155238886"
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"sid": "SMtest123", "status": "queued"}
            mock_post.return_value = mock_response

            await provider.send_button_message(
                to="+233501234567",
                body="Choose an option:",
                buttons=[
                    {"id": "yes", "title": "Yes"},
                    {"id": "no", "title": "No"},
                ],
            )

            call_kwargs = mock_post.call_args.kwargs
            body = call_kwargs["data"]["Body"]
            assert "1. Yes" in body
            assert "2. No" in body
            assert "Reply with a number (1-2)" in body

    @pytest.mark.asyncio
    async def test_mark_as_read_noop(self):
        """Test Twilio mark_as_read is a no-op."""
        provider = TwilioWhatsAppProvider(
            account_sid="ACtest", auth_token="test_token", from_number="whatsapp:+14155238886"
        )
        result = await provider.mark_as_read(message_id="SMtest123")
        assert result is True


class TestProviderFactory:
    """Test WhatsAppProviderFactory."""

    def test_create_meta_provider(self):
        """Test factory creates Meta provider."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"

            from gapsense.engagement.whatsapp.factory import (
                WhatsAppProviderFactory,
                reset_whatsapp_client,
            )

            reset_whatsapp_client()
            provider = WhatsAppProviderFactory.create()
            assert isinstance(provider, MetaWhatsAppProvider)

    def test_create_twilio_provider(self):
        """Test factory creates Twilio provider."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "twilio"
            mock_settings.TWILIO_ACCOUNT_SID = "ACtest"
            mock_settings.TWILIO_AUTH_TOKEN = "test_token"
            mock_settings.TWILIO_WHATSAPP_NUMBER = "whatsapp:+14155238886"

            from gapsense.engagement.whatsapp.factory import (
                WhatsAppProviderFactory,
                reset_whatsapp_client,
            )

            reset_whatsapp_client()
            provider = WhatsAppProviderFactory.create()
            assert isinstance(provider, TwilioWhatsAppProvider)

    def test_unknown_provider_raises(self):
        """Test factory raises for unknown provider."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "unknown"

            from gapsense.engagement.whatsapp.factory import (
                WhatsAppProviderFactory,
                reset_whatsapp_client,
            )

            reset_whatsapp_client()
            with pytest.raises(ValueError, match="Unknown WhatsApp provider"):
                WhatsAppProviderFactory.create()


class TestBackwardCompatibility:
    """Test that the old WhatsAppClient shim still works."""

    def test_from_settings_returns_provider(self):
        """Test WhatsAppClient.from_settings() returns a provider instance."""
        with patch("gapsense.engagement.whatsapp.factory.settings") as mock_settings:
            mock_settings.WHATSAPP_PROVIDER = "meta"
            mock_settings.WHATSAPP_API_TOKEN = "test_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "test_phone_id"

            from gapsense.engagement.whatsapp.factory import reset_whatsapp_client

            reset_whatsapp_client()

            from gapsense.engagement.whatsapp_client import WhatsAppClient

            client = WhatsAppClient.from_settings()
            assert isinstance(client, MetaWhatsAppProvider)
