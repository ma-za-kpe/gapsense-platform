"""
Command handling for WhatsApp flows.

Implements error recovery commands: RESTART, CANCEL, HELP, STATUS

Phase B of TDD implementation plan.
"""

from dataclasses import dataclass


@dataclass
class CommandResult:
    """Result of processing a command."""

    handled: bool
    message: str | None = None
    clear_state: bool = False


# List of reserved command keywords
RESERVED_COMMANDS = ["RESTART", "CANCEL", "HELP", "STATUS", "START", "STOP"]


def is_command(message: str) -> bool:
    """
    Check if a message is a command.

    Args:
        message: Message text

    Returns:
        True if message is a command
    """
    normalized = message.strip().upper()
    return normalized in RESERVED_COMMANDS


def handle_command(
    message: str, has_active_flow: bool, current_step: str | None = None
) -> CommandResult:
    """
    Handle a command message.

    Args:
        message: Command text
        has_active_flow: Whether user has an active conversation flow
        current_step: Current step in the flow (if active)

    Returns:
        CommandResult with handling instructions
    """
    command = message.strip().upper()

    if command == "RESTART":
        return _handle_restart()

    elif command == "CANCEL":
        return _handle_cancel(has_active_flow)

    elif command == "HELP":
        return _handle_help(has_active_flow, current_step)

    elif command == "STATUS":
        return _handle_status(has_active_flow, current_step)

    else:
        return CommandResult(handled=False)


def _handle_restart() -> CommandResult:
    """Handle RESTART command - clear state and start fresh."""
    message = (
        "🔄 Restarting...\n\n"
        "Your progress has been cleared.\n\n"
        "Send START to begin onboarding."
    )
    return CommandResult(handled=True, message=message, clear_state=True)


def _handle_cancel(has_active_flow: bool) -> CommandResult:
    """Handle CANCEL command - cancel current operation."""
    if not has_active_flow:
        message = "Nothing to cancel right now.\n\n" "Send START if you'd like to begin onboarding."
        return CommandResult(handled=True, message=message, clear_state=False)

    message = (
        "✅ Cancelled.\n\n"
        "Your progress has been cleared.\n\n"
        "Send START to begin again, or HELP for more options."
    )
    return CommandResult(handled=True, message=message, clear_state=True)


def _handle_help(has_active_flow: bool, current_step: str | None) -> CommandResult:
    """Handle HELP command - show context-specific help."""
    base_message = "📖 **Available Commands:**\n\n"
    commands = [
        "• START - Begin onboarding",
        "• RESTART - Clear progress and start over",
        "• CANCEL - Cancel current operation",
        "• STATUS - Show your current progress",
        "• HELP - Show this message",
    ]

    # Add context-specific help
    if has_active_flow and current_step:
        step_help = _get_step_help(current_step)
        if step_help:
            message = (
                f"📍 **You are currently:** {step_help}\n\n"
                f"{base_message}{chr(10).join(commands)}\n\n"
                "Need to start over? Send RESTART"
            )
        else:
            message = f"{base_message}{chr(10).join(commands)}"
    else:
        message = f"{base_message}{chr(10).join(commands)}\n\nSend START to begin!"

    return CommandResult(handled=True, message=message, clear_state=False)


def _handle_status(has_active_flow: bool, current_step: str | None) -> CommandResult:
    """Handle STATUS command - show current progress."""
    if not has_active_flow:
        message = "📊 **Status:** No active flow\n\nSend START to begin onboarding."
        return CommandResult(handled=True, message=message, clear_state=False)

    # Map steps to progress messages
    step_info = _get_step_info(current_step)
    if step_info:
        message = f"📊 **Status:** {step_info}\n\nSend HELP for available commands."
    else:
        message = (
            "📊 **Status:** Onboarding in progress\n\n"
            "Send HELP for available commands or RESTART to start over."
        )

    return CommandResult(handled=True, message=message, clear_state=False)


def _get_step_help(step: str) -> str | None:
    """Get context-specific help for a step."""
    step_help_map = {
        "AWAITING_OPT_IN": "Waiting for you to opt in to GapSense",
        "AWAITING_STUDENT_SELECTION": "Selecting your child from the list",
        "AWAITING_DIAGNOSTIC_CONSENT": "Providing consent for diagnostic questions",
        "AWAITING_LANGUAGE": "Selecting your preferred language",
        "COLLECT_SCHOOL": "Collecting your school name",
        "COLLECT_CLASS": "Collecting your class name",
        "COLLECT_STUDENT_COUNT": "Collecting number of students",
        "COLLECT_STUDENT_LIST": "Collecting student names",
    }
    return step_help_map.get(step)


def _get_step_info(step: str | None) -> str | None:
    """Get status info for a step."""
    if not step:
        return None

    step_info_map = {
        "AWAITING_OPT_IN": "Onboarding - Step 1 of 4 (Opt-in)",
        "AWAITING_STUDENT_SELECTION": "Onboarding - Step 2 of 4 (Select child)",
        "AWAITING_DIAGNOSTIC_CONSENT": "Onboarding - Step 3 of 4 (Diagnostic consent)",
        "AWAITING_LANGUAGE": "Onboarding - Step 4 of 4 (Language preference)",
        "COLLECT_SCHOOL": "Teacher Onboarding - Step 1 of 4 (School name)",
        "COLLECT_CLASS": "Teacher Onboarding - Step 2 of 4 (Class name)",
        "COLLECT_STUDENT_COUNT": "Teacher Onboarding - Step 3 of 4 (Student count)",
        "COLLECT_STUDENT_LIST": "Teacher Onboarding - Step 4 of 4 (Student names)",
    }
    return step_info_map.get(step, "In progress...")
