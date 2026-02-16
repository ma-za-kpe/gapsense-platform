"""
Unit tests for input validation functions.

Tests follow TDD approach: write failing tests first, then implement.
"""

import pytest

from gapsense.core.validation import (
    ValidationError,
    validate_class_name,
    validate_phone_number,
    validate_school_name,
    validate_student_count,
    validate_student_name,
)

# ============================================================================
# Phase A.1: Phone Number Validation
# ============================================================================


class TestPhoneValidation:
    """Tests for phone number validation."""

    def test_valid_ghana_phone_number_with_plus(self):
        """Should accept valid Ghana phone number with + prefix."""
        assert validate_phone_number("+233501234567") == "+233501234567"

    def test_valid_ghana_phone_number_with_zero(self):
        """Should accept valid Ghana phone number with 0 prefix."""
        # 0501234567 → +233501234567
        assert validate_phone_number("0501234567") == "+233501234567"

    def test_normalize_spaces(self):
        """Should normalize phone numbers with spaces."""
        assert validate_phone_number("+233 50 123 4567") == "+233501234567"
        assert validate_phone_number("0 50 123 4567") == "+233501234567"

    def test_normalize_dashes(self):
        """Should normalize phone numbers with dashes."""
        assert validate_phone_number("+233-50-123-4567") == "+233501234567"

    def test_reject_invalid_format(self):
        """Should reject obviously invalid formats."""
        with pytest.raises(ValidationError, match="Invalid phone number format"):
            validate_phone_number("abc123")

    def test_reject_too_short(self):
        """Should reject numbers that are too short."""
        with pytest.raises(ValidationError, match="Invalid phone number"):
            validate_phone_number("+23350123")

    def test_reject_too_long(self):
        """Should reject numbers that are too long."""
        with pytest.raises(ValidationError, match="Invalid phone number"):
            validate_phone_number("+2335012345678901234")

    def test_reject_non_ghana_country_code(self):
        """Should reject non-Ghana country codes."""
        with pytest.raises(ValidationError, match="Only Ghana phone numbers"):
            validate_phone_number("+1234567890")

    def test_reject_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValidationError, match="Phone number cannot be empty"):
            validate_phone_number("")

    def test_reject_none(self):
        """Should reject None values."""
        with pytest.raises(ValidationError, match="Phone number cannot be empty"):
            validate_phone_number(None)


# ============================================================================
# Phase A.2: School Name Validation
# ============================================================================


class TestSchoolNameValidation:
    """Tests for school name validation."""

    def test_valid_school_name(self):
        """Should accept valid school names."""
        assert validate_school_name("St. Mary's JHS, Accra") == "St. Mary's JHS, Accra"

    def test_normalize_whitespace(self):
        """Should normalize multiple spaces to single space."""
        assert validate_school_name("St.  Mary's   JHS") == "St. Mary's JHS"

    def test_strip_leading_trailing_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert validate_school_name("  St. Mary's JHS  ") == "St. Mary's JHS"

    def test_reject_too_short(self):
        """Should reject school names that are too short."""
        with pytest.raises(ValidationError, match="School name must be at least"):
            validate_school_name("AB")

    def test_reject_too_long(self):
        """Should reject school names that are too long."""
        long_name = "A" * 201
        with pytest.raises(ValidationError, match="School name cannot exceed"):
            validate_school_name(long_name)

    def test_reject_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValidationError, match="School name cannot be empty"):
            validate_school_name("")

    def test_reject_whitespace_only(self):
        """Should reject strings with only whitespace."""
        with pytest.raises(ValidationError, match="School name cannot be empty"):
            validate_school_name("   ")

    def test_reject_numbers_only(self):
        """Should reject school names with only numbers."""
        with pytest.raises(ValidationError, match="School name must contain letters"):
            validate_school_name("12345")


# ============================================================================
# Phase A.3: Class Name Validation
# ============================================================================


