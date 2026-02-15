"""
Tests for WhatsApp Cloud API Client

Tests message sending functionality (text, buttons, lists, templates).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gapsense.engagement.whatsapp_client import WhatsAppClient, WhatsAppError


class TestWhatsAppClientInitialization:
    """Test WhatsAppClient initialization."""

    def test_client_initialization_with_credentials(self):
        """Test client initializes with API credentials."""
        client = WhatsAppClient(
            api_token="test_token",
            phone_number_id="test_phone_id",
        )

        assert client.api_token == "test_token"
        assert client.phone_number_id == "test_phone_id"
        assert client.base_url == "https://graph.facebook.com/v21.0"

    def test_client_initialization_from_settings(self):
        """Test client initializes from settings."""
        with patch("gapsense.engagement.whatsapp_client.settings") as mock_settings:
            mock_settings.WHATSAPP_API_TOKEN = "settings_token"
            mock_settings.WHATSAPP_PHONE_NUMBER_ID = "settings_phone_id"

            client = WhatsAppClient.from_settings()

            assert client.api_token == "settings_token"
            assert client.phone_number_id == "settings_phone_id"


class TestSendTextMessage:
    """Test sending text messages."""

    @pytest.mark.asyncio
    async def test_send_text_message_success(self):
        """Test sending a simple text message."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "messaging_product": "whatsapp",
                "contacts": [{"input": "233501234567", "wa_id": "233501234567"}],
                "messages": [{"id": "wamid.test123"}],
            }
            mock_post.return_value = mock_response

            message_id = await client.send_text_message(
                to="+233501234567",
                text="Hello from GapSense!",
            )

            assert message_id == "wamid.test123"
            mock_post.assert_called_once()

            # Verify request payload
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["messaging_product"] == "whatsapp"
            assert call_kwargs["json"]["to"] == "+233501234567"
            assert call_kwargs["json"]["type"] == "text"
            assert call_kwargs["json"]["text"]["body"] == "Hello from GapSense!"

    @pytest.mark.asyncio
    async def test_send_text_message_with_preview(self):
        """Test sending text message with link preview enabled."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            await client.send_text_message(
                to="+233501234567",
                text="Check this out: https://gapsense.app",
                preview_url=True,
            )

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["text"]["preview_url"] is True

    @pytest.mark.asyncio
    async def test_send_text_message_api_error(self):
        """Test handling API error when sending text."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {
                "error": {
                    "message": "Invalid phone number",
                    "code": 100,
                }
            }
            mock_post.return_value = mock_response

            with pytest.raises(WhatsAppError) as exc_info:
                await client.send_text_message(
                    to="invalid_number",
                    text="Test",
                )

            assert "Invalid phone number" in str(exc_info.value)


class TestSendButtonMessage:
    """Test sending interactive button messages."""

    @pytest.mark.asyncio
    async def test_send_button_message_success(self):
        """Test sending button message with up to 3 buttons."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            buttons = [
                {"id": "btn_yes", "title": "Yes"},
                {"id": "btn_no", "title": "No"},
            ]

            message_id = await client.send_button_message(
                to="+233501234567",
                body="Would you like to continue?",
                buttons=buttons,
            )

            assert message_id == "wamid.test123"

            # Verify payload structure
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
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        buttons = [
            {"id": f"btn_{i}", "title": f"Button {i}"}
            for i in range(4)  # 4 buttons (max is 3)
        ]

        with pytest.raises(ValueError, match="Maximum 3 buttons allowed"):
            await client.send_button_message(
                to="+233501234567",
                body="Choose an option",
                buttons=buttons,
            )


class TestSendListMessage:
    """Test sending interactive list messages."""

    @pytest.mark.asyncio
    async def test_send_list_message_success(self):
        """Test sending list message with sections."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

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

            message_id = await client.send_list_message(
                to="+233501234567",
                body="Please select your preferred language",
                button_text="Choose Language",
                sections=sections,
            )

            assert message_id == "wamid.test123"

            # Verify payload structure
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["type"] == "interactive"
            assert call_kwargs["json"]["interactive"]["type"] == "list"
            assert call_kwargs["json"]["interactive"]["action"]["button"] == "Choose Language"
            assert len(call_kwargs["json"]["interactive"]["action"]["sections"]) == 1

    @pytest.mark.asyncio
    async def test_send_list_message_too_many_items(self):
        """Test error when sending more than 10 list items."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        sections = [
            {
                "title": "Options",
                "rows": [
                    {"id": f"opt_{i}", "title": f"Option {i}"}
                    for i in range(11)  # 11 items (max is 10)
                ],
            }
        ]

        with pytest.raises(ValueError, match="Maximum 10 list items allowed"):
            await client.send_list_message(
                to="+233501234567",
                body="Choose an option",
                button_text="Select",
                sections=sections,
            )


class TestSendTemplate:
    """Test sending WhatsApp message templates."""

    @pytest.mark.asyncio
    async def test_send_template_success(self):
        """Test sending a message template."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            message_id = await client.send_template(
                to="+233501234567",
                template_name="activity_followup",
                language_code="en",
                parameters=[
                    {"type": "text", "text": "Auntie Ama"},
                    {"type": "text", "text": "counting practice"},
                ],
            )

            assert message_id == "wamid.test123"

            # Verify payload structure
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["type"] == "template"
            assert call_kwargs["json"]["template"]["name"] == "activity_followup"
            assert call_kwargs["json"]["template"]["language"]["code"] == "en"

    @pytest.mark.asyncio
    async def test_send_template_no_parameters(self):
        """Test sending template without parameters."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": [{"id": "wamid.test123"}]}
            mock_post.return_value = mock_response

            await client.send_template(
                to="+233501234567",
                template_name="simple_greeting",
                language_code="tw",
            )

            call_kwargs = mock_post.call_args.kwargs
            # Should not include components if no parameters
            assert "components" not in call_kwargs["json"]["template"]


class TestMarkAsRead:
    """Test marking messages as read."""

    @pytest.mark.asyncio
    async def test_mark_message_as_read(self):
        """Test marking a message as read."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response

            success = await client.mark_as_read(message_id="wamid.test123")

            assert success is True

            # Verify payload
            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["messaging_product"] == "whatsapp"
            assert call_kwargs["json"]["status"] == "read"
            assert call_kwargs["json"]["message_id"] == "wamid.test123"


class TestErrorHandling:
    """Test error handling and retries."""

    @pytest.mark.asyncio
    async def test_handle_rate_limit_error(self):
        """Test handling rate limit errors (429)."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.json.return_value = {
                "error": {
                    "message": "Rate limit exceeded",
                    "code": 80007,
                }
            }
            mock_post.return_value = mock_response

            with pytest.raises(WhatsAppError, match="Rate limit exceeded"):
                await client.send_text_message(
                    to="+233501234567",
                    text="Test",
                )

    @pytest.mark.asyncio
    async def test_handle_network_error(self):
        """Test handling network errors."""
        client = WhatsAppClient(api_token="test_token", phone_number_id="test_phone_id")

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Connection timeout")

            with pytest.raises(WhatsAppError, match="Connection timeout"):
                await client.send_text_message(
                    to="+233501234567",
                    text="Test",
                )
