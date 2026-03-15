"""
Tests for WhatsApp Webhook Adapter

Tests normalization of Meta and Twilio webhook formats into common structure.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from gapsense.engagement.whatsapp.webhook_adapter import (
    _detect_numbered_reply,
    _normalize_twilio_webhook,
    normalize_webhook,
)


class TestNormalizeWebhook:
    """Test main webhook normalization function."""

    @pytest.mark.asyncio
    async def test_normalize_meta_webhook_passthrough(self):
        """Test Meta webhooks pass through unchanged."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "application/json"

        meta_webhook = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "changes": [
                        {
                            "field": "messages",
                            "value": {
                                "messages": [
                                    {
                                        "from": "+233244123456",
                                        "id": "wamid.test123",
                                        "type": "text",
                                        "text": {"body": "Hello"},
                                    }
                                ]
                            },
                        }
                    ]
                }
            ],
        }

        mock_request.json = AsyncMock(return_value=meta_webhook)

        result = await normalize_webhook(mock_request)

        assert result == meta_webhook
        assert result["object"] == "whatsapp_business_account"

    @pytest.mark.asyncio
    async def test_normalize_twilio_webhook_converts_to_meta_format(self):
        """Test Twilio webhooks are normalized to Meta format."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "application/x-www-form-urlencoded"

        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "Hello from Twilio",
            "MessageSid": "SMtest123",
            "NumMedia": "0",
        }

        async def mock_form():
            return twilio_data

        mock_request.form = mock_form

        result = await normalize_webhook(mock_request)

        assert result is not None
        assert result["object"] == "whatsapp_business_account"
        assert len(result["entry"]) == 1
        assert result["entry"][0]["changes"][0]["field"] == "messages"

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert len(messages) == 1
        assert messages[0]["from"] == "+233244123456"
        assert messages[0]["type"] == "text"
        assert messages[0]["text"]["body"] == "Hello from Twilio"

    @pytest.mark.asyncio
    async def test_normalize_unrecognized_webhook_returns_none(self):
        """Test unrecognized webhooks return None."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "application/json"
        mock_request.json = AsyncMock(return_value={"unknown": "format"})

        result = await normalize_webhook(mock_request)

        assert result is None

    @pytest.mark.asyncio
    async def test_normalize_malformed_json_returns_none(self):
        """Test malformed JSON returns None gracefully."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = "application/json"
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))

        result = await normalize_webhook(mock_request)

        assert result is None


class TestNormalizeTwilioWebhook:
    """Test Twilio-specific normalization logic."""

    def test_normalize_text_message(self):
        """Test normalizing Twilio text message."""
        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "Test message",
            "MessageSid": "SMtest123",
            "NumMedia": "0",
        }

        result = _normalize_twilio_webhook(twilio_data)

        assert result["object"] == "whatsapp_business_account"
        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["type"] == "text"
        assert messages[0]["text"]["body"] == "Test message"
        assert messages[0]["from"] == "+233244123456"

    def test_normalize_image_message(self):
        """Test normalizing Twilio image message."""
        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "",
            "MessageSid": "SMtest123",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/image123",
            "MediaContentType0": "image/jpeg",
        }

        result = _normalize_twilio_webhook(twilio_data)

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["type"] == "image"
        assert messages[0]["image"]["mime_type"] == "image/jpeg"
        assert messages[0]["image"]["url"] == "https://api.twilio.com/media/image123"

    def test_normalize_voice_message(self):
        """Test normalizing Twilio voice message."""
        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "",
            "MessageSid": "SMtest123",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/audio123",
            "MediaContentType0": "audio/ogg",
        }

        result = _normalize_twilio_webhook(twilio_data)

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["type"] == "voice"
        assert messages[0]["voice"]["mime_type"] == "audio/ogg"
        assert messages[0]["voice"]["url"] == "https://api.twilio.com/media/audio123"

    def test_normalize_document_message(self):
        """Test normalizing Twilio document message."""
        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "",
            "MessageSid": "SMtest123",
            "NumMedia": "1",
            "MediaUrl0": "https://api.twilio.com/media/doc123",
            "MediaContentType0": "application/pdf",
        }

        result = _normalize_twilio_webhook(twilio_data)

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["type"] == "document"
        assert messages[0]["document"]["mime_type"] == "application/pdf"

    def test_normalize_numbered_reply(self):
        """Test numbered reply is detected and converted to interactive."""
        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "1",
            "MessageSid": "SMtest123",
            "NumMedia": "0",
        }

        result = _normalize_twilio_webhook(twilio_data)

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["type"] == "interactive"
        assert messages[0]["interactive"]["type"] == "button_reply"
        assert messages[0]["interactive"]["button_reply"]["title"] == "1"

    def test_normalize_phone_without_whatsapp_prefix(self):
        """Test phone normalization adds + prefix if missing."""
        twilio_data = {
            "From": "233244123456",  # Missing whatsapp: and +
            "Body": "Test",
            "MessageSid": "SMtest123",
            "NumMedia": "0",
        }

        result = _normalize_twilio_webhook(twilio_data)

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["from"] == "+233244123456"

    def test_normalize_phone_strips_whatsapp_prefix(self):
        """Test phone normalization strips whatsapp: prefix."""
        twilio_data = {
            "From": "whatsapp:+233244123456",
            "Body": "Test",
            "MessageSid": "SMtest123",
            "NumMedia": "0",
        }

        result = _normalize_twilio_webhook(twilio_data)

        messages = result["entry"][0]["changes"][0]["value"]["messages"]
        assert messages[0]["from"] == "+233244123456"
        assert "whatsapp:" not in messages[0]["from"]


class TestDetectNumberedReply:
    """Test numbered reply detection for button/list fallbacks."""

    def test_detect_single_digit_numbers(self):
        """Test detects numbers 1-9."""
        for i in range(1, 10):
            result = _detect_numbered_reply(str(i))
            assert result is not None
            assert result["title"] == str(i)
            assert result["id"] == f"numbered_reply_{i}"

    def test_detect_number_10(self):
        """Test detects number 10."""
        result = _detect_numbered_reply("10")
        assert result is not None
        assert result["title"] == "10"
        assert result["id"] == "numbered_reply_10"

    def test_does_not_detect_number_0(self):
        """Test does not detect 0 as numbered reply."""
        result = _detect_numbered_reply("0")
        assert result is None

    def test_does_not_detect_numbers_above_10(self):
        """Test does not detect numbers > 10."""
        result = _detect_numbered_reply("11")
        assert result is None

        result = _detect_numbered_reply("99")
        assert result is None

    def test_does_not_detect_text(self):
        """Test does not detect regular text as numbered reply."""
        result = _detect_numbered_reply("Hello")
        assert result is None

        result = _detect_numbered_reply("Yes")
        assert result is None

    def test_handles_whitespace(self):
        """Test strips whitespace before detection."""
        result = _detect_numbered_reply("  5  ")
        assert result is not None
        assert result["title"] == "5"

    def test_does_not_detect_numbers_with_text(self):
        """Test does not detect numbers mixed with text."""
        result = _detect_numbered_reply("1st option")
        assert result is None

        result = _detect_numbered_reply("Option 1")
        assert result is None

    def test_does_not_detect_negative_numbers(self):
        """Test does not detect negative numbers."""
        result = _detect_numbered_reply("-1")
        assert result is None
