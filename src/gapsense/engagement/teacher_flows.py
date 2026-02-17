"""
Teacher WhatsApp Flows

Handles teacher-specific flows:
- FLOW-TEACHER-ONBOARD: Teacher registers class roster
- FLOW-EXERCISE-BOOK-SCAN: Teacher scans student work (future)
- FLOW-TEACHER-CONVERSATION: Conversational diagnostic partner (future)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from gapsense.core.models import School, Teacher

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from gapsense.core.models import School, Student
from gapsense.core.validation import (
    ValidationError,
    validate_class_name,
    validate_school_name,
    validate_student_count,
    validate_student_name,
)
from gapsense.engagement.commands import handle_command, is_command
from gapsense.engagement.whatsapp_client import WhatsAppClient

logger = logging.getLogger(__name__)


@dataclass
class TeacherFlowResult:
    """Result of processing a teacher message through a flow."""

    flow_name: str
    message_sent: bool
    message_id: str | None
    next_step: str | None
    completed: bool
    error: str | None = None


class TeacherFlowExecutor:
    """Executes teacher-specific WhatsApp flows.

    Responsibilities:
    - Handle teacher onboarding (class roster upload)
    - Handle exercise book scanning (future)
    - Handle teacher conversation partner (future)
    """

    def __init__(self, *, db: AsyncSession):
        """Initialize teacher flow executor.

        Args:
            db: Database session
        """
        self.db = db
        self.whatsapp = WhatsAppClient.from_settings()

    async def process_teacher_message(
        self,
        *,
        teacher: Teacher,
        message_type: str,
        message_content: str | dict[str, Any],
        message_id: str,
    ) -> TeacherFlowResult:
        """Process incoming teacher message.

        Args:
            teacher: Teacher model instance
            message_type: Message type (text, interactive, image, etc.)
            message_content: Message content
            message_id: WhatsApp message ID

        Returns:
            TeacherFlowResult with processing outcome
        """
        try:
            # Phase D.5: Check for expired session
            await self._check_session_expiry(teacher)

            # Update session tracking
            await self._update_session_tracking(teacher)

            # Check for commands (RESTART, CANCEL, HELP, STATUS)
            if (
                message_type == "text"
                and isinstance(message_content, str)
                and is_command(message_content)
            ):
                return await self._handle_teacher_command(teacher, message_content)

            # Get current flow state
            current_state = teacher.conversation_state or {}
            current_flow = current_state.get("flow")

            # Route to appropriate flow
            if current_flow == "FLOW-TEACHER-ONBOARD":
                return await self._continue_teacher_onboarding(
                    teacher, message_type, message_content
                )
            elif current_flow is None:
                # No active flow - check if starting onboarding
                if message_type == "text" and isinstance(message_content, str):
                    msg_lower = message_content.strip().lower()
                    if msg_lower in ("start", "hi", "hello"):
                        return await self._start_teacher_onboarding(teacher)

                # Unknown message - provide help
                return await self._send_teacher_help(teacher)
            else:
                # Unknown flow - reset
                logger.warning(f"Unknown teacher flow: {current_flow}. Resetting.")
                teacher.conversation_state = None
                await self.db.commit()
                return await self._send_teacher_help(teacher)

        except Exception as e:
            logger.error(f"Error processing teacher message: {e}", exc_info=True)
            return TeacherFlowResult(
                flow_name="UNKNOWN",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=False,
                error=str(e),
            )

    async def _start_teacher_onboarding(self, teacher: Teacher) -> TeacherFlowResult:
        """Start teacher onboarding flow (FLOW-TEACHER-ONBOARD).

        Args:
            teacher: Teacher starting onboarding

        Returns:
            TeacherFlowResult
        """
        # Initialize conversation state
        teacher.conversation_state = {
            "flow": "FLOW-TEACHER-ONBOARD",
            "step": "COLLECT_SCHOOL",
            "data": {},
        }
        flag_modified(teacher, "conversation_state")
        await self.db.commit()

        # Send welcome message
        message = (
            "Welcome to GapSense! 👋\n\n"
            "I'll help you set up your class in just a few minutes.\n\n"
            "First, what is your school name?\n"
            "Example: 'St. Mary's JHS, Accra'"
        )

        message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

        return TeacherFlowResult(
            flow_name="FLOW-TEACHER-ONBOARD",
            message_sent=True,
            message_id=message_id,
            next_step="COLLECT_SCHOOL",
            completed=False,
        )

    async def _continue_teacher_onboarding(
        self,
        teacher: Teacher,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> TeacherFlowResult:
        """Continue teacher onboarding flow.

        Args:
            teacher: Teacher in onboarding
            message_type: Message type
            message_content: Message content

        Returns:
            TeacherFlowResult
        """
        current_step = teacher.conversation_state.get("step")  # type: ignore[union-attr]

        # Handle confirmation step (expects button response)
        if current_step == "CONFIRM_STUDENT_CREATION":
            return await self._confirm_student_creation(teacher, message_type, message_content)

        # Other steps expect text input
        if message_type != "text" or not isinstance(message_content, str):
            # For MVP, only handle text input for non-confirmation steps
            message_id = await self.whatsapp.send_text_message(
                to=teacher.phone, text="Please send a text message."
            )
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=current_step,
                completed=False,
            )

        user_input = message_content.strip()

        # Route to step handler
        if current_step == "COLLECT_SCHOOL":
            return await self._collect_school_name(teacher, user_input)
        elif current_step == "COLLECT_CLASS":
            return await self._collect_class_name(teacher, user_input)
        elif current_step == "COLLECT_STUDENT_COUNT":
            return await self._collect_student_count(teacher, user_input)
        elif current_step == "COLLECT_STUDENT_LIST":
            return await self._collect_student_list(teacher, user_input)
        else:
            # Unknown step - reset
            teacher.conversation_state = None
            await self.db.commit()
            return await self._send_teacher_help(teacher)

    async def _collect_school_name(self, teacher: Teacher, school_name: str) -> TeacherFlowResult:
        """Collect school name and find/create school.

        Now supports invitation codes for school-initiated onboarding.
        If teacher sends invitation code (e.g., "STMARYS-ABC123"), automatically link to school.

        Args:
            teacher: Teacher in onboarding
            school_name: School name OR invitation code provided

        Returns:
            TeacherFlowResult
        """
        import re

        from gapsense.core.models.schools import SchoolInvitation
        from gapsense.engagement.invitation_codes import validate_invitation_code

        # Step 1: Check if input is an invitation code
        # Pattern: SCHOOLCODE-XXX123 (1-8 chars, dash, 6 alphanumeric)
        invitation_code_pattern = r"\b([A-Z0-9]{1,8}-[A-Z0-9]{6})\b"
        code_match = re.search(invitation_code_pattern, school_name.upper())

        if code_match:
            invitation_code = code_match.group(1)

            # Validate format first
            if validate_invitation_code(invitation_code):
                # Validate against database
                stmt = select(SchoolInvitation).where(
                    SchoolInvitation.invitation_code == invitation_code
                )
                result = await self.db.execute(stmt)
                invitation = result.scalar_one_or_none()

                if invitation and invitation.is_active:
                    # Check expiry
                    from datetime import UTC, datetime

                    if invitation.expires_at:
                        try:
                            expires_at = datetime.fromisoformat(invitation.expires_at)
                            if expires_at < datetime.now(UTC):
                                message = (
                                    f"❌ Invitation code {invitation_code} has expired.\n\n"
                                    "Please contact your headmaster for a new code, "
                                    "or send your school name to continue."
                                )
                                message_id = await self.whatsapp.send_text_message(
                                    to=teacher.phone, text=message
                                )
                                return TeacherFlowResult(
                                    flow_name="FLOW-TEACHER-ONBOARD",
                                    message_sent=True,
                                    message_id=message_id,
                                    next_step="COLLECT_SCHOOL",
                                    completed=False,
                                    error="Invitation code expired",
                                )
                        except (ValueError, TypeError):
                            pass  # Invalid date format, continue

                    # Check max teachers limit
                    if (
                        invitation.max_teachers is not None
                        and invitation.teachers_joined >= invitation.max_teachers
                    ):
                        message = (
                            f"❌ Invitation code {invitation_code} has reached its limit.\n\n"
                            "Please contact your headmaster for a new code, "
                            "or send your school name to continue."
                        )
                        message_id = await self.whatsapp.send_text_message(
                            to=teacher.phone, text=message
                        )
                        return TeacherFlowResult(
                            flow_name="FLOW-TEACHER-ONBOARD",
                            message_sent=True,
                            message_id=message_id,
                            next_step="COLLECT_SCHOOL",
                            completed=False,
                            error="Invitation code at max teachers",
                        )

                    # Valid code! Link teacher to school
                    school_stmt = select(School).where(School.id == invitation.school_id)
                    school_result = await self.db.execute(school_stmt)
                    school = school_result.scalar_one_or_none()

                    if school:
                        teacher.school_id = school.id

                        # Increment teachers_joined counter
                        invitation.teachers_joined += 1

                        # Update conversation state
                        teacher.conversation_state["step"] = "COLLECT_CLASS"  # type: ignore[index]
                        teacher.conversation_state["data"]["school_id"] = str(school.id)  # type: ignore[index]
                        teacher.conversation_state["data"]["school_name"] = school.name  # type: ignore[index]
                        teacher.conversation_state["data"]["joined_via_code"] = invitation_code  # type: ignore[index]
                        flag_modified(teacher, "conversation_state")
                        await self.db.commit()

                        # Success message
                        message = (
                            f"✅ Welcome to {school.name}!\n\n"
                            f"You've successfully joined using invitation code {invitation_code}.\n\n"
                            "What class do you teach?\n"
                            "Example: 'JHS 1A' or 'B4'"
                        )

                        message_id = await self.whatsapp.send_text_message(
                            to=teacher.phone, text=message
                        )

                        return TeacherFlowResult(
                            flow_name="FLOW-TEACHER-ONBOARD",
                            message_sent=True,
                            message_id=message_id,
                            next_step="COLLECT_CLASS",
                            completed=False,
                        )

                # Code invalid or not found
                message = (
                    f"❌ Invitation code {invitation_code} is not valid.\n\n"
                    "Please check the code and try again, "
                    "or send your school name to continue."
                )
                message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
                return TeacherFlowResult(
                    flow_name="FLOW-TEACHER-ONBOARD",
                    message_sent=True,
                    message_id=message_id,
                    next_step="COLLECT_SCHOOL",
                    completed=False,
                    error="Invalid invitation code",
                )

        # Step 2: Not an invitation code - proceed with manual school name entry
        # Validate and normalize school name
        try:
            normalized_school_name = validate_school_name(school_name)
        except ValidationError as e:
            message = f"❌ {str(e)}\n\nPlease send your school name again."
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_SCHOOL",
                completed=False,
                error=str(e),
            )

        # For MVP: Create school if doesn't exist
        # TODO: In production, we'd want to search existing schools first
        school_query_stmt = (
            select(School)
            .where(School.name == normalized_school_name)
            .where(School.is_active.is_(True))
        )
        school_query_result = await self.db.execute(school_query_stmt)
        found_school = school_query_result.scalar_one_or_none()

        if not found_school:
            # Create new school (minimal info for MVP)
            # TODO: Would need to link to proper district
            found_school = School(
                name=normalized_school_name,
                district_id=1,  # Default district - TODO: proper district selection
                school_type="jhs",
                is_active=True,
            )
            self.db.add(found_school)
            await self.db.flush()

        # Update teacher with school
        teacher.school_id = found_school.id

        # Update conversation state
        teacher.conversation_state["step"] = "COLLECT_CLASS"  # type: ignore[index]
        teacher.conversation_state["data"]["school_id"] = str(found_school.id)  # type: ignore[index]
        teacher.conversation_state["data"]["school_name"] = normalized_school_name  # type: ignore[index]
        flag_modified(teacher, "conversation_state")
        await self.db.commit()

        # Ask for class name
        message = (
            f"Great! School: {normalized_school_name} ✅\n\n"
            "What class do you teach?\n"
            "Example: 'JHS 1A' or 'B4'"
        )

        message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

        return TeacherFlowResult(
            flow_name="FLOW-TEACHER-ONBOARD",
            message_sent=True,
            message_id=message_id,
            next_step="COLLECT_CLASS",
            completed=False,
        )

    async def _collect_class_name(self, teacher: Teacher, class_name: str) -> TeacherFlowResult:
        """Collect class name.

        Args:
            teacher: Teacher in onboarding
            class_name: Class name provided

        Returns:
            TeacherFlowResult
        """
        # Validate and normalize class name
        try:
            normalized_class_name = validate_class_name(class_name)
        except ValidationError as e:
            message = (
                f"❌ {str(e)}\n\n"
                "Please send your class name again.\n"
                "Examples: 'Basic 7', 'B7', 'JHS 1'"
            )
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_CLASS",
                completed=False,
                error=str(e),
            )

        # Extract grade from class name (e.g., "JHS 1A" -> "JHS1")
        grade = self._extract_grade(normalized_class_name)

        # Update teacher
        teacher.class_name = normalized_class_name
        teacher.grade_taught = grade

        # Update conversation state
        teacher.conversation_state["step"] = "COLLECT_STUDENT_COUNT"  # type: ignore[index]
        teacher.conversation_state["data"]["class_name"] = normalized_class_name  # type: ignore[index]
        teacher.conversation_state["data"]["grade_taught"] = grade  # type: ignore[index]
        flag_modified(teacher, "conversation_state")
        await self.db.commit()

        # Ask for number of students
        message = (
            f"Perfect! Class: {normalized_class_name} ✅\n\n"
            "How many students are in your class?\n"
            "Just send me a number (e.g., '42')"
        )

        message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

        return TeacherFlowResult(
            flow_name="FLOW-TEACHER-ONBOARD",
            message_sent=True,
            message_id=message_id,
            next_step="COLLECT_STUDENT_COUNT",
            completed=False,
        )

    async def _collect_student_count(
        self, teacher: Teacher, student_count_str: str
    ) -> TeacherFlowResult:
        """Collect student count and ask for student list.

        Args:
            teacher: Teacher in onboarding
            student_count_str: Student count as string

        Returns:
            TeacherFlowResult
        """
        # Validate student count
        try:
            student_count = validate_student_count(student_count_str)
        except ValidationError as e:
            message = f"❌ {str(e)}\n\nPlease send a valid number.\n\nHow many students?"
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_STUDENT_COUNT",
                completed=False,
                error=str(e),
            )

        # Update conversation state
        teacher.conversation_state["step"] = "COLLECT_STUDENT_LIST"  # type: ignore[index]
        teacher.conversation_state["data"]["student_count"] = student_count  # type: ignore[index]
        flag_modified(teacher, "conversation_state")
        await self.db.commit()

        # Ask for student names
        message = (
            f"Got it! {student_count} students ✅\n\n"
            "Now, please send me the list of student names.\n\n"
            "You can:\n"
            "• Type them (one per line)\n"
            "• Or send in this format:\n"
            "  1. Kwame Mensah\n"
            "  2. Akosua Boateng\n"
            "  3. Kofi Asante\n"
            "  ...\n\n"
            "Send all names in ONE message."
        )

        message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

        return TeacherFlowResult(
            flow_name="FLOW-TEACHER-ONBOARD",
            message_sent=True,
            message_id=message_id,
            next_step="COLLECT_STUDENT_LIST",
            completed=False,
        )

    async def _collect_student_list(
        self, teacher: Teacher, student_list_text: str
    ) -> TeacherFlowResult:
        """Parse student list and create student profiles.

        Args:
            teacher: Teacher in onboarding
            student_list_text: Text containing student names

        Returns:
            TeacherFlowResult
        """
        # Parse and validate student names
        try:
            student_names = self._parse_student_names(student_list_text)
        except ValidationError as e:
            message = f"❌ {str(e)}\n\nPlease send the student list again."
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_STUDENT_LIST",
                completed=False,
                error=str(e),
            )

        if len(student_names) == 0:
            message = "I couldn't find any names. Please send the student list again."
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_STUDENT_LIST",
                completed=False,
            )

        # Save parsed names to conversation state for confirmation
        teacher.conversation_state["data"]["parsed_names"] = student_names  # type: ignore[index]
        teacher.conversation_state["step"] = "CONFIRM_STUDENT_CREATION"  # type: ignore[index]
        flag_modified(teacher, "conversation_state")
        await self.db.commit()

        # Show preview and ask for confirmation
        try:
            student_list_preview = "\n".join(
                [f"{idx}. {name}" for idx, name in enumerate(student_names, start=1)]
            )

            # Phase D.1: Check for count mismatch
            expected_count = teacher.conversation_state["data"].get("student_count")  # type: ignore[index]
            count_warning = ""
            if expected_count and len(student_names) != expected_count:
                count_warning = (
                    f"\n⚠️ Note: You said {expected_count} students, "
                    f"but I found {len(student_names)} names.\n"
                )

            # Phase D.2: Check for duplicate names
            duplicate_warning = ""
            name_counts: dict[str, int] = {}
            for name in student_names:
                name_lower = name.lower()
                name_counts[name_lower] = name_counts.get(name_lower, 0) + 1

            duplicates = [name for name, count in name_counts.items() if count > 1]
            if duplicates:
                duplicate_list = ", ".join(
                    [f"'{name.title()}' ({name_counts[name]}x)" for name in duplicates]
                )
                duplicate_warning = (
                    f"\n⚠️ Warning: Duplicate names found: {duplicate_list}\n"
                    "Multiple students with the same name is okay, but please confirm.\n"
                )

            message_body = (
                f"I found {len(student_names)} students:\n\n"
                f"{student_list_preview}"
                f"{count_warning}"
                f"{duplicate_warning}\n"
                f"Is this correct?"
            )

            message_id = await self.whatsapp.send_button_message(
                to=teacher.phone,
                body=message_body,
                buttons=[
                    {"id": "confirm_yes", "title": "Yes, create profiles"},
                    {"id": "confirm_no", "title": "No, let me resend"},
                ],
            )

            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="CONFIRM_STUDENT_CREATION",
                completed=False,
            )

        except Exception as e:
            logger.error(
                f"Failed to send confirmation to teacher {teacher.phone}: {e}",
                exc_info=True,
            )

            # Send error message to teacher
            message = (
                "Sorry, there was an error creating student profiles. "
                "Please try sending the student list again, or contact support if this continues."
            )
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_STUDENT_LIST",
                completed=False,
                error=str(e),
            )

    async def _confirm_student_creation(
        self,
        teacher: Teacher,
        message_type: str,
        message_content: str | dict[str, Any],
    ) -> TeacherFlowResult:
        """Handle student creation confirmation (Phase C - confirmation before creating).

        Teacher has provided student list and now must confirm before we create profiles.

        Args:
            teacher: Teacher confirming student creation
            message_type: Message type
            message_content: Message content (should be button response)

        Returns:
            TeacherFlowResult
        """
        # Check for button response
        if message_type != "interactive" or not isinstance(message_content, dict):
            # Invalid input - they need to click a button
            message_id = await self.whatsapp.send_text_message(
                to=teacher.phone,
                text="Please click one of the buttons above to continue.",
            )
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="CONFIRM_STUDENT_CREATION",
                completed=False,
            )

        # Extract button ID
        if "button_reply" in message_content:
            button_reply = message_content.get("button_reply", {})
            button_id = button_reply.get("id")
        else:
            button_id = message_content.get("id")

        # Handle confirmation response
        if button_id == "confirm_no":
            # Teacher declined - go back to student list collection
            teacher.conversation_state["step"] = "COLLECT_STUDENT_LIST"  # type: ignore[index]
            flag_modified(teacher, "conversation_state")
            await self.db.commit()

            message = (
                "No problem! Let's try again.\n\n" "Please send the list of student names again."
            )
            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="COLLECT_STUDENT_LIST",
                completed=False,
            )

        elif button_id == "confirm_yes":
            # Teacher confirmed - create students
            conversation_data = teacher.conversation_state.get("data", {})  # type: ignore[union-attr]
            student_names = conversation_data.get("parsed_names", [])

            if not student_names:
                # Missing student names (shouldn't happen)
                message = "Sorry, something went wrong. Please try sending the student list again."
                message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
                teacher.conversation_state = None
                await self.db.commit()
                return TeacherFlowResult(
                    flow_name="FLOW-TEACHER-ONBOARD",
                    message_sent=True,
                    message_id=message_id,
                    next_step=None,
                    completed=False,
                    error="Missing parsed_names",
                )

            # Create student profiles
            grade = teacher.grade_taught or "JHS1"
            created_students = []

            try:
                for full_name in student_names:
                    # Extract first name (take first word)
                    first_name = full_name.split()[0] if full_name else "Student"

                    student = Student(
                        full_name=full_name,
                        first_name=first_name,
                        current_grade=grade,
                        school_id=teacher.school_id,
                        teacher_id=teacher.id,
                        # NOTE: primary_parent_id will be NULL until parent links
                        is_active=True,
                    )
                    self.db.add(student)
                    created_students.append(full_name)

                # Mark teacher as onboarded
                # NOTE: Teacher.onboarded_at doesn't have DateTime(timezone=True) in model
                # so we use naive datetime for now (TODO: fix in migration)
                teacher.onboarded_at = datetime.now(UTC).replace(tzinfo=None)
                teacher.conversation_state = None  # Clear state - onboarding complete
                await self.db.commit()

            except Exception as e:
                await self.db.rollback()
                logger.error(
                    f"Failed to create students for teacher {teacher.phone}: {e}",
                    exc_info=True,
                    extra={"teacher_id": teacher.id, "student_count": len(student_names)},
                )
                message = (
                    "Sorry, there was an error creating student profiles. "
                    "Please try again or contact support if this continues."
                )
                message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)
                return TeacherFlowResult(
                    flow_name="FLOW-TEACHER-ONBOARD",
                    message_sent=True,
                    message_id=message_id,
                    next_step="COLLECT_STUDENT_LIST",
                    completed=False,
                    error=str(e),
                )

            # Send completion message
            student_list_preview = "\n".join(
                f"  {i+1}. {name}" for i, name in enumerate(created_students[:5])
            )
            if len(created_students) > 5:
                student_list_preview += f"\n  ... and {len(created_students) - 5} more"

            message = (
                f"Perfect! ✅ I've created profiles for all {len(created_students)} students:\n\n"  # nosec B608
                f"{student_list_preview}\n\n"
                "Now share this WhatsApp number with parents at your next PTA meeting "
                "or in your class WhatsApp group.\n\n"
                "When parents message START, I'll ask them to select their child from your class list.\n\n"
                "🎓 You're ready to start using GapSense!\n\n"
                "Next steps:\n"
                "• Share this number with parents\n"
                "• Scan student exercise books (coming soon)\n"
                "• Ask me questions about your class"
            )

            message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=None,
                completed=True,
            )

        else:
            # Unknown button
            message_id = await self.whatsapp.send_text_message(
                to=teacher.phone,
                text="Please select one of the options above.",
            )
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step="CONFIRM_STUDENT_CREATION",
                completed=False,
            )

    def _extract_grade(self, class_name: str) -> str:
        """Extract grade from class name.

        Args:
            class_name: Class name (e.g., "JHS 1A", "B4")

        Returns:
            Grade code (e.g., "JHS1", "B4")
        """
        # Try to extract grade using common patterns
        # Pattern 1: "JHS 1" or "JHS1"
        match = re.search(r"(?:JHS|jhs)\s*(\d)", class_name, re.IGNORECASE)
        if match:
            return f"JHS{match.group(1)}"

        # Pattern 2: "B4", "B5", etc.
        match = re.search(r"B(\d)", class_name, re.IGNORECASE)
        if match:
            return f"B{match.group(1)}"

        # Default: assume JHS1
        return "JHS1"

    def _parse_student_names(self, text: str) -> list[str]:
        """Parse student names from text.

        Handles formats:
        - "1. Name\n2. Name\n..."
        - "Name\nName\nName"
        - "Name, Name, Name"

        Validates and normalizes each name (title case, whitespace normalization).

        Args:
            text: Text containing student names

        Returns:
            List of normalized student names

        Raises:
            ValidationError: If any student name is invalid
        """
        names = []

        # Split by newlines first
        lines = text.strip().split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Remove numbering (e.g., "1. " or "1) " or "1 ")
            line = re.sub(r"^\d+[\.\)]\s*", "", line)
            line = re.sub(r"^\d+\s+", "", line)

            # Split by commas (in case names are comma-separated)
            parts = line.split(",")

            for part in parts:
                part = part.strip()
                if not part:
                    continue

                # Validate and normalize each student name
                try:
                    normalized_name = validate_student_name(part)
                    names.append(normalized_name)
                except ValidationError as e:
                    # Re-raise with context about which name failed
                    raise ValidationError(f"Invalid student name '{part}': {str(e)}") from e

        return names

    async def _send_teacher_help(self, teacher: Teacher) -> TeacherFlowResult:
        """Send help message to teacher.

        Args:
            teacher: Teacher requesting help

        Returns:
            TeacherFlowResult
        """
        message = (
            "Welcome to GapSense! 👋\n\n"
            "I'm your AI teaching assistant for diagnosing student gaps.\n\n"
            "To get started, send: START\n\n"
            "Questions? Just ask me anything!"
        )

        message_id = await self.whatsapp.send_text_message(to=teacher.phone, text=message)

        return TeacherFlowResult(
            flow_name="HELP",
            message_sent=True,
            message_id=message_id,
            next_step=None,
            completed=True,
        )

    async def _handle_teacher_command(
        self, teacher: Teacher, command_text: str
    ) -> TeacherFlowResult:
        """Handle error recovery commands (RESTART, CANCEL, HELP, STATUS).

        Args:
            teacher: Teacher instance
            command_text: Command text

        Returns:
            TeacherFlowResult for command handling
        """
        current_state = teacher.conversation_state or {}
        has_active_flow = current_state.get("flow") is not None
        current_step = current_state.get("step")

        # Handle the command
        cmd_result = handle_command(command_text, has_active_flow, current_step)

        if not cmd_result.handled:
            # Not a recognized command - let it flow through normal processing
            return TeacherFlowResult(
                flow_name="COMMAND",
                message_sent=False,
                message_id=None,
                next_step=None,
                completed=False,
                error="Command not recognized",
            )

        # Clear conversation state if requested
        if cmd_result.clear_state:
            teacher.conversation_state = None
            await self.db.commit()

        # Send response message if provided
        if cmd_result.message:
            try:
                message_id = await self.whatsapp.send_text_message(
                    to=teacher.phone, text=cmd_result.message
                )

                return TeacherFlowResult(
                    flow_name="COMMAND",
                    message_sent=True,
                    message_id=message_id,
                    next_step=None,
                    completed=True,
                    error=None,
                )
            except Exception as e:
                logger.error(f"Failed to send command response to {teacher.phone}: {e}")
                return TeacherFlowResult(
                    flow_name="COMMAND",
                    message_sent=False,
                    message_id=None,
                    next_step=None,
                    completed=True,
                    error=str(e),
                )

        return TeacherFlowResult(
            flow_name="COMMAND",
            message_sent=False,
            message_id=None,
            next_step=None,
            completed=True,
            error=None,
        )

    async def _check_session_expiry(self, teacher: Teacher) -> None:
        """Check if conversation session has expired (Phase D.5).

        If session expired (> 24 hours since last activity), clear conversation state.

        Args:
            teacher: Teacher instance
        """
        if not teacher.conversation_state:
            # No active conversation, nothing to expire
            return

        if not teacher.last_active_at:
            # No timestamp, can't check expiry
            return

        # Convert both to UTC for comparison
        now_utc = datetime.now(UTC).replace(tzinfo=None)  # Make naive for comparison
        time_since_last_activity = now_utc - teacher.last_active_at

        # Session expires after 24 hours
        if time_since_last_activity > timedelta(hours=24):
            logger.info(
                f"Session expired for teacher {teacher.phone} "
                f"(last active {time_since_last_activity.total_seconds() / 3600:.1f}h ago)"
            )
            teacher.conversation_state = None
            await self.db.commit()

    async def _update_session_tracking(self, teacher: Teacher) -> None:
        """Update session tracking.

        Args:
            teacher: Teacher instance
        """
        # NOTE: Teacher.last_active_at expects timezone-naive datetime
        now_naive = datetime.now(UTC).replace(tzinfo=None)
        teacher.last_active_at = now_naive
        await self.db.commit()
