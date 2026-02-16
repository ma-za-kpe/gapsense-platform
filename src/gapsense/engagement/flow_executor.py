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
from gapsense.engagement.commands import handle_command, is_command
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

            # Check for commands (RESTART, CANCEL, HELP, STATUS)
            if (
                message_type == "text"
                and isinstance(message_content, str)
                and is_command(message_content)
            ):
                return await self._handle_command(parent, message_content)

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

    async def _handle_command(self, parent: Parent, command_text: str) -> FlowResult:
        """Handle error recovery commands (RESTART, CANCEL, HELP, STATUS).

        Args:
            parent: Parent instance
            command_text: Command text

        Returns:
            FlowResult for command handling
        """
        current_state = parent.conversation_state or {}
        has_active_flow = current_state.get("flow") is not None
        current_step = current_state.get("step")

        # Handle the command
        cmd_result = handle_command(command_text, has_active_flow, current_step)

        if not cmd_result.handled:
            # Not a recognized command - let it flow through normal processing
            return FlowResult(
                flow_name="COMMAND",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=False,
                error="Command not recognized",
            )

        # Clear conversation state if requested
        if cmd_result.clear_state:
            parent.conversation_state = None
            await self.db.commit()

        # Send response message if provided
        if cmd_result.message:
            client = WhatsAppClient.from_settings()
            try:
                message_id = await client.send_text_message(
                    to=parent.phone,
                    text=cmd_result.message,
                )

                return FlowResult(
                    flow_name="COMMAND",
                    message_sent=True,
                    message_id=message_id,
                    next_step=None,
                    completed=True,
                    error=None,
                )
            except Exception as e:
                logger.error(f"Failed to send command response to {parent.phone}: {e}")
                return FlowResult(
                    flow_name="COMMAND",
                    message_sent=False,
                    message_id=None,
                    next_step=None,
                    completed=True,
                    error=str(e),
                )

        return FlowResult(
            flow_name="COMMAND",
            message_sent=False,
            message_id=None,
            next_step=None,
            completed=True,
            error=None,
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

        NEW Teacher-Initiated Onboarding Flow (MVP Blueprint):
            1. AWAITING_OPT_IN → handle opt-in button
            2. AWAITING_STUDENT_SELECTION → parent selects child from teacher's roster
            3. AWAITING_DIAGNOSTIC_CONSENT → get consent for diagnostic assessment
            4. AWAITING_LANGUAGE → collect language preference
            5. Complete → link parent to student, set onboarded_at

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
        elif current_step == "AWAITING_STUDENT_SELECTION":
            return await self._onboard_select_student(parent, message_type, message_content)
        elif current_step == "AWAITING_DIAGNOSTIC_CONSENT":
            return await self._onboard_collect_consent(parent, message_type, message_content)
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
            # Parent opted in! Set flags and move to student selection
            parent.opted_in = True
            parent.opted_in_at = datetime.now(UTC)

            if parent.conversation_state is None:
                parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
            parent.conversation_state["step"] = "AWAITING_STUDENT_SELECTION"
            flag_modified(parent, "conversation_state")

            await self.db.commit()

            # Query unlinked students and show selection list
            return await self._show_student_selection_list(parent)

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

    async def _show_student_selection_list(self, parent: Parent) -> FlowResult:
        """Show list of unlinked students for parent to select from.

        Queries all students where primary_parent_id IS NULL and displays them
        as a numbered list with full_name, grade, and school for disambiguation.

        For MVP, shows ALL unlinked students. For production, would filter by:
        - School/district (based on phone area code or teacher linkage)
        - Grade range
        - Geographic proximity

        Args:
            parent: Parent selecting their child

        Returns:
            FlowResult with student selection message
        """
        from sqlalchemy import select

        # Query unlinked students
        stmt = (
            select(Student)
            .where(Student.primary_parent_id == None)  # noqa: E711
            .where(Student.is_active == True)  # noqa: E712
            .order_by(Student.created_at.desc())
            .limit(100)  # Safety limit for MVP
        )
        result = await self.db.execute(stmt)
        students = result.scalars().all()

        if not students:
            # No students available - this shouldn't happen if teachers onboard first
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text=(
                    "No students are available for linking yet. "
                    "Please make sure your child's teacher has registered their class first.\n\n"
                    "Contact your school if you need assistance."
                ),
            )
            parent.conversation_state = None
            await self.db.commit()
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error="No unlinked students available",
            )

        # Build student list message
        # Format: "1. Kwame Mensah (JHS 1, Accra Academy JHS)"
        student_list_lines = []
        for idx, student in enumerate(students[:50], 1):  # Show max 50 for UX
            # Use full_name if available, otherwise first_name
            display_name = student.full_name or student.first_name
            school_name = student.school.name if student.school else "Unknown School"
            line = f"{idx}. {display_name} (Grade {student.current_grade}, {school_name})"
            student_list_lines.append(line)

        student_list_text = "\n".join(student_list_lines)

        # Store student IDs in conversation state for selection
        student_ids_map = {
            str(idx + 1): str(student.id) for idx, student in enumerate(students[:50])
        }
        if parent.conversation_state is None:
            parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
        parent.conversation_state["data"]["student_ids_map"] = student_ids_map
        flag_modified(parent, "conversation_state")
        await self.db.commit()

        # Send selection message
        client = WhatsAppClient.from_settings()
        # TODO: L1 TRANSLATION
        message = (
            f"Great! 🎉 Which child is yours?\n\n"
            f"{student_list_text}\n\n"
            f"Reply with the number (e.g., '1' for the first child)."
        )

        if len(students) > 50:
            message += f"\n\n(Showing first 50 of {len(students)} students. Contact support if you don't see your child.)"

        message_id = await client.send_text_message(to=parent.phone, text=message)

        return FlowResult(
            flow_name="FLOW-ONBOARD",
            message_sent=True,
            message_id=message_id,
            next_step="AWAITING_STUDENT_SELECTION",
            completed=False,
            error=None,
        )

    async def _onboard_select_student(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Handle parent's student selection (new Step 2).

        Parent replies with number from list (e.g., "1", "5", "10").
        System links parent to selected student.

        Args:
            parent: Parent making selection
            message_type: Message type
            message_content: Message content (should be text with number)

        Returns:
            FlowResult for student selection
        """
        if message_type != "text" or not isinstance(message_content, str):
            # Invalid input - prompt again
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Please reply with the number of your child from the list above (e.g., '1').",
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_STUDENT_SELECTION",
                completed=False,
                error=None,
            )

        # Extract number from message
        selection = message_content.strip()

        # Get student IDs map from conversation state
        conversation_data = (
            parent.conversation_state.get("data", {}) if parent.conversation_state else {}
        )
        student_ids_map = conversation_data.get("student_ids_map", {})

        if selection not in student_ids_map:
            # Invalid selection
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text=(
                    f"'{selection}' is not a valid number. "
                    "Please reply with a number from the list above (e.g., '1')."
                ),
            )
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_STUDENT_SELECTION",
                completed=False,
                error=None,
            )

        # Get selected student
        from uuid import UUID

        student_id = UUID(student_ids_map[selection])

        from sqlalchemy import select

        stmt = select(Student).where(Student.id == student_id)
        result = await self.db.execute(stmt)
        selected_student = result.scalar_one_or_none()

        if not selected_student:
            # Student not found (edge case - student deleted after list shown)
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Sorry, that student is no longer available. Please try again by sending 'START'.",
            )
            parent.conversation_state = None
            await self.db.commit()
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error="Selected student not found",
            )

        # Check if student already has a parent (race condition)
        if selected_student.primary_parent_id is not None:
            client = WhatsAppClient.from_settings()
            # TODO: L1 TRANSLATION
            message_id = await client.send_text_message(
                to=parent.phone,
                text=(
                    f"Sorry, {selected_student.first_name} already has a parent linked. "
                    "If this is an error, please contact your child's teacher."
                ),
            )
            parent.conversation_state = None
            await self.db.commit()
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error="Student already linked to another parent",
            )

        # Save student selection to conversation state (will link after consent)
        if parent.conversation_state is None:
            parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
        parent.conversation_state["data"]["selected_student_id"] = str(student_id)
        parent.conversation_state["step"] = "AWAITING_DIAGNOSTIC_CONSENT"
        flag_modified(parent, "conversation_state")
        await self.db.commit()

        # Ask for diagnostic consent
        client = WhatsAppClient.from_settings()
        # TODO: L1 TRANSLATION
        student_display_name = selected_student.full_name or selected_student.first_name
        try:
            message_id = await client.send_button_message(
                to=parent.phone,
                body=(
                    f"Perfect! You selected {student_display_name}.\n\n"
                    f"To help {selected_student.first_name} learn, we'll send a quick diagnostic quiz "
                    f"to find where they need support.\n\n"
                    f"This quiz is private - only you and the teacher will see results.\n\n"
                    f"Do you consent to this diagnostic assessment?"
                ),
                buttons=[
                    {"id": "consent_yes", "title": "Yes, proceed"},
                    {"id": "consent_no", "title": "No, skip for now"},
                ],
            )

            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="AWAITING_DIAGNOSTIC_CONSENT",
                completed=False,
                error=None,
            )

        except Exception as e:
            logger.error(f"Failed to send diagnostic consent to {parent.phone}: {e}")
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=False,
                message_id=None,
                next_step="AWAITING_DIAGNOSTIC_CONSENT",
                completed=False,
                error=str(e),
            )

    async def _onboard_collect_consent(
        self,
        parent: Parent,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> FlowResult:
        """Collect diagnostic consent (new Step 3).

        Args:
            parent: Parent providing consent
            message_type: Message type
            message_content: Message content (should be button response)

        Returns:
            FlowResult for consent collection
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
                next_step="AWAITING_DIAGNOSTIC_CONSENT",
                completed=False,
                error=None,
            )

        # Extract button ID
        if "button_reply" in message_content:
            button_reply = message_content.get("button_reply", {})
            button_id = button_reply.get("id")
        else:
            button_id = message_content.get("id")

        # Save consent decision
        if button_id == "consent_yes":
            parent.diagnostic_consent = True
            parent.diagnostic_consent_at = datetime.now(UTC)
        elif button_id == "consent_no":
            parent.diagnostic_consent = False
            parent.diagnostic_consent_at = datetime.now(UTC)
        else:
            # Unknown button
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
                next_step="AWAITING_DIAGNOSTIC_CONSENT",
                completed=False,
                error=None,
            )

        # Move to language selection
        if parent.conversation_state is None:
            parent.conversation_state = {"flow": "FLOW-ONBOARD", "data": {}}
        parent.conversation_state["step"] = "AWAITING_LANGUAGE"
        flag_modified(parent, "conversation_state")
        await self.db.commit()

        # Ask for language preference
        client = WhatsAppClient.from_settings()
        # TODO: L1 TRANSLATION (this is ironic - asking for language in English)
        try:
            message_id = await client.send_button_message(
                to=parent.phone,
                body="One last question: What language would you like me to use?",
                buttons=[
                    {"id": "lang_en", "title": "English"},
                    {"id": "lang_tw", "title": "Twi (Akan)"},
                    {"id": "lang_ga", "title": "Ga"},
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
            "lang_tw": "tw",  # Twi (Akan)
            "lang_twi": "tw",  # Alias for compatibility
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

        # Get selected student ID from conversation_state
        conversation_data = (
            parent.conversation_state.get("data", {}) if parent.conversation_state else {}
        )
        selected_student_id_str = conversation_data.get("selected_student_id")

        if not selected_student_id_str:
            # Missing student selection - this shouldn't happen but handle gracefully
            logger.error(f"Missing selected_student_id for {parent.phone}")
            client = WhatsAppClient.from_settings()
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Sorry, something went wrong. Please start over by sending 'START'.",
            )
            parent.conversation_state = None
            await self.db.commit()
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error="Missing selected_student_id",
            )

        # Get selected student
        from uuid import UUID

        from sqlalchemy import select

        student_id = UUID(selected_student_id_str)
        stmt = select(Student).where(Student.id == student_id)
        result = await self.db.execute(stmt)
        student = result.scalar_one_or_none()

        if not student:
            logger.error(f"Student {student_id} not found for {parent.phone}")
            client = WhatsAppClient.from_settings()
            message_id = await client.send_text_message(
                to=parent.phone,
                text="Sorry, that student is no longer available. Please start over by sending 'START'.",
            )
            parent.conversation_state = None
            await self.db.commit()
            return FlowResult(
                flow_name="FLOW-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=False,
                error="Selected student not found",
            )

        # CRITICAL: Link parent to student (don't create new student)
        student.primary_parent_id = parent.id
        student.home_language = language_code  # Update student's home language

        # Complete onboarding
        now = datetime.now(UTC)
        parent.onboarded_at = now
        parent.conversation_state = None  # Clear state - onboarding complete

        try:
            await self.db.commit()
            logger.info(
                f"Onboarding complete for {parent.phone}: Linked to student {student.first_name} "
                f"(ID {student.id}, grade {student.current_grade})"
            )
        except Exception as e:
            logger.error(f"Failed to link parent {parent.phone} to student: {e}")
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

        student_name = student.first_name
        try:
            # TODO: L1 TRANSLATION - Completion message must be in parent's preferred_language
            message_id = await client.send_text_message(
                to=parent.phone,
                text=(
                    f"All set! 🌟\n\n"
                    f"You're now linked to {student_name} (Grade {student.current_grade}). "
                    f"We'll send a quick diagnostic quiz soon to find where {student_name} needs support.\n\n"
                    f"We only use {student_name}'s first name and class to help them learn. "
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
