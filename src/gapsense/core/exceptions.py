"""GapSense domain exception hierarchy.

Provides a two-tier classification so the WorkerService can distinguish
transient failures (retry with backoff) from permanent failures (route
straight to the DLQ).

Hierarchy
---------
Exception
└── GapSenseError
    ├── RetryableError
    │   ├── MediaDownloadError    — S3/media fetch failures
    │   └── AIClientError         — Anthropic API timeouts, rate limits
    └── PermanentError
        ├── StudentNotFoundError  — Student ID not in database
        └── CurriculumDataError   — Missing/invalid curriculum graph
"""


class GapSenseError(Exception):
    """Base exception for all GapSense domain errors."""


class RetryableError(GapSenseError):
    """Transient failure — retry with backoff."""


class PermanentError(GapSenseError):
    """Non-recoverable failure — route to DLQ immediately."""


class StudentNotFoundError(PermanentError):
    """Student ID was not found in the database."""


class CurriculumDataError(PermanentError):
    """Curriculum graph data is missing or invalid."""


class MediaDownloadError(RetryableError):
    """Failed to download media (e.g. S3/image fetch timeout)."""


class AIClientError(RetryableError):
    """AI API call failed (e.g. timeout, rate limit, transient error)."""
