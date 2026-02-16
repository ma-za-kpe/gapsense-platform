"""
WhatsApp Conversation Flow Executor

Orchestrates multi-step WhatsApp conversations with parents.
Manages conversation state transitions and routes messages to flow handlers.

TODO: L1-FIRST TRANSLATIONS NEEDED (Wolf/Aurino Compliance VIOLATION)
    ⚠️ CRITICAL: All messages in this file are currently hardcoded in English.
    This violates L1-first principle. Must add translations for:
    - Twi (tw)
    - Ewe (ee)
    - Ga (ga)
    - Dagbani (dag)

    User's language choice is in parent.preferred_language.
    Implement translation lookup function or message catalog system.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.core.models import Parent, Student

from sqlalchemy.orm.attributes import flag_modified

from gapsense.core.models import Student
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

    # Opt-out keywords (case-insensitive, L1-first for Wolf/Aurino compliance)
    OPT_OUT_KEYWORDS = frozenset(
        [
            # English
            "stop",
            "unsubscribe",
            "cancel",
            "quit",
            "opt out",
            "optout",
            # Twi (Akan)
            "gyae",
            "gyina",
            # Ewe
            "tɔtɔ",
            "tɔe",
            # Ga
            "tsia",
            # Dagbani
            "nyɛli",
        ]
    )

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
        # TODO: L1 TRANSLATION - Opt-out message must be in parent's preferred_language
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
        """Start onboarding flow (FLOW-ONBOARD) with template message.

        Spec: gapsense_whatsapp_flows.json Step 1
        Sends TMPL-ONBOARD-001 template (requires Meta pre-approval).

        Args:
            parent: Parent to onboard

        Returns:
            FlowResult for onboarding start
        """
        # Initialize conversation state
        parent.conversation_state = {
            "flow": "FLOW-ONBOARD",
            "step": "AWAITING_OPT_IN",
            "data": {},
        }
        await self.db.commit()

        # Send template welcome message
        client = WhatsAppClient.from_settings()

        # TODO: L1 TRANSLATION - Use language-specific template variant (TMPL-ONBOARD-001-TW, etc.)
        # when parent's language is known from previous interaction
        try:
            message_id = await client.send_template_message(
                to=parent.phone,
                template_name="gapsense_welcome",  # TMPL-ONBOARD-001
                language_code="en",
                # Note: Template parameters would include school_name and child_name
                # For initial onboarding, we don't have these yet
                # This template should have a no-parameter variant
            )

            logger.info(f"Started onboarding for {parent.phone} with template message")

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_OPT_IN",
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send onboarding template to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_OPT_IN",
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

        Spec-Compliant Onboarding Flow (gapsense_whatsapp_flows.json lines 85-197):
            1. AWAITING_OPT_IN → handle opt-in button
            2. AWAITING_CHILD_NAME → collect child's first_name
            3. AWAITING_CHILD_AGE → collect child's age
            4. AWAITING_CHILD_GRADE → collect child's grade (B1-B9)
            5. AWAITING_LANGUAGE → collect language preference
            6. Complete → create Student record, set onboarded_at

        Args:
            parent: Parent in onboarding
            message_type: Message type
            message_content: Message content

        Returns:
            FlowResult for current step
        """
        current_state = parent.conversation_state or {}
        current_step = current_state.get("step")

        if current_step == "AWAITING_OPT_IN":
            return await self._onboard_opt_in(parent, message_type, message_content)
        elif current_step == "AWAITING_CHILD_NAME":
            return await self._onboard_collect_child_name(parent, message_type, message_content)
        elif current_step == "AWAITING_CHILD_AGE":
            return await self._onboard_collect_child_age(parent, message_type, message_content)
        elif current_step == "AWAITING_CHILD_GRADE":
            return await self._onboard_collect_child_grade(parent, message_type, message_content)
        elif current_step == "AWAITING_LANGUAGE":
            return await self._onboard_collect_language(parent, message_type, message_content)
        else:
            # Unknown step
            logger.warning(f"Unknown onboarding step: {current_step}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step=current_step,
                completed=False,
                error=f"Unknown step: {current_step}",
            )

    async def _onboard_opt_in(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Handle opt-in button response (Step 2 of spec).

        Spec: gapsense_whatsapp_flows.json Step 2
        Expects button response: "yes_start", "tell_me_more", or "not_now"

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content

        Returns:
            FlowResult for opt-in step
        """
        # Check for button response
        if message_type != "interactive" or not isinstance(message_content, dict):
            # Invalid input - they need to click a button
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please click one of the buttons above to continue.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_OPT_IN",
                completed=False,
                error=None,
            )

        # Webhook extracts button_reply, so message_content IS the button_reply dict
        # But unit tests may pass full structure, so handle both
        if "button_reply" in message_content:
            button_reply = message_content.get("button_reply", {})
            button_id = button_reply.get("id")
        else:
            # Webhook format: message_content IS the button_reply
            button_id = message_content.get("id")

        if button_id == "yes_start":
            # Parent opted in! Set flags and move to collect child name
            parent.opted_in = True
            parent.opted_in_at = datetime.now(UTC)

            if parent.conversation_state is None:
                parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
            parent.conversation_state["step"] = "AWAITING_CHILD_NAME"
            flag_modified(parent, "conversation_state")

            await self.db.commit()

            # Ask for child's name
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Great! 🎉 Just a few quick questions.\n\nWhat is your child's first name?",
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_NAME",
                completed=False,
                error=None,
            )

        elif button_id == "not_now":
            # Parent declined - clear state and log
            parent.conversation_state = None
            await self.db.commit()

            logger.info(f"Parent {parent.phone} declined onboarding ('not_now')")

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=True,  # Flow complete (declined)
                error=None,
            )

        else:
            # Unknown button - ask again
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select one of the options above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_OPT_IN",
                completed=False,
                error=None,
            )

    async def _onboard_collect_child_name(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Collect CHILD's first name (Step 3 of spec).

        Spec: gapsense_whatsapp_flows.json Step 3-4
        This is NOT the parent's name - it's the child's name for Student record.

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content (should be text with child's name)

        Returns:
            FlowResult for name collection
        """
        if message_type != "text" or not isinstance(message_content, str):
            # Invalid input - prompt again
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please send me your child's first name as a text message. For example: 'Kwame'",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_NAME",
                completed=False,
                error=None,
            )

        # Save CHILD's name to conversation data (will be used for Student creation)
        child_name = message_content.strip()

        # Update conversation state
        if parent.conversation_state is None:
            parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
        elif "data" not in parent.conversation_state:
            parent.conversation_state["data"] = {}

        parent.conversation_state["data"]["child_name"] = child_name
        parent.conversation_state["step"] = "AWAITING_CHILD_AGE"
        flag_modified(parent, "conversation_state")

        await self.db.commit()

        # Ask for child's age (buttons)
        client = WhatsAppClient.from_settings()

        try:
            # TODO: L1 TRANSLATION
            message_id = await client.send_button_message(
                to=parent.phone,
                body=f"Thanks! How old is {child_name}?",
                buttons=[
                    {"id": "age_5", "title": "5-6 years"},
                    {"id": "age_7", "title": "7-8 years"},
                    {"id": "age_9", "title": "9-10 years"},
                ],
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_AGE",
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send age selection to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_CHILD_AGE",
                completed=False,
                error=str(e),
            )

    async def _onboard_collect_child_age(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Collect child's age (Step 4 of spec).

        Spec: gapsense_whatsapp_flows.json Step 4-5

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content (should be button response)

        Returns:
            FlowResult for age collection
        """
        # Check for button response
        if message_type != "interactive" or not isinstance(message_content, dict):
            # Invalid input - they need to click a button
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select your child's age from the buttons above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_AGE",
                completed=False,
                error=None,
            )

        # Webhook extracts button_reply, so message_content IS the button_reply dict
        # But unit tests may pass full structure, so handle both
        if "button_reply" in message_content:
            button_reply = message_content.get("button_reply", {})
            button_id = button_reply.get("id")
        else:
            # Webhook format: message_content IS the button_reply
            button_id = message_content.get("id")

        # Map button ID to approximate age
        age_map = {
            "age_5": 5,
            "age_7": 7,
            "age_9": 9,
            "age_11": 11,
        }

        if button_id not in age_map:
            # Invalid button
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select one of the age options above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_AGE",
                completed=False,
                error=None,
            )

        # Save age
        age = age_map[button_id]

        if parent.conversation_state is None:
            parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
        parent.conversation_state["data"]["child_age"] = age
        parent.conversation_state["step"] = "AWAITING_CHILD_GRADE"
        flag_modified(parent, "conversation_state")

        await self.db.commit()

        # Ask for child's grade (list)
        client = WhatsAppClient.from_settings()

        child_name = parent.conversation_state["data"].get("child_name", "your child")

        try:
            # TODO: L1 TRANSLATION
            message_id = await client.send_list_message(
                to=parent.phone,
                body=f"What class is {child_name} in?",
                button_text="Select class",
                sections=[
                    {
                        "title": "Primary",
                        "rows": [
                            {"id": "grade_B1", "title": "Class 1 (B1)"},
                            {"id": "grade_B2", "title": "Class 2 (B2)"},
                            {"id": "grade_B3", "title": "Class 3 (B3)"},
                            {"id": "grade_B4", "title": "Class 4 (B4)"},
                            {"id": "grade_B5", "title": "Class 5 (B5)"},
                            {"id": "grade_B6", "title": "Class 6 (B6)"},
                        ],
                    },
                    {
                        "title": "JHS",
                        "rows": [
                            {"id": "grade_B7", "title": "JHS 1 (B7)"},
                            {"id": "grade_B8", "title": "JHS 2 (B8)"},
                            {"id": "grade_B9", "title": "JHS 3 (B9)"},
                        ],
                    },
                ],
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_GRADE",
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send grade selection to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_CHILD_GRADE",
                completed=False,
                error=str(e),
            )

    async def _onboard_collect_child_grade(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Collect child's grade (Step 5 of spec).

        Spec: gapsense_whatsapp_flows.json Step 5-6

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content (should be list response)

        Returns:
            FlowResult for grade collection
        """
        # Check for list response
        if (
            message_type != "interactive"
            or not isinstance(message_content, dict)
            or message_content.get("type") != "list_reply"
        ):
            # Invalid input - they need to select from list
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select your child's class from the list above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_GRADE",
                completed=False,
                error=None,
            )

        # Webhook extracts list_reply, so message_content IS the list_reply dict
        # But unit tests may pass full structure, so handle both
        if "list_reply" in message_content:
            list_reply = message_content.get("list_reply", {})
            grade_id = list_reply.get("id")
        else:
            # Webhook format: message_content IS the list_reply
            grade_id = message_content.get("id")

        # Extract grade from ID (e.g., "grade_B2" → "B2")
        if not grade_id or not grade_id.startswith("grade_"):
            # Invalid selection
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select a class from the list above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_CHILD_GRADE",
                completed=False,
                error=None,
            )

        grade = grade_id.replace("grade_", "")  # "grade_B2" → "B2"

        # Save grade
        if parent.conversation_state is None:
            parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
        parent.conversation_state["data"]["child_grade"] = grade
        parent.conversation_state["step"] = "AWAITING_LANGUAGE"
        flag_modified(parent, "conversation_state")

        await self.db.commit()

        # Ask for language preference (final step before completion)
        client = WhatsAppClient.from_settings()

        try:
            # TODO: L1 TRANSLATION
            message_id = await client.send_button_message(
                to=parent.phone,
                body="Last question — what language do you prefer?",
                buttons=[
                    {"id": "lang_en", "title": "English"},
                    {"id": "lang_twi", "title": "Twi"},
                    {"id": "lang_ewe", "title": "Ewe"},
                ],
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_LANGUAGE",
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send language selection to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_LANGUAGE",
                completed=False,
                error=str(e),
            )

    async def _onboard_collect_language(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Collect language preference and CREATE STUDENT RECORD (Step 6-7 of spec).

        Spec: gapsense_whatsapp_flows.json Step 6-7
        This is the FINAL step - creates Student record with collected data.

        Args:
            parent: Parent instance
            message_type: Message type
            message_content: Message content (should be button response)

        Returns:
            FlowResult for language collection and onboarding completion
        """
        # Check for button response
        if message_type != "interactive" or not isinstance(message_content, dict):
            # Invalid input - they need to click a button
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select your preferred language from the buttons above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_LANGUAGE",
                completed=False,
                error=None,
            )

        # Webhook extracts button_reply, so message_content IS the button_reply dict
        # But unit tests may pass full structure, so handle both
        if "button_reply" in message_content:
            button_reply = message_content.get("button_reply", {})
            button_id = button_reply.get("id")
        else:
            # Webhook format: message_content IS the button_reply
            button_id = message_content.get("id")

        # Language mapping
        language_map = {
            "lang_en": "en",
            "lang_twi": "tw",
            "lang_ewe": "ee",
            "lang_ga": "ga",
            "lang_dagbani": "dag",
        }

        if button_id not in language_map:
            # Invalid button
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please select one of the language options above.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_LANGUAGE",
                completed=False,
                error=None,
            )

        # Save language
        language_code = language_map[button_id]
        parent.preferred_language = language_code

        # Get collected child data from conversation_state
        conversation_data = (
            parent.conversation_state.get("data", {}) if parent.conversation_state else {}
        )
        child_name = conversation_data.get("child_name")
        child_age = conversation_data.get("child_age")
        child_grade = conversation_data.get("child_grade")

        if not child_name or not child_grade:
            # Missing required data - this shouldn't happen but handle gracefully
            logger.error(
                f"Missing child data for {parent.phone}: name={child_name}, grade={child_grade}"
            )
            client = WhatsAppClient.from_settings()
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Sorry, something went wrong. Please start over by sending 'Hi'.",
            )
            parent.conversation_state = None
            await self.db.commit()
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error="Missing required child data",
            )

        # CRITICAL: Create Student record
        student = Student(
            first_name=child_name,
            age=child_age,
            current_grade=child_grade,
            primary_parent_id=parent.id,
            home_language=language_code,
            school_language="English",  # Default for Ghana
            is_active=True,
        )
        self.db.add(student)

        # Complete onboarding
        now = datetime.now(UTC)
        parent.onboarded_at = now
        parent.conversation_state = None  # Clear state - onboarding complete

        try:
            await self.db.commit()
            logger.info(
                f"Onboarding complete for {parent.phone}: Student {student.first_name} "
                f"(grade {student.current_grade}) created with ID {student.id}"
            )
        except Exception as e:
            logger.error(f"Failed to create Student for {parent.phone}: {e}")
            await self.db.rollback()
            client = WhatsAppClient.from_settings()
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Sorry, something went wrong. Please try again later.",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error=str(e),
            )

        # Send completion message
        client = WhatsAppClient.from_settings()

        try:
            # TODO: L1 TRANSLATION - Completion message must be in parent's preferred_language
            message_id = await client.send_text_message(
                to=parent.phone,
                text=(
                    f"All set! 🌟\n\n"
                    f"{child_name} is registered. We'll send a quick learning check soon "
                    f"to find the perfect activity for them.\n\n"
                    f"We only use {child_name}'s first name and class to help them learn. "
                    f"Your info is private.\n\n"
                    f"Thank you! 🙏"
                ),
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=True,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send onboarding completion to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=True,  # Still complete - Student was created
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
        # TODO: L1 TRANSLATION - Help message must be in parent's preferred_language
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
