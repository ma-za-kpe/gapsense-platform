"""
S3 Media Service for Images and Audio

Handles upload/download of images (exercise book photos) and audio (voice notes)
to/from S3 with presigned URLs, content validation, size limits, and retry logic.
Uses LocalStack endpoint in dev, default AWS endpoint in production.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import structlog
from aiobotocore.session import get_session

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})
ALLOWED_AUDIO_TYPES = frozenset({"audio/ogg", "audio/mpeg", "audio/wav", "audio/mp4"})
ALLOWED_CONTENT_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_AUDIO_TYPES

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25 MB

MAX_RETRIES = 2  # 2 retries = 3 total attempts
BASE_BACKOFF = 0.5  # seconds


class MediaServiceError(Exception):
    """Base exception for MediaService errors."""


class ContentTypeError(MediaServiceError):
    """Raised when content type is not allowed."""


class FileSizeError(MediaServiceError):
    """Raised when file exceeds size limit."""


class UploadError(MediaServiceError):
    """Raised when S3 upload fails after retries."""


class MediaService:
    """S3 media service for images and audio."""

    def __init__(self, settings: Any) -> None:
        self._bucket = settings.S3_MEDIA_BUCKET
        self._region = settings.AWS_REGION
        self._access_key = settings.AWS_ACCESS_KEY_ID
        self._secret_key = settings.AWS_SECRET_ACCESS_KEY
        self._endpoint_url: str | None = os.environ.get("S3_ENDPOINT_URL") or None
        self._session = get_session()

    def _client_kwargs(self) -> dict[str, Any]:
        """Build kwargs for the S3 client context manager."""
        kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": self._region,
        }
        if self._access_key:
            kwargs["aws_access_key_id"] = self._access_key
        if self._secret_key:
            kwargs["aws_secret_access_key"] = self._secret_key
        if self._endpoint_url:
            kwargs["endpoint_url"] = self._endpoint_url
        return kwargs

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_content_type(content_type: str, media_type: str) -> None:
        """Validate content type against allowed types for the media type."""
        if media_type == "image":
            allowed = ALLOWED_IMAGE_TYPES
        elif media_type == "audio":
            allowed = ALLOWED_AUDIO_TYPES
        else:
            raise ContentTypeError(
                f"Unsupported media_type '{media_type}'. Must be 'image' or 'audio'."
            )

        if content_type not in allowed:
            raise ContentTypeError(
                f"Content type '{content_type}' not allowed for {media_type}. "
                f"Allowed: {sorted(allowed)}"
            )

    @staticmethod
    def _validate_size(content: bytes, media_type: str) -> None:
        """Validate file size against limits for the media type."""
        size = len(content)
        if media_type == "image" and size > MAX_IMAGE_SIZE:
            raise FileSizeError(
                f"Image size {size} bytes exceeds limit of {MAX_IMAGE_SIZE} bytes (10 MB)."
            )
        if media_type == "audio" and size > MAX_AUDIO_SIZE:
            raise FileSizeError(
                f"Audio size {size} bytes exceeds limit of {MAX_AUDIO_SIZE} bytes (25 MB)."
            )

    @staticmethod
    def _build_s3_key(
        country: str,
        student_id: str,
        media_type: str,
        filename: str,
    ) -> str:
        """Build S3 key: {country}/{student_id}/{media_type}/{timestamp}_{filename}."""
        timestamp = str(int(time.time()))
        return f"{country}/{student_id}/{media_type}/{timestamp}_{filename}"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def upload(
        self,
        content: bytes,
        *,
        country: str,
        student_id: str,
        media_type: str,
        filename: str,
        content_type: str,
    ) -> str:
        """Upload binary content to S3. Returns the S3 key.

        Validates content type and size before uploading.
        Retries up to 2 times with exponential backoff on S3 failure.

        Raises:
            ContentTypeError: If content_type is not allowed for the media_type.
            FileSizeError: If content exceeds size limit.
            UploadError: If S3 upload fails after all retries.
        """
        self._validate_content_type(content_type, media_type)
        self._validate_size(content, media_type)

        s3_key = self._build_s3_key(country, student_id, media_type, filename)

        last_error: Exception | None = None
        for attempt in range(1, MAX_RETRIES + 2):  # 1 initial + 2 retries = 3 attempts
            try:
                async with self._session.create_client(**self._client_kwargs()) as client:
                    await client.put_object(
                        Bucket=self._bucket,
                        Key=s3_key,
                        Body=content,
                        ContentType=content_type,
                    )
                logger.info(
                    "media_upload_success",
                    s3_key=s3_key,
                    media_type=media_type,
                    content_type=content_type,
                    size_bytes=len(content),
                    attempt=attempt,
                )
                return s3_key
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "media_upload_retry",
                    s3_key=s3_key,
                    attempt=attempt,
                    max_attempts=MAX_RETRIES + 1,
                    error=str(exc),
                )
                if attempt <= MAX_RETRIES:
                    backoff = BASE_BACKOFF * (2 ** (attempt - 1))
                    await asyncio.sleep(backoff)

        raise UploadError(f"S3 upload failed after {MAX_RETRIES + 1} attempts: {last_error}")

    async def generate_download_url(self, s3_key: str, expiry_seconds: int = 3600) -> str:
        """Generate a presigned download URL for an S3 object.

        Args:
            s3_key: The S3 object key.
            expiry_seconds: URL expiry in seconds (default 1 hour).

        Returns:
            Presigned URL string.
        """
        async with self._session.create_client(**self._client_kwargs()) as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": s3_key},
                ExpiresIn=expiry_seconds,
            )
        return url

    async def generate_upload_url(
        self, s3_key: str, content_type: str, expiry_seconds: int = 900
    ) -> str:
        """Generate a presigned upload URL for direct client uploads.

        Args:
            s3_key: The S3 object key.
            content_type: Expected content type for the upload.
            expiry_seconds: URL expiry in seconds (default 15 minutes).

        Returns:
            Presigned URL string.
        """
        async with self._session.create_client(**self._client_kwargs()) as client:
            url = await client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": s3_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expiry_seconds,
            )
        return url

    async def download(self, s3_key: str) -> bytes:
        """Download file bytes from S3.

        Args:
            s3_key: The S3 object key.

        Returns:
            File content as bytes.
        """
        async with self._session.create_client(**self._client_kwargs()) as client:
            response = await client.get_object(Bucket=self._bucket, Key=s3_key)
            async with response["Body"] as stream:
                data = await stream.read()
        return data

    async def verify_connectivity(self) -> bool:
        """Health check: verify S3 bucket is accessible.

        Returns:
            True if bucket is reachable, False otherwise.
        """
        try:
            async with self._session.create_client(**self._client_kwargs()) as client:
                await client.head_bucket(Bucket=self._bucket)
            logger.info("s3_connectivity_ok", bucket=self._bucket)
            return True
        except Exception as exc:
            logger.error(
                "s3_connectivity_failed",
                bucket=self._bucket,
                error=str(exc),
            )
            return False
