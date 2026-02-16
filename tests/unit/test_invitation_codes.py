"""
Tests for school invitation code generation and validation.

TDD approach: Tests written first to define expected behavior.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.gapsense.engagement.invitation_codes import (
    InvitationCodeError,
    generate_invitation_code,
    generate_school_code_prefix,
    validate_invitation_code,
    validate_invitation_code_db,
)


class TestGenerateSchoolCodePrefix:
    """Tests for generating school code prefix from school name."""

    def test_simple_school_name(self):
        """Generate code from simple school name."""
        name = "St. Mary's JHS"
        code = generate_school_code_prefix(name)
        assert code == "STMARYS"

    def test_long_school_name_truncated(self):
        """Truncate long school names to max 8 characters."""
        name = "Abakrampa Senior High Technical School"
        code = generate_school_code_prefix(name)
        assert len(code) <= 8
        assert code == "ABAKRAMP"

    def test_removes_special_characters(self):
        """Remove apostrophes, hyphens, and other special chars."""
        name = "Wesley Girls' High-Tech School"
        code = generate_school_code_prefix(name)
        assert "'" not in code
        assert "-" not in code
        assert code == "WESLEYGI"

    def test_removes_common_words(self):
        """Remove common words like 'School', 'High', 'JHS'."""
        name = "Wesley Girls High School"
        code = generate_school_code_prefix(name)
        assert code == "WESLEYGI"  # Removes 'High' and 'School'

    def test_handles_primary_schools(self):
        """Generate code for primary schools."""
        name = "Accra Primary School"
        code = generate_school_code_prefix(name)
        assert code == "ACCRA"

    def test_handles_jhs_schools(self):
        """Generate code for JHS schools."""
        name = "Kumasi JHS"
        code = generate_school_code_prefix(name)
        assert code == "KUMASI"

    def test_handles_empty_after_filtering(self):
        """Handle edge case where name becomes empty after filtering."""
        name = "High School"
        code = generate_school_code_prefix(name)
        assert code == "HS"  # Fallback to initials

    def test_all_uppercase_output(self):
        """Output is always uppercase."""
        name = "accra primary school"
        code = generate_school_code_prefix(name)
        assert code == "ACCRA"
        assert code.isupper()


class TestGenerateInvitationCode:
    """Tests for generating complete invitation codes."""

    @pytest.mark.asyncio
    async def test_generate_code_format(self):
        """Generate code with format SCHOOLCODE-XXX123."""
        school_name = "St. Mary's JHS"
        code = await generate_invitation_code(school_name)

        # Should match pattern: STMARYS-XXX123
        assert code.startswith("STMARYS-")
        suffix = code.split("-")[1]
        assert len(suffix) == 6  # 3 letters + 3 numbers
        assert suffix[:3].isalpha()
        assert suffix[3:].isdigit()

    @pytest.mark.asyncio
    async def test_generates_unique_codes(self):
        """Generate unique codes for same school name."""
        school_name = "Wesley Girls High"

        code1 = await generate_invitation_code(school_name)
        code2 = await generate_invitation_code(school_name)

        assert code1 != code2
        assert code1.split("-")[0] == code2.split("-")[0]  # Same prefix

    @pytest.mark.asyncio
    async def test_checks_database_for_uniqueness(self):
        """Check database to ensure code doesn't already exist."""
        school_name = "Accra JHS"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            # Mock database to return existing code on first try
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar_one_or_none.side_effect = [
                Mock(),  # First try: code exists
                None,  # Second try: code doesn't exist
            ]
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            await generate_invitation_code(school_name)

            # Should have tried twice (once found duplicate, second time succeeded)
            assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_error_after_max_retries(self):
        """Raise error if can't generate unique code after max retries."""
        school_name = "Test School"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            # Mock database to always return existing code
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = Mock()  # Always exists
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            with pytest.raises(InvitationCodeError, match="Could not generate unique code"):
                await generate_invitation_code(school_name, max_retries=3)


class TestValidateInvitationCode:
    """Tests for validating invitation codes."""

    @pytest.mark.asyncio
    async def test_valid_code_format(self):
        """Accept valid code format."""
        code = "STMARYS-ABC123"
        is_valid = validate_invitation_code(code)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_invalid_format_no_dash(self):
        """Reject code without dash separator."""
        code = "STMARYSABC123"
        is_valid = validate_invitation_code(code)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_invalid_format_wrong_suffix_length(self):
        """Reject code with wrong suffix length."""
        code = "STMARYS-AB12"  # Only 4 chars in suffix
        is_valid = validate_invitation_code(code)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_invalid_format_suffix_not_alphanumeric(self):
        """Reject code with special characters in suffix."""
        code = "STMARYS-ABC-23"
        is_valid = validate_invitation_code(code)
        assert is_valid is False

    @pytest.mark.asyncio
    async def test_case_insensitive_validation(self):
        """Accept lowercase codes (normalize to uppercase)."""
        code = "stmarys-abc123"
        is_valid = validate_invitation_code(code)
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_checks_code_exists_in_database(self):
        """Verify code exists in database."""
        code = "WESLEY-XYZ789"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.scalar_one_or_none.return_value = None  # Code doesn't exist
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            is_valid = await validate_invitation_code_db(code)
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_checks_code_is_active(self):
        """Verify code is active (not disabled)."""
        code = "WESLEY-XYZ789"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_invitation = Mock()
            mock_invitation.is_active = False  # Code is disabled
            mock_result.scalar_one_or_none.return_value = mock_invitation
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            is_valid = await validate_invitation_code_db(code)
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_checks_code_not_expired(self):
        """Verify code hasn't expired."""
        code = "WESLEY-XYZ789"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_invitation = Mock()
            mock_invitation.is_active = True
            # Expired yesterday
            mock_invitation.expires_at = (datetime.now(UTC) - timedelta(days=1)).isoformat()
            mock_result.scalar_one_or_none.return_value = mock_invitation
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            is_valid = await validate_invitation_code_db(code)
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_checks_max_teachers_not_reached(self):
        """Verify code hasn't reached max teachers limit."""
        code = "WESLEY-XYZ789"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_invitation = Mock()
            mock_invitation.is_active = True
            mock_invitation.expires_at = None
            mock_invitation.max_teachers = 5
            mock_invitation.teachers_joined = 5  # At limit
            mock_result.scalar_one_or_none.return_value = mock_invitation
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            is_valid = await validate_invitation_code_db(code)
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_allows_unlimited_teachers_when_max_is_none(self):
        """Allow unlimited teachers when max_teachers is None."""
        code = "WESLEY-XYZ789"

        with patch("src.gapsense.engagement.invitation_codes.get_db") as mock_db:
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_invitation = Mock()
            mock_invitation.is_active = True
            mock_invitation.expires_at = None
            mock_invitation.max_teachers = None  # Unlimited
            mock_invitation.teachers_joined = 100  # Any number
            mock_result.scalar_one_or_none.return_value = mock_invitation
            mock_session.execute.return_value = mock_result
            mock_db.return_value.__aiter__.return_value = [mock_session]

            is_valid = await validate_invitation_code_db(code)
            assert is_valid is True
