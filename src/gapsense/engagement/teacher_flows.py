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
from datetime import UTC, datetime
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
        if message_type != "text" or not isinstance(message_content, str):
            # For MVP, only handle text input
            message_id = await self.whatsapp.send_text_message(
                to=teacher.phone, text="Please send a text message."
            )
            return TeacherFlowResult(
                flow_name="FLOW-TEACHER-ONBOARD",
                message_sent=True,
                message_id=message_id,
                next_step=teacher.conversation_state.get("step"),  # type: ignore[union-attr]
                completed=False,
            )

        current_step = teacher.conversation_state.get("step")  # type: ignore[union-attr]
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

        Args:
            teacher: Teacher in onboarding
            school_name: School name provided

        Returns:
            TeacherFlowResult
        """
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
        stmt = (
            select(School)
            .where(School.name == normalized_school_name)
            .where(School.is_active.is_(True))
        )
        result = await self.db.execute(stmt)
        school = result.scalar_one_or_none()

        if not school:
            # Create new school (minimal info for MVP)
            # TODO: Would need to link to proper district
            school = School(
                name=normalized_school_name,
                district_id=1,  # Default district - TODO: proper district selection
                school_type="jhs",
                is_active=True,
            )
            self.db.add(school)
            await self.db.flush()

        # Update teacher with school
        teacher.school_id = school.id

        # Update conversation state
        teacher.conversation_state["step"] = "COLLECT_CLASS"  # type: ignore[index]
        teacher.conversation_state["data"]["school_id"] = str(school.id)  # type: ignore[index]
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

        # Create student profiles
        grade = teacher.grade_taught or "JHS1"
        created_students = []

        try:
            for full_name in student_names:
                # Extract first name (take first word)
                first_name = full_name.split()[0] if full_name else "Student"

                student = Student(
                    full_name=full_name,  # Complete name from register (for parent selection)
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
            teacher.onboarded_at = datetime.now(UTC)
            teacher.conversation_state = None  # Clear state - onboarding complete
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to create students for teacher {teacher.phone}: {e}",
                exc_info=True,
                extra={"teacher_id": teacher.id, "student_count": len(student_names)},
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

        # Send completion message
        student_list_preview = "\n".join(
            f"  {i+1}. {name}" for i, name in enumerate(created_students[:5])
        )
        if len(created_students) > 5:
            student_list_preview += f"\n  ... and {len(created_students) - 5} more"

        message = (
            f"Perfect! ✅ I've created profiles for all {len(created_students)} students:\n\n"
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
