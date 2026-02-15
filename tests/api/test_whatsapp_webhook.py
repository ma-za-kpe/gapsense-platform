"""
Tests for WhatsApp Webhook Endpoints

Tests webhook verification (GET) and message handling (POST).
Based on WhatsApp Cloud API v21.0 webhook specification.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import Parent
from gapsense.main import app


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Create test client with database dependency override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def test_parent(db_session: AsyncSession) -> Parent:
    """Create a test parent."""
    parent = Parent(
        phone="+233501234567",
        preferred_name="Auntie Ama",
        preferred_language="tw",
        opted_in=True,
        is_active=True,
    )
    db_session.add(parent)
    await db_session.commit()
    await db_session.refresh(parent)
    return parent


class TestWebhookVerification:
    """Test WhatsApp webhook verification (GET endpoint)."""

    async def test_webhook_verification_success(self, client: AsyncClient):
        """Test successful webhook verification with correct token."""
        response = await client.get(
            "/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "local_verify_token",  # Default from settings
                "hub.challenge": "test_challenge_string",
            },
        )

        assert response.status_code == 200
        assert response.text == "test_challenge_string"

    async def test_webhook_verification_wrong_token(self, client: AsyncClient):
        """Test webhook verification fails with wrong token."""
        response = await client.get(
            "/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong_token",
                "hub.challenge": "test_challenge_string",
            },
        )

        assert response.status_code == 403
        assert "Invalid verify token" in response.json()["detail"]

    async def test_webhook_verification_missing_mode(self, client: AsyncClient):
        """Test webhook verification fails with missing hub.mode."""
        response = await client.get(
            "/v1/webhooks/whatsapp",
            params={
                "hub.verify_token": "test_verify_token",
                "hub.challenge": "test_challenge_string",
            },
        )

        # FastAPI returns 422 for missing required params (Unprocessable Entity)
        assert response.status_code == 422

    async def test_webhook_verification_missing_challenge(self, client: AsyncClient):
        """Test webhook verification fails with missing hub.challenge."""
        response = await client.get(
            "/v1/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "test_verify_token",
            },
        )

        # FastAPI returns 422 for missing required params (Unprocessable Entity)
        assert response.status_code == 422


class TestWebhookMessageHandling:
    """Test WhatsApp webhook message handling (POST endpoint)."""

    async def test_receive_text_message(self, client: AsyncClient, test_parent: Parent):
        """Test receiving a text message from parent."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "PHONE_NUMBER_ID",
                                },
                                "contacts": [
                                    {"profile": {"name": "Auntie Ama"}, "wa_id": "233501234567"}
                                ],
                                "messages": [
                                    {
                                        "from": "233501234567",
                                        "id": "wamid.test123",
                                        "timestamp": "1234567890",
                                        "text": {"body": "Hello"},
                                        "type": "text",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    async def test_receive_button_response(self, client: AsyncClient, test_parent: Parent):
        """Test receiving a button response from parent."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "PHONE_NUMBER_ID",
                                },
                                "contacts": [
                                    {"profile": {"name": "Auntie Ama"}, "wa_id": "233501234567"}
                                ],
                                "messages": [
                                    {
                                        "from": "233501234567",
                                        "id": "wamid.test123",
                                        "timestamp": "1234567890",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {"id": "btn_yes", "title": "Yes"},
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    async def test_receive_list_response(self, client: AsyncClient, test_parent: Parent):
        """Test receiving a list selection from parent."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "PHONE_NUMBER_ID",
                                },
                                "contacts": [
                                    {"profile": {"name": "Auntie Ama"}, "wa_id": "233501234567"}
                                ],
                                "messages": [
                                    {
                                        "from": "233501234567",
                                        "id": "wamid.test123",
                                        "timestamp": "1234567890",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "list_reply",
                                            "list_reply": {"id": "lang_twi", "title": "Twi"},
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    async def test_receive_delivery_status(self, client: AsyncClient):
        """Test receiving message delivery status update."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "PHONE_NUMBER_ID",
                                },
                                "statuses": [
                                    {
                                        "id": "wamid.test123",
                                        "status": "delivered",
                                        "timestamp": "1234567890",
                                        "recipient_id": "233501234567",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    async def test_receive_read_receipt(self, client: AsyncClient):
        """Test receiving message read receipt."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "PHONE_NUMBER_ID",
                                },
                                "statuses": [
                                    {
                                        "id": "wamid.test123",
                                        "status": "read",
                                        "timestamp": "1234567890",
                                        "recipient_id": "233501234567",
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    async def test_receive_image_message(self, client: AsyncClient, test_parent: Parent):
        """Test receiving an image (exercise book photo) from parent."""
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "15551234567",
                                    "phone_number_id": "PHONE_NUMBER_ID",
                                },
                                "contacts": [
                                    {"profile": {"name": "Auntie Ama"}, "wa_id": "233501234567"}
                                ],
                                "messages": [
                                    {
                                        "from": "233501234567",
                                        "id": "wamid.test123",
                                        "timestamp": "1234567890",
                                        "type": "image",
                                        "image": {
                                            "id": "IMAGE_ID",
                                            "mime_type": "image/jpeg",
                                            "sha256": "IMAGE_HASH",
                                        },
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "received"}

    async def test_ignore_non_whatsapp_object(self, client: AsyncClient):
        """Test ignoring webhooks from non-WhatsApp objects."""
        payload = {"object": "instagram", "entry": []}

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}

    async def test_handle_malformed_payload(self, client: AsyncClient):
        """Test handling malformed webhook payload."""
        payload = {"invalid": "payload"}

        response = await client.post("/v1/webhooks/whatsapp", json=payload)

        # Should still return 200 to prevent Meta from retrying
        assert response.status_code == 200

    async def test_handle_empty_payload(self, client: AsyncClient):
        """Test handling empty webhook payload."""
        response = await client.post("/v1/webhooks/whatsapp", json={})

        # Should still return 200 to prevent Meta from retrying
        assert response.status_code == 200
