"""
School invitation code generation and validation.

Invitation codes follow format: SCHOOLCODE-XXX123
- SCHOOLCODE: 1-8 char prefix from school name
- XXX123: 3 random letters + 3 random digits
"""

import random
import re
import string
from datetime import UTC, datetime

from sqlalchemy import select

from gapsense.core.database import get_db
from gapsense.core.models.schools import SchoolInvitation


class InvitationCodeError(Exception):
    """Error raised when invitation code operations fail."""

    pass


def generate_school_code_prefix(school_name: str, max_length: int = 8) -> str:
    """Generate school code prefix from school name.

    Args:
        school_name: Full school name (e.g., "St. Mary's JHS")
        max_length: Maximum length of prefix (default: 8)

    Returns:
        Uppercase alphanumeric code (e.g., "STMARYS")

    Examples:
        >>> generate_school_code_prefix("St. Mary's JHS")
        'STMARYS'
        >>> generate_school_code_prefix("Abakrampa Senior High Technical School")
        'ABAKRAMP'
    """
    # Remove common school-related words (but keep identifying words like "Girls", "Boys")
    common_words = {
        "school",
        "high",
        "jhs",
        "primary",
        "junior",
        "senior",
        "technical",
        "tech",
    }

    # Convert to uppercase and remove special characters
    name = school_name.upper()
    name = re.sub(r"[^A-Z0-9\s]", "", name)

    # Split into words and filter out common words
    words = name.split()
    filtered_words = [w for w in words if w.lower() not in common_words]

    # If nothing left after filtering, use initials of original words
    code = "".join(w[0] for w in words if w) if not filtered_words else "".join(filtered_words)

    # Truncate to max length
    return code[:max_length]


async def generate_invitation_code(school_name: str, max_retries: int = 10) -> str:
    """Generate unique invitation code for school.

    Args:
        school_name: School name to generate code for
        max_retries: Maximum attempts to generate unique code

    Returns:
        Unique invitation code (e.g., "STMARYS-ABC123")

    Raises:
        InvitationCodeError: If unable to generate unique code
    """
    prefix = generate_school_code_prefix(school_name)

    for _attempt in range(max_retries):
        # Generate random suffix: 3 letters + 3 digits
        letters = "".join(random.choices(string.ascii_uppercase, k=3))
        digits = "".join(random.choices(string.digits, k=3))
        suffix = f"{letters}{digits}"

        code = f"{prefix}-{suffix}"

        # Check if code already exists in database
        async for db in get_db():
            stmt = select(SchoolInvitation).where(SchoolInvitation.invitation_code == code)
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            if not existing:
                return code

    raise InvitationCodeError(
        f"Could not generate unique code for {school_name} after {max_retries} attempts"
    )


def validate_invitation_code(code: str, check_db: bool = False) -> bool:
    """Validate invitation code format.

    Args:
        code: Invitation code to validate
        check_db: Whether to check database for existence (async)

    Returns:
        True if code format is valid, False otherwise

    Examples:
        >>> validate_invitation_code("STMARYS-ABC123")
        True
        >>> validate_invitation_code("INVALID")
        False
    """
    # Normalize to uppercase
    code = code.upper()

    # Check format: PREFIX-XXX123
    if "-" not in code:
        return False

    parts = code.split("-")
    if len(parts) != 2:
        return False

    prefix, suffix = parts

    # Prefix: 1-8 uppercase alphanumeric characters
    if not prefix or len(prefix) > 8:
        return False
    if not re.match(r"^[A-Z0-9]+$", prefix):
        return False

    # Suffix: exactly 6 alphanumeric characters
    if len(suffix) != 6:
        return False

    return bool(re.match(r"^[A-Z0-9]+$", suffix))


async def validate_invitation_code_db(code: str) -> bool:
    """Validate invitation code against database.

    Checks:
    - Code exists in database
    - Code is active
    - Code hasn't expired
    - Code hasn't reached max teachers limit

    Args:
        code: Invitation code to validate

    Returns:
        True if code is valid and can be used, False otherwise
    """
    # First check format
    if not validate_invitation_code(code):
        return False

    code = code.upper()

    # Check database
    async for db in get_db():
        stmt = select(SchoolInvitation).where(SchoolInvitation.invitation_code == code)
        result = await db.execute(stmt)
        invitation = result.scalar_one_or_none()

        # Code doesn't exist
        if not invitation:
            return False

        # Code is inactive
        if not invitation.is_active:
            return False

        # Code has expired
        if invitation.expires_at:
            try:
                expires_at = datetime.fromisoformat(invitation.expires_at)
                if expires_at < datetime.now(UTC):
                    return False
            except (ValueError, TypeError):
                # Invalid date format, consider expired
                return False

        # Check max teachers limit
        return not (
            invitation.max_teachers is not None
            and invitation.teachers_joined >= invitation.max_teachers
        )

    return False
