"""
Integration Tests for WhatsApp Webhook + FlowExecutor

Tests complete flow from webhook to FlowExecutor to WhatsAppClient.
"""

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.database import get_db
from gapsense.core.models import Parent
from gapsense.main import app


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database dependency override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestWebhookFlowIntegration:
    """Test webhook integration with FlowExecutor."""

    @pytest.mark.asyncio
    async def test_new_parent_onboarding_flow(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test complete onboarding flow for new parent."""
        # Setup webhook payload
        webhook_payload = {
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
                                "messages": [
                                    {
                                        "from": "+233501234567",
                                        "id": "wamid.test123",
                                        "timestamp": "1234567890",
                                        "type": "text",
                                        "text": {"body": "Hi"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        # Mock WhatsAppClient
        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.response123"

            # Send webhook request
            response = await client.post(
                "/v1/webhooks/whatsapp",
                json=webhook_payload,
            )

            assert response.status_code == 200
            assert response.json() == {"status": "received"}

            # Verify parent was created
            stmt = select(Parent).where(Parent.phone == "+233501234567")
            result = await db_session.execute(stmt)
            parent = result.scalar_one()

            assert parent is not None
            assert parent.conversation_state is not None
            assert parent.conversation_state["flow"] == "FLOW-ONBOARD"
            assert parent.conversation_state["step"] == "AWAITING_NAME"

            # Verify welcome message was sent
            mock_client.send_text_message.assert_called_once()
            call_kwargs = mock_client.send_text_message.call_args.kwargs
            assert call_kwargs["to"] == "+233501234567"
            assert "Welcome to GapSense" in call_kwargs["text"]

    @pytest.mark.asyncio
    async def test_parent_name_collection(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test collecting parent's name during onboarding."""
        # Create parent in AWAITING_NAME state
        parent = Parent(
            phone="+233501234567",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_NAME",
                "data": {},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        # Setup webhook payload with name
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+233501234567",
                                        "id": "wamid.test456",
                                        "type": "text",
                                        "text": {"body": "Auntie Ama"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        # Mock WhatsAppClient
        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_list_message.return_value = "wamid.response456"

            # Send webhook request
            response = await client.post(
                "/v1/webhooks/whatsapp",
                json=webhook_payload,
            )

            assert response.status_code == 200

            # Verify name was saved
            await db_session.refresh(parent)
            assert parent.preferred_name == "Auntie Ama"
            assert parent.conversation_state is not None
            assert parent.conversation_state["data"]["name"] == "Auntie Ama"
            assert parent.conversation_state["step"] == "AWAITING_LANGUAGE"

            # Verify language selection list was sent
            mock_client.send_list_message.assert_called_once()
            call_kwargs = mock_client.send_list_message.call_args.kwargs
            assert "Auntie Ama" in call_kwargs["header"]
            assert "language" in call_kwargs["body"].lower()

    @pytest.mark.asyncio
    async def test_parent_opt_out_flow(self, client: AsyncClient, db_session: AsyncSession) -> None:
        """Test parent opt-out flow."""
        # Create parent
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            opted_in=True,
            opted_out=False,
        )
        db_session.add(parent)
        await db_session.commit()

        # Setup webhook payload with opt-out keyword
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+233501234567",
                                        "id": "wamid.test789",
                                        "type": "text",
                                        "text": {"body": "stop"},
                                    }
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        # Mock WhatsAppClient
        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.response789"

            # Send webhook request
            response = await client.post(
                "/v1/webhooks/whatsapp",
                json=webhook_payload,
            )

            assert response.status_code == 200

            # Verify parent opted out
            await db_session.refresh(parent)
            assert parent.opted_out is True
            assert parent.opted_out_at is not None
            assert parent.conversation_state is None

            # Verify opt-out confirmation was sent
            mock_client.send_text_message.assert_called_once()
            call_kwargs = mock_client.send_text_message.call_args.kwargs
            assert "stopped all messages" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_interactive_button_message(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test handling interactive button message."""
        # Create parent
        parent = Parent(
            phone="+233501234567",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CONFIRMATION",
                "data": {},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        # Setup webhook payload with button reply
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+233501234567",
                                        "id": "wamid.test321",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {
                                                "id": "confirm_yes",
                                                "title": "Yes",
                                            },
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

        # Mock WhatsAppClient
        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client

            # Send webhook request
            response = await client.post(
                "/v1/webhooks/whatsapp",
                json=webhook_payload,
            )

            assert response.status_code == 200

            # Verify parent still exists
            await db_session.refresh(parent)
            assert parent is not None

    @pytest.mark.asyncio
    async def test_webhook_handles_multiple_messages(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test webhook handling multiple messages in batch."""
        # Setup webhook payload with multiple messages
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+233501111111",
                                        "id": "wamid.msg1",
                                        "type": "text",
                                        "text": {"body": "Hi"},
                                    },
                                    {
                                        "from": "+233502222222",
                                        "id": "wamid.msg2",
                                        "type": "text",
                                        "text": {"body": "Hello"},
                                    },
                                ],
                            },
                            "field": "messages",
                        }
                    ],
                }
            ],
        }

        # Mock WhatsAppClient
        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.response"

            # Send webhook request
            response = await client.post(
                "/v1/webhooks/whatsapp",
                json=webhook_payload,
            )

            assert response.status_code == 200

            # Verify both parents were created
            stmt1 = select(Parent).where(Parent.phone == "+233501111111")
            result1 = await db_session.execute(stmt1)
            parent1 = result1.scalar_one()
            assert parent1 is not None

            stmt2 = select(Parent).where(Parent.phone == "+233502222222")
            result2 = await db_session.execute(stmt2)
            parent2 = result2.scalar_one()
            assert parent2 is not None

            # Verify messages were sent to both
            assert mock_client.send_text_message.call_count == 2

    @pytest.mark.asyncio
    async def test_diagnostic_consent_persistence(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Test that diagnostic consent is persisted to database after complete onboarding."""
        # Create parent in AWAITING_CONSENT state
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            preferred_language="en",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CONSENT",
                "data": {"name": "Auntie Ama", "language": "en"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        # Setup webhook payload with consent given
        webhook_payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [
                        {
                            "value": {
                                "messages": [
                                    {
                                        "from": "+233501234567",
                                        "id": "wamid.consent123",
                                        "type": "interactive",
                                        "interactive": {
                                            "type": "button_reply",
                                            "button_reply": {
                                                "id": "consent_yes",
                                                "title": "Yes, I consent",
                                            },
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

        # Mock WhatsAppClient
        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.response_consent"

            # Send webhook request
            response = await client.post(
                "/v1/webhooks/whatsapp",
                json=webhook_payload,
            )

            assert response.status_code == 200

            # CRITICAL: Verify diagnostic consent was persisted to database
            await db_session.refresh(parent)
            assert parent.diagnostic_consent is True
            assert parent.diagnostic_consent_at is not None
            assert parent.onboarded_at is not None
            assert parent.opted_in is True
            assert parent.opted_in_at is not None
            assert parent.conversation_state is None  # Flow completed
