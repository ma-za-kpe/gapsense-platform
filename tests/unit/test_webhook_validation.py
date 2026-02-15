"""
Tests for WhatsApp Webhook Input Validation

Tests phone number validation and error handling.
"""

import pytest

from gapsense.webhooks.whatsapp import _validate_phone


class TestPhoneValidation:
    """Test phone number validation."""

    def test_valid_phone_e164_format(self) -> None:
        """Test valid E.164 phone number."""
        assert _validate_phone("+233501234567") == "+233501234567"
        assert _validate_phone("+12125551234") == "+12125551234"
        assert _validate_phone("+447700900000") == "+447700900000"

    def test_valid_phone_with_whitespace(self) -> None:
        """Test phone number with leading/trailing whitespace."""
        assert _validate_phone("  +233501234567  ") == "+233501234567"
        assert _validate_phone("\t+233501234567\n") == "+233501234567"

    def test_invalid_phone_missing_plus(self) -> None:
        """Test phone number without + prefix."""
        with pytest.raises(ValueError, match="must start with \\+"):
            _validate_phone("233501234567")

    def test_invalid_phone_empty(self) -> None:
        """Test empty phone number."""
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_phone("")
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_phone("   ")

    def test_invalid_phone_too_short(self) -> None:
        """Test phone number too short."""
        with pytest.raises(ValueError, match="length invalid"):
            _validate_phone("+123")  # Only 4 chars

    def test_invalid_phone_too_long(self) -> None:
        """Test phone number too long."""
        with pytest.raises(ValueError, match="length invalid"):
            _validate_phone("+" + "1" * 25)  # 26 chars

    def test_invalid_phone_non_numeric(self) -> None:
        """Test phone number with non-numeric characters."""
        with pytest.raises(ValueError, match="must contain only digits"):
            _validate_phone("+233-501-234-567")
        with pytest.raises(ValueError, match="must contain only digits"):
            _validate_phone("+233 501 234 567")
        with pytest.raises(ValueError, match="must contain only digits"):
            _validate_phone("+233abc123456")

    def test_invalid_phone_sql_injection_attempt(self) -> None:
        """Test SQL injection attempt is rejected."""
        with pytest.raises(ValueError, match="must start with \\+"):
            _validate_phone("' OR 1=1--")
        # SQL injection with special chars caught by length or digit checks
        with pytest.raises(ValueError):  # Will fail length or digit check
            _validate_phone("+233'; DROP TABLE parents;--")

    def test_invalid_phone_xss_attempt(self) -> None:
        """Test XSS attempt is rejected."""
        with pytest.raises(ValueError, match="must start with \\+"):
            _validate_phone("<script>alert('xss')</script>")
        with pytest.raises(ValueError, match="must contain only digits"):
            _validate_phone("+233<script>")

    def test_edge_case_minimum_length(self) -> None:
        """Test minimum valid length (8 chars)."""
        assert _validate_phone("+1234567") == "+1234567"  # 8 chars

    def test_edge_case_maximum_length(self) -> None:
        """Test maximum valid length (20 chars)."""
        assert _validate_phone("+" + "1" * 19) == "+" + "1" * 19  # 20 chars
