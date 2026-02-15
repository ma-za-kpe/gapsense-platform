"""
WhatsApp Conversation Flow Executor

Orchestrates multi-step WhatsApp conversations with parents.
Manages conversation state transitions and routes messages to flow handlers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.core.models import Parent

from sqlalchemy.orm.attributes import flag_modified

from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


@dataclass
class FlowResult:
    """Result of processing a message through a flow.

    Attributes:
        flow_name: Name of the flow that processed the message
        message_sent: Whether a response was sent to the parent
        message_id: WhatsApp message ID of sent response (if any)
        next_step: Next step in the flow (None if completed)
        completed: Whether the flow is now completed
        error: Error message if processing failed
    """

    flow_name: str
    message_sent: bool
    message_id: str | None
    next_step: str | None
    completed: bool
    error: str | None = None


class FlowExecutor:
    """Executes WhatsApp conversation flows.

    Responsibilities:
    - Route incoming messages to appropriate flow handlers
    - Manage conversation state (Parent.conversation_state)
    - Track 24-hour session window
    - Send responses via WhatsAppClient
    """

    # Opt-out keywords (case-insensitive)
    OPT_OUT_KEYWORDS = frozenset(["stop", "unsubscribe", "cancel", "quit", "opt out", "optout"])

    def __init__(self, *, db: AsyncSession):
        """Initialize flow executor.

        Args:
            db: Database session for state persistence
        """
        self.db = db

    async def process_message(
        self,
        *,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
        message_id: str,
    ) -> FlowResult:
        """Process incoming message and execute appropriate flow.

        Args:
            parent: Parent model instance
            message_type: Message type (text, interactive, image, etc.)
            message_content: Message content (text string or structured dict)
            message_id: WhatsApp message ID

        Returns:
            FlowResult with processing outcome
        """
        try:
            # Update session tracking
            await self._update_session_tracking(parent)

            # Check for opt-out (takes precedence over all flows)
            if self._is_opt_out_message(message_type, message_content):
                return await self._handle_opt_out(parent)

            # Get current flow state
            current_state = parent.conversation_state or {}
            current_flow = current_state.get("flow")

            # Route to appropriate flow handler
            if current_flow == "FLOW-ONBOARD":
                return await self._continue_onboarding(parent, message_type, message_content)
            elif current_flow is None:
                # No active flow - start new flow
                return await self._start_new_flow(parent, message_type, message_content)
            else:
                # Unknown flow - reset state and start fresh
                logger.warning(f"Unknown flow: {current_flow}. Resetting state.")
                parent.conversation_state = None
                await self.db.commit()
                return await self._start_new_flow(parent, message_type, message_content)

        except Exception as e:
            logger.error(f"Error processing message for {parent.phone}: {e}", exc_info=True)
            return FlowResult(
                flow_name="UNKNOWN",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=False,
                error=str(e),
            )

    def _is_opt_out_message(self, message_type: str, message_content: str | dict[str, Any]) -> bool:
        """Check if message is an opt-out request.

        Args:
            message_type: Message type
            message_content: Message content

        Returns:
            True if message requests opt-out
        """
        if message_type != "text":
            return False

        if not isinstance(message_content, str):
            return False

        return message_content.strip().lower() in self.OPT_OUT_KEYWORDS

    async def _handle_opt_out(self, parent: Parent) -> FlowResult:
        """Handle parent opt-out (FLOW-OPT-OUT).

        Wolf/Aurino compliance: Instant opt-out, no friction, no confirmation.

        Args:
            parent: Parent requesting opt-out

        Returns:
            FlowResult for opt-out completion
        """
        # Mark parent as opted out
        parent.opted_out = True
        parent.opted_out_at = datetime.now(UTC)
        parent.conversation_state = None  # Clear any active flows
        await self.db.commit()

        # Send confirmation message
        client = WhatsAppClient.from_settings()

        parent_name = parent.preferred_name or "friend"
        opt_out_message = (
            f"We've stopped all messages. Your data will be removed.\n\n"
            f"If you ever want to restart, just send us 'Hi'. "
            f"Thank you, {parent_name}. 🙏"
        )

        try:
            message_id = await client.send_text_message(
                to=parent.phone,
                text=opt_out_message,
            )

            logger.info(f"Parent {parent.phone} opted out successfully")

            return FlowResult(
                flow_name="FLOW-OPT-OUT",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send opt-out confirmation to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-OPT-OUT",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=True,  # Still mark as completed (opt-out succeeded)
                error=str(e),
            )

    async def _start_new_flow(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Start a new conversation flow.

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content

        Returns:
            FlowResult from flow start
        """
        # For now, default to starting onboarding for new parents
        # In future, this could route to different flows based on context

        if not parent.opted_in:
            # Start onboarding flow
            return await self._start_onboarding(parent)
        else:
            # Parent already onboarded - send help message
            return await self._send_help_message(parent)

    async def _start_onboarding(self, parent: Parent) -> FlowResult:
        """Start onboarding flow (FLOW-ONBOARD).

        Args:
            parent: Parent to onboard

        Returns:
            FlowResult for onboarding start
        """
        # Initialize conversation state
        parent.conversation_state = {
            "flow": "FLOW-ONBOARD",
            "step": "AWAITING_NAME",
            "data": {},
        }
        await self.db.commit()

        # Send welcome message with name prompt
        client = WhatsAppClient.from_settings()

        welcome_message = (
            "Welcome to GapSense! 📚\n\n"
            "I'm here to help you support your child's learning with fun "
            "3-minute activities at home.\n\n"
            "What would you like me to call you?"
        )

        try:
            message_id = await client.send_text_message(
                to=parent.phone,
                text=welcome_message,
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_NAME",
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send onboarding start to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_NAME",
                completed=False,
                error=str(e),
            )

    async def _continue_onboarding(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Continue onboarding flow from current step.

        Args:
            parent: Parent in onboarding
            message_type: Message type
            message_content: Message content

        Returns:
            FlowResult for current step
        """
        current_state = parent.conversation_state or {}
        current_step = current_state.get("step")

        if current_step == "AWAITING_NAME":
            return await self._onboard_collect_name(parent, message_type, message_content)
        else:
            # Unknown step - this will be implemented with full onboarding handler
            logger.warning(f"Unknown onboarding step: {current_step}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step=current_step,
                completed=False,
                error=f"Unknown step: {current_step}",
            )

    async def _onboard_collect_name(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Collect parent's preferred name.

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content (should be text with name)

        Returns:
            FlowResult for name collection
        """
        if message_type != "text" or not isinstance(message_content, str):
            # Invalid input - prompt again
            client = WhatsAppClient.from_settings()
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please send me your name as a text message. For example: 'Auntie Ama'",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_NAME",
                completed=False,
                error=None,
            )

        # Save name
        name = message_content.strip()
        parent.preferred_name = name

        # Update conversation state
        if parent.conversation_state is None:
            parent.conversation_state = {"data": {}}
        elif "data" not in parent.conversation_state:
            parent.conversation_state["data"] = {}

        parent.conversation_state["data"]["name"] = name
        flag_modified(parent, "conversation_state")  # Mark as modified for SQLAlchemy

        await self.db.commit()

        # Send acknowledgment (next steps handled by full onboarding handler)
        client = WhatsAppClient.from_settings()
        ack_message = f"Nice to meet you, {name}! 😊\n\n[Onboarding continues...]"

        try:
            message_id = await client.send_text_message(
                to=parent.phone,
                text=ack_message,
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_LANGUAGE",  # Would continue to language selection
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send name acknowledgment to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_LANGUAGE",
                completed=False,
                error=str(e),
            )

    async def _send_help_message(self, parent: Parent) -> FlowResult:
        """Send help message to onboarded parent.

        Args:
            parent: Parent instance

        Returns:
            FlowResult for help message
        """
        client = WhatsAppClient.from_settings()

        parent_name = parent.preferred_name or "friend"
        help_message = (
            f"Hi {parent_name}! 👋\n\n"
            "Here's what I can help with:\n\n"
            "• Get learning activities for your child\n"
            "• Check on your child's progress\n"
            "• Answer questions about activities\n\n"
            "What would you like to do?"
        )

        try:
            message_id = await client.send_text_message(
                to=parent.phone,
                text=help_message,
            )

            return FlowResult(
                flow_name="HELP",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send help message to {parent.phone}: {e}")
            return FlowResult(
                flow_name="HELP",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=False,
                error=str(e),
            )

    async def _update_session_tracking(self, parent: Parent) -> None:
        """Update 24-hour session window tracking.

        Args:
            parent: Parent instance
        """
        now = datetime.now(UTC)
        parent.last_message_at = now
        parent.session_expires_at = now + timedelta(hours=24)
        await self.db.commit()