class TestClassNameValidation:
    """Tests for class name validation."""

    def test_valid_class_name_basic_7(self):
        """Should accept Basic 7 format."""
        assert validate_class_name("Basic 7") == "Basic 7"

    def test_valid_class_name_b7(self):
        """Should accept B7 format."""
        assert validate_class_name("B7") == "B7"

    def test_valid_class_name_jhs_1(self):
        """Should accept JHS 1 format."""
        assert validate_class_name("JHS 1") == "JHS 1"

    def test_normalize_case(self):
        """Should normalize case to title case."""
        assert validate_class_name("basic 7") == "Basic 7"
        assert validate_class_name("BASIC 7") == "Basic 7"

    def test_normalize_whitespace(self):
        """Should normalize whitespace."""
        assert validate_class_name("Basic  7") == "Basic 7"

    def test_reject_invalid_grade_level(self):
        """Should reject invalid grade levels."""
        with pytest.raises(ValidationError, match="Invalid grade level"):
            validate_class_name("Basic 15")

    def test_reject_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValidationError, match="Class name cannot be empty"):
            validate_class_name("")


# ============================================================================
# Phase A.4: Student Count Validation
# ============================================================================


class TestStudentCountValidation:
    """Tests for student count validation."""

    def test_valid_student_count_as_int(self):
        """Should accept valid student count as integer."""
        assert validate_student_count(25) == 25

    def test_valid_student_count_as_string(self):
        """Should accept valid student count as string."""
        assert validate_student_count("25") == 25

    def test_reject_negative_count(self):
        """Should reject negative student counts."""
        with pytest.raises(ValidationError, match="Student count must be positive"):
            validate_student_count(-5)

    def test_reject_zero_count(self):
        """Should reject zero student count."""
        with pytest.raises(ValidationError, match="Student count must be positive"):
            validate_student_count(0)

    def test_reject_too_large_count(self):
        """Should reject unreasonably large student counts."""
        with pytest.raises(ValidationError, match="Student count cannot exceed"):
            validate_student_count(1000)

    def test_reject_non_numeric_string(self):
        """Should reject non-numeric strings."""
        with pytest.raises(ValidationError, match="Student count must be a number"):
            validate_student_count("twenty")

    def test_warn_if_very_small(self):
        """Should warn if count is suspiciously small."""
        # Should pass but might want to log warning
        assert validate_student_count(1) == 1


# ============================================================================
# Phase A.5: Student Name Validation
# ============================================================================


class TestStudentNameValidation:
    """Tests for student name validation."""

    def test_valid_single_name(self):
        """Should accept single name."""
        assert validate_student_name("Kwame") == "Kwame"

    def test_valid_full_name(self):
        """Should accept full name."""
        assert validate_student_name("Kwame Mensah") == "Kwame Mensah"

    def test_normalize_whitespace(self):
        """Should normalize multiple spaces to single space."""
        assert validate_student_name("Kwame  Mensah") == "Kwame Mensah"

    def test_strip_leading_trailing_whitespace(self):
        """Should strip leading and trailing whitespace."""
        assert validate_student_name("  Kwame  ") == "Kwame"

    def test_normalize_case_to_title_case(self):
        """Should normalize to title case."""
        assert validate_student_name("kwame mensah") == "Kwame Mensah"
        assert validate_student_name("KWAME MENSAH") == "Kwame Mensah"

    def test_strip_numbering(self):
        """Should strip numbering prefix."""
        assert validate_student_name("1. Kwame") == "Kwame"
        assert validate_student_name("42. Ama Serwaa") == "Ama Serwaa"

    def test_reject_too_short(self):
        """Should reject names that are too short."""
        with pytest.raises(ValidationError, match="Student name must be at least"):
            validate_student_name("K")

    def test_reject_too_long(self):
        """Should reject names that are too long."""
        long_name = "A" * 101
        with pytest.raises(ValidationError, match="Student name cannot exceed"):
            validate_student_name(long_name)

    def test_reject_empty_string(self):
        """Should reject empty strings."""
        with pytest.raises(ValidationError, match="Student name cannot be empty"):
            validate_student_name("")

    def test_reject_numbers_only(self):
        """Should reject names with only numbers."""
        with pytest.raises(ValidationError, match="Student name must contain letters"):
            validate_student_name("123")

    def test_reject_special_characters_only(self):
        """Should reject names with only special characters."""
        with pytest.raises(ValidationError, match="Student name must contain letters"):
            validate_student_name("!@#$")
