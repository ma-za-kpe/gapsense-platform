"""
Tests for WhatsApp Flow Executor

Tests conversation flow orchestration and state management.
"""

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from gapsense.core.models import Parent
from gapsense.engagement.flow_executor import FlowExecutor, FlowResult


class TestFlowExecutorInitialization:
    """Test FlowExecutor initialization."""

    @pytest.mark.asyncio
    async def test_executor_initialization(self, db_session: AsyncSession):
        """Test executor initializes with database session."""
        executor = FlowExecutor(db=db_session)

        assert executor.db == db_session


class TestOptOutFlow:
    """Test opt-out flow (FLOW-OPT-OUT)."""

    @pytest.mark.asyncio
    async def test_opt_out_from_text_stop(self, db_session: AsyncSession):
        """Test parent opts out by sending 'stop'."""
        # Create parent
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            preferred_language="en",
            opted_in=True,
            opted_out=False,
        )
        db_session.add(parent)
        await db_session.commit()
        await db_session.refresh(parent)

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test123"

            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="stop",
                message_id="wamid.incoming123",
            )

            assert result.flow_name == "FLOW-OPT-OUT"
            assert result.completed is True
            assert result.next_step is None

            # Verify parent opted out
            await db_session.refresh(parent)
            assert parent.opted_out is True
            assert parent.opted_out_at is not None
            assert parent.conversation_state is None  # Cleared after completion

            # Verify confirmation message sent
            mock_client.send_text_message.assert_called_once()
            call_kwargs = mock_client.send_text_message.call_args.kwargs
            assert "stopped all messages" in call_kwargs["text"].lower()

    @pytest.mark.asyncio
    async def test_opt_out_variations(self, db_session: AsyncSession):
        """Test opt-out triggers on various keywords including L1 languages."""
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            opted_out=False,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        # Test English, Twi, Ewe, Ga, Dagbani (L1-first compliance)
        opt_out_keywords = [
            "stop",
            "STOP",
            "unsubscribe",
            "cancel",
            "quit",
            "Stop",  # English
            "gyae",
            "GYAE",
            "Gyina",  # Twi
            "tɔtɔ",
            "TƆE",  # Ewe
            "tsia",
            "TSIA",  # Ga
            "nyɛli",
            "NYƐLI",  # Dagbani
        ]

        for keyword in opt_out_keywords:
            # Reset parent state
            await db_session.refresh(parent)
            parent.opted_out = False
            parent.opted_out_at = None
            await db_session.commit()

            with patch("gapsense.engagement.flow_executor.WhatsAppClient"):
                result = await executor.process_message(
                    parent=parent,
                    message_type="text",
                    message_content=keyword,
                    message_id=f"wamid.{keyword}",
                )

                assert result.flow_name == "FLOW-OPT-OUT"
                await db_session.refresh(parent)
                assert parent.opted_out is True, f"Failed for keyword: {keyword}"


