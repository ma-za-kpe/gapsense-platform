"""
Unit Tests for GapSense Exception Hierarchy

Tests for exception class relationships and inheritance structure.
Requirements: 5.1, 5.2, 5.3
"""

import pytest

from gapsense.core.exceptions import (
    AIClientError,
    CurriculumDataError,
    GapSenseError,
    MediaDownloadError,
    PermanentError,
    RetryableError,
    StudentNotFoundError,
)


class TestExceptionHierarchy:
    """Test exception inheritance relationships."""

    def test_retryable_error_is_gapsense_error(self):
        """RetryableError should inherit from GapSenseError."""
        error = RetryableError("transient failure")
        assert isinstance(error, GapSenseError)
        assert isinstance(error, Exception)

    def test_permanent_error_is_gapsense_error(self):
        """PermanentError should inherit from GapSenseError."""
        error = PermanentError("non-recoverable failure")
        assert isinstance(error, GapSenseError)
        assert isinstance(error, Exception)

    def test_student_not_found_error_is_permanent_and_gapsense(self):
        """StudentNotFoundError should inherit from both PermanentError and GapSenseError."""
        error = StudentNotFoundError("student 123 not found")
        assert isinstance(error, PermanentError)
        assert isinstance(error, GapSenseError)
        assert isinstance(error, Exception)

    def test_curriculum_data_error_is_permanent_and_gapsense(self):
        """CurriculumDataError should inherit from both PermanentError and GapSenseError."""
        error = CurriculumDataError("missing curriculum graph")
        assert isinstance(error, PermanentError)
        assert isinstance(error, GapSenseError)
        assert isinstance(error, Exception)

    def test_media_download_error_is_retryable_and_gapsense(self):
        """MediaDownloadError should inherit from both RetryableError and GapSenseError."""
        error = MediaDownloadError("S3 timeout")
        assert isinstance(error, RetryableError)
        assert isinstance(error, GapSenseError)
        assert isinstance(error, Exception)

    def test_ai_client_error_is_retryable_and_gapsense(self):
        """AIClientError should inherit from both RetryableError and GapSenseError."""
        error = AIClientError("rate limit exceeded")
        assert isinstance(error, RetryableError)
        assert isinstance(error, GapSenseError)
        assert isinstance(error, Exception)


class TestExceptionMessages:
    """Test that exception messages are preserved."""

    @pytest.mark.parametrize(
        "exception_class,message",
        [
            (GapSenseError, "base error"),
            (RetryableError, "retry me"),
            (PermanentError, "permanent failure"),
            (StudentNotFoundError, "student abc not found"),
            (CurriculumDataError, "invalid curriculum"),
            (MediaDownloadError, "download failed"),
            (AIClientError, "API error"),
        ],
    )
    def test_exception_message_preserved(self, exception_class, message):
        """Exception message should be accessible via str()."""
        error = exception_class(message)
        assert str(error) == message


class TestExceptionClassification:
    """Test that exceptions can be correctly classified for error handling."""

    def test_permanent_errors_not_retryable(self):
        """PermanentError subclasses should not be instances of RetryableError."""
        permanent_errors = [
            StudentNotFoundError("test"),
            CurriculumDataError("test"),
            PermanentError("test"),
        ]
        for error in permanent_errors:
            assert not isinstance(error, RetryableError)

    def test_retryable_errors_not_permanent(self):
        """RetryableError subclasses should not be instances of PermanentError."""
        retryable_errors = [
            MediaDownloadError("test"),
            AIClientError("test"),
            RetryableError("test"),
        ]
        for error in retryable_errors:
            assert not isinstance(error, PermanentError)

    def test_all_domain_errors_are_gapsense_errors(self):
        """All domain exceptions should be GapSenseError instances."""
        all_errors = [
            GapSenseError("test"),
            RetryableError("test"),
            PermanentError("test"),
            StudentNotFoundError("test"),
            CurriculumDataError("test"),
            MediaDownloadError("test"),
            AIClientError("test"),
        ]
        for error in all_errors:
            assert isinstance(error, GapSenseError)