class TestOnboardingFlow:
    """Test onboarding flow (FLOW-ONBOARD)."""

    @pytest.mark.asyncio
    async def test_start_onboarding_new_parent(self, db_session: AsyncSession):
        """Test starting onboarding for new parent."""
        parent = Parent(
            phone="+233501234567",
            preferred_name=None,  # Not yet onboarded
            opted_in=False,
            opted_out=False,
        )
        db_session.add(parent)
        await db_session.commit()
        await db_session.refresh(parent)

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test123"

            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="Hi",
                message_id="wamid.incoming123",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is False
            assert result.next_step == "AWAITING_NAME"

            # Verify conversation state updated
            await db_session.refresh(parent)
            assert parent.conversation_state is not None
            assert parent.conversation_state["flow"] == "FLOW-ONBOARD"
            assert parent.conversation_state["step"] == "AWAITING_NAME"

            # Verify welcome message sent
            mock_client.send_text_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_onboarding_collect_name(self, db_session: AsyncSession):
        """Test collecting parent's name during onboarding."""
        parent = Parent(
            phone="+233501234567",
            opted_in=False,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_NAME",
                "data": {},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test123"

            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="Auntie Ama",
                message_id="wamid.incoming123",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is False

            # Verify name saved
            await db_session.refresh(parent)
            assert parent.preferred_name == "Auntie Ama"
            assert parent.conversation_state["data"]["name"] == "Auntie Ama"

    @pytest.mark.asyncio
    async def test_onboarding_collect_language(self, db_session: AsyncSession):
        """Test collecting parent's language preference."""
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {"name": "Auntie Ama"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_button_message.return_value = "wamid.test456"

            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "list_reply",
                    "list_reply": {"id": "lang_twi", "title": "Twi"},
                },
                message_id="wamid.incoming456",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is False
            assert result.next_step == "AWAITING_CONSENT"

            # Verify language saved
            await db_session.refresh(parent)
            assert parent.preferred_language == "tw"
            assert parent.conversation_state["data"]["language"] == "tw"
            assert parent.conversation_state["step"] == "AWAITING_CONSENT"

            # Verify consent request sent
            mock_client.send_button_message.assert_called_once()
            call_kwargs = mock_client.send_button_message.call_args.kwargs
            assert "consent" in call_kwargs["body"].lower()
            assert len(call_kwargs["buttons"]) == 2

    @pytest.mark.asyncio
    async def test_onboarding_invalid_language(self, db_session: AsyncSession):
        """Test invalid language selection prompts re-selection."""
        parent = Parent(
            phone="+233501234567",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {"name": "Auntie Ama"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test789"

            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="invalid",
                message_id="wamid.incoming789",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is False
            assert result.next_step == "AWAITING_LANGUAGE"

            # Verify still in same step
            await db_session.refresh(parent)
            assert parent.conversation_state["step"] == "AWAITING_LANGUAGE"
            # Language not changed from default
            assert parent.preferred_language == "en"

    @pytest.mark.asyncio
    async def test_onboarding_consent_given(self, db_session: AsyncSession):
        """Test parent gives consent and completes onboarding."""
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            preferred_language="tw",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CONSENT",
                "data": {"name": "Auntie Ama", "language": "tw"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test321"

            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "consent_yes", "title": "Yes, I consent"},
                },
                message_id="wamid.incoming321",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is True
            assert result.next_step is None

            # Verify onboarding completed
            await db_session.refresh(parent)
            assert parent.opted_in is True
            assert parent.opted_in_at is not None
            assert parent.onboarded_at is not None
            assert parent.diagnostic_consent is True
            assert parent.diagnostic_consent_at is not None
            assert parent.conversation_state is None  # Cleared after completion

            # Verify confirmation message sent
            mock_client.send_text_message.assert_called_once()
            call_kwargs = mock_client.send_text_message.call_args.kwargs
            assert (
                "all set" in call_kwargs["text"].lower()
                or "wonderful" in call_kwargs["text"].lower()
            )

    @pytest.mark.asyncio
    async def test_onboarding_consent_declined(self, db_session: AsyncSession):
        """Test parent declines consent but still completes onboarding."""
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            preferred_language="tw",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CONSENT",
                "data": {"name": "Auntie Ama", "language": "tw"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test654"

            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "consent_no", "title": "No, thank you"},
                },
                message_id="wamid.incoming654",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is True
            assert result.next_step is None

            # Verify onboarding completed but no diagnostic consent
            await db_session.refresh(parent)
            assert parent.opted_in is True  # Still opted in for messages
            assert parent.opted_in_at is not None
            assert parent.onboarded_at is not None
            assert parent.diagnostic_consent is False
            assert parent.diagnostic_consent_at is not None
            assert parent.conversation_state is None

            # Verify message acknowledges no consent
            mock_client.send_text_message.assert_called_once()
            call_kwargs = mock_client.send_text_message.call_args.kwargs
            assert (
                "understand" in call_kwargs["text"].lower()
                or "not send" in call_kwargs["text"].lower()
            )

    @pytest.mark.asyncio
    async def test_onboarding_invalid_button(self, db_session: AsyncSession):
        """Test invalid button click prompts re-selection."""
        parent = Parent(
            phone="+233501234567",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_CONSENT",
                "data": {"name": "Auntie Ama", "language": "tw"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test987"

            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={
                    "type": "button_reply",
                    "button_reply": {"id": "invalid_button", "title": "Invalid"},
                },
                message_id="wamid.incoming987",
            )

            assert result.flow_name == "FLOW-ONBOARD"
            assert result.completed is False
            assert result.next_step == "AWAITING_CONSENT"

            # Verify still in same step
            await db_session.refresh(parent)
            assert parent.conversation_state["step"] == "AWAITING_CONSENT"
            assert parent.opted_in is False


class TestFlowStateManagement:
    """Test conversation state management."""

    @pytest.mark.asyncio
    async def test_resume_interrupted_flow(self, db_session: AsyncSession):
        """Test resuming flow after interruption."""
        parent = Parent(
            phone="+233501234567",
            preferred_name="Auntie Ama",
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "AWAITING_LANGUAGE",
                "data": {"name": "Auntie Ama"},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_list_message.return_value = "wamid.test123"

            result = await executor.process_message(
                parent=parent,
                message_type="interactive",
                message_content={"id": "lang_twi", "title": "Twi"},
                message_id="wamid.incoming123",
            )

            # Should process from current step
            assert result.flow_name == "FLOW-ONBOARD"

    @pytest.mark.asyncio
    async def test_clear_state_on_flow_completion(self, db_session: AsyncSession):
        """Test conversation state cleared when flow completes."""
        parent = Parent(
            phone="+233501234567",
            opted_in=True,
            conversation_state={
                "flow": "FLOW-ONBOARD",
                "step": "FINAL_STEP",
                "data": {},
            },
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient"):
            result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="continue",
                message_id="wamid.incoming123",
            )

            if result.completed:
                await db_session.refresh(parent)
                assert parent.conversation_state is None

    @pytest.mark.asyncio
    async def test_session_expiry_tracking(self, db_session: AsyncSession):
        """Test 24-hour session window tracking."""
        parent = Parent(
            phone="+233501234567",
            last_message_at=None,
            session_expires_at=None,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient"):
            await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="Hi",
                message_id="wamid.incoming123",
            )

            await db_session.refresh(parent)
            assert parent.last_message_at is not None
            assert parent.session_expires_at is not None

            # Session should expire ~24 hours from now
            expected_expiry = parent.last_message_at + timedelta(hours=24)
            assert abs((parent.session_expires_at - expected_expiry).total_seconds()) < 60


class TestFlowResult:
    """Test FlowResult dataclass."""

    def test_flow_result_creation(self):
        """Test creating FlowResult."""
        result = FlowResult(
            flow_name="FLOW-ONBOARD",
            message_sent=True,
            message_id="wamid.test123",
            next_step="AWAITING_NAME",
            completed=False,
            error=None,
        )

        assert result.flow_name == "FLOW-ONBOARD"
        assert result.message_sent is True
        assert result.completed is False

    def test_flow_result_with_error(self):
        """Test FlowResult with error."""
        result = FlowResult(
            flow_name="FLOW-ONBOARD",
            message_sent=False,
            message_id=None,
            next_step=None,
            completed=False,
            error="WhatsApp API error",
        )

        assert result.error is not None
        assert result.message_sent is False


class TestErrorHandling:
    """Test error handling in flow executor."""

    @pytest.mark.asyncio
    async def test_handle_invalid_message_type(self, db_session: AsyncSession):
        """Test handling unknown message types."""
        parent = Parent(
            phone="+233501234567",
            conversation_state=None,
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.from_settings.return_value = mock_client
            mock_client.send_text_message.return_value = "wamid.test123"

            result = await executor.process_message(
                parent=parent,
                message_type="unknown_type",
                message_content="test",
                message_id="wamid.test",
            )

            # Should gracefully handle unknown types
            assert result.error is None or "unknown" in result.error.lower()

    @pytest.mark.asyncio
    async def test_handle_corrupted_state(self, db_session: AsyncSession):
        """Test handling corrupted conversation state."""
        parent = Parent(
            phone="+233501234567",
            conversation_state={"invalid": "state"},  # Missing required fields
        )
        db_session.add(parent)
        await db_session.commit()

        executor = FlowExecutor(db=db_session)

        with patch("gapsense.engagement.flow_executor.WhatsAppClient"):
            _result = await executor.process_message(
                parent=parent,
                message_type="text",
                message_content="Hi",
                message_id="wamid.test",
            )

            # Should recover by starting fresh flow
            await db_session.refresh(parent)
            assert parent.conversation_state is None or "flow" in parent.conversation_state
