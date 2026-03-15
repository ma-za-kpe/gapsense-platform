"""
Unit tests for MediaService.

Tests upload validation, S3 key format, retry logic, presigned URLs,
download, and connectivity checks — all with mocked S3 client.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gapsense.services.media_service import (
    ALLOWED_AUDIO_TYPES,
    ALLOWED_IMAGE_TYPES,
    BASE_BACKOFF,
    MAX_AUDIO_SIZE,
    MAX_IMAGE_SIZE,
    MAX_RETRIES,
    ContentTypeError,
    FileSizeError,
    MediaService,
    UploadError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(**overrides) -> SimpleNamespace:
    defaults = {
        "S3_MEDIA_BUCKET": "test-bucket",
        "AWS_REGION": "af-south-1",
        "AWS_ACCESS_KEY_ID": "test-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret",
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _make_service(settings=None, endpoint_url=None) -> MediaService:
    """Create a MediaService with optional endpoint override."""
    s = settings or _make_settings()
    env_patch = {"S3_ENDPOINT_URL": endpoint_url} if endpoint_url else {}
    with patch.dict("os.environ", env_patch, clear=False):
        return MediaService(s)


def _mock_s3_client():
    """Create a mock S3 client with async context manager support."""
    mock_client = AsyncMock()
    mock_client.put_object = AsyncMock(return_value={})
    mock_client.get_object = AsyncMock()
    mock_client.head_bucket = AsyncMock(return_value={})
    mock_client.generate_presigned_url = AsyncMock(return_value="https://s3.example.com/presigned")

    # Mock the stream for download
    mock_stream = AsyncMock()
    mock_stream.read = AsyncMock(return_value=b"file-content")
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=False)
    mock_client.get_object.return_value = {"Body": mock_stream}

    return mock_client


def _patch_s3_client(service: MediaService, mock_client):
    """Patch the service's session to return our mock client."""
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_client)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)
    service._session = MagicMock()
    service._session.create_client = MagicMock(return_value=mock_ctx)


# ---------------------------------------------------------------------------
# Content type validation
# ---------------------------------------------------------------------------


class TestContentTypeValidation:
    """Req 7.4, 7.5: Validate content types for images and audio."""

    def test_valid_image_types_accepted(self):
        for ct in ALLOWED_IMAGE_TYPES:
            MediaService._validate_content_type(ct, "image")  # Should not raise

    def test_valid_audio_types_accepted(self):
        for ct in ALLOWED_AUDIO_TYPES:
            MediaService._validate_content_type(ct, "audio")  # Should not raise

    def test_invalid_image_type_rejected(self):
        with pytest.raises(ContentTypeError, match="not allowed for image"):
            MediaService._validate_content_type("image/gif", "image")

    def test_invalid_audio_type_rejected(self):
        with pytest.raises(ContentTypeError, match="not allowed for audio"):
            MediaService._validate_content_type("audio/flac", "audio")

    def test_audio_type_rejected_for_image_media(self):
        with pytest.raises(ContentTypeError, match="not allowed for image"):
            MediaService._validate_content_type("audio/ogg", "image")

    def test_image_type_rejected_for_audio_media(self):
        with pytest.raises(ContentTypeError, match="not allowed for audio"):
            MediaService._validate_content_type("image/jpeg", "audio")

    def test_unsupported_media_type_rejected(self):
        with pytest.raises(ContentTypeError, match="Unsupported media_type"):
            MediaService._validate_content_type("video/mp4", "video")


# ---------------------------------------------------------------------------
# File size validation
# ---------------------------------------------------------------------------


class TestFileSizeValidation:
    """Req 7.8: Enforce size limits — 10 MB images, 25 MB audio."""

    def test_image_within_limit(self):
        content = b"x" * MAX_IMAGE_SIZE
        MediaService._validate_size(content, "image")  # Should not raise

    def test_image_exceeds_limit(self):
        content = b"x" * (MAX_IMAGE_SIZE + 1)
        with pytest.raises(FileSizeError, match="10 MB"):
            MediaService._validate_size(content, "image")

    def test_audio_within_limit(self):
        content = b"x" * MAX_AUDIO_SIZE
        MediaService._validate_size(content, "audio")  # Should not raise

    def test_audio_exceeds_limit(self):
        content = b"x" * (MAX_AUDIO_SIZE + 1)
        with pytest.raises(FileSizeError, match="25 MB"):
            MediaService._validate_size(content, "audio")

    def test_empty_file_accepted(self):
        MediaService._validate_size(b"", "image")  # Should not raise
        MediaService._validate_size(b"", "audio")  # Should not raise


# ---------------------------------------------------------------------------
# S3 key format
# ---------------------------------------------------------------------------


class TestS3KeyFormat:
    """Req 7.1: S3 key format {country}/{student_id}/{media_type}/{timestamp}_{filename}."""

    def test_key_format_structure(self):
        key = MediaService._build_s3_key("GH", "student-123", "image", "photo.jpg")
        parts = key.split("/")
        assert parts[0] == "GH"
        assert parts[1] == "student-123"
        assert parts[2] == "image"
        # Last part: {timestamp}_{filename}
        last = parts[3]
        assert last.endswith("_photo.jpg")
        timestamp_str = last.split("_")[0]
        assert timestamp_str.isdigit()

    def test_key_format_audio(self):
        key = MediaService._build_s3_key("UG", "stu-456", "audio", "voice.ogg")
        assert key.startswith("UG/stu-456/audio/")
        assert key.endswith("_voice.ogg")

    def test_key_contains_all_components(self):
        key = MediaService._build_s3_key("KE", "s1", "image", "scan.png")
        assert "KE" in key
        assert "s1" in key
        assert "image" in key
        assert "scan.png" in key


# ---------------------------------------------------------------------------
# Upload — success path
# ---------------------------------------------------------------------------


class TestUploadSuccess:
    """Req 7.1: Upload binary content to S3 with structured key."""

    @pytest.mark.asyncio
    async def test_upload_returns_s3_key(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        key = await service.upload(
            b"image-data",
            country="GH",
            student_id="stu-1",
            media_type="image",
            filename="photo.jpg",
            content_type="image/jpeg",
        )

        assert key.startswith("GH/stu-1/image/")
        assert key.endswith("_photo.jpg")
        mock_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_passes_correct_params_to_s3(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        content = b"audio-data"
        await service.upload(
            content,
            country="UG",
            student_id="stu-2",
            media_type="audio",
            filename="voice.ogg",
            content_type="audio/ogg",
        )

        call_kwargs = mock_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Body"] == content
        assert call_kwargs["ContentType"] == "audio/ogg"
        assert call_kwargs["Key"].startswith("UG/stu-2/audio/")


# ---------------------------------------------------------------------------
# Upload — validation errors
# ---------------------------------------------------------------------------


class TestUploadValidation:
    """Req 7.4, 7.5, 7.8: Upload rejects invalid content type and oversized files."""

    @pytest.mark.asyncio
    async def test_upload_rejects_invalid_content_type(self):
        service = _make_service()

        with pytest.raises(ContentTypeError):
            await service.upload(
                b"data",
                country="GH",
                student_id="s1",
                media_type="image",
                filename="f.gif",
                content_type="image/gif",
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_image(self):
        service = _make_service()

        with pytest.raises(FileSizeError):
            await service.upload(
                b"x" * (MAX_IMAGE_SIZE + 1),
                country="GH",
                student_id="s1",
                media_type="image",
                filename="big.jpg",
                content_type="image/jpeg",
            )

    @pytest.mark.asyncio
    async def test_upload_rejects_oversized_audio(self):
        service = _make_service()

        with pytest.raises(FileSizeError):
            await service.upload(
                b"x" * (MAX_AUDIO_SIZE + 1),
                country="GH",
                student_id="s1",
                media_type="audio",
                filename="big.ogg",
                content_type="audio/ogg",
            )


# ---------------------------------------------------------------------------
# Upload — retry logic
# ---------------------------------------------------------------------------


class TestUploadRetry:
    """Req 7.6: Retry up to 2 times with exponential backoff on S3 failure."""

    @pytest.mark.asyncio
    async def test_retries_on_s3_failure_then_succeeds(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        # Fail first attempt, succeed on second
        mock_client.put_object = AsyncMock(side_effect=[Exception("S3 error"), {}])
        _patch_s3_client(service, mock_client)

        with patch("gapsense.services.media_service.asyncio.sleep", new_callable=AsyncMock):
            key = await service.upload(
                b"data",
                country="GH",
                student_id="s1",
                media_type="image",
                filename="photo.jpg",
                content_type="image/jpeg",
            )

        assert key.endswith("_photo.jpg")
        assert mock_client.put_object.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        mock_client.put_object = AsyncMock(side_effect=Exception("persistent S3 error"))
        _patch_s3_client(service, mock_client)

        with patch("gapsense.services.media_service.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(UploadError, match="3 attempts"):
                await service.upload(
                    b"data",
                    country="GH",
                    student_id="s1",
                    media_type="image",
                    filename="photo.jpg",
                    content_type="image/jpeg",
                )

        # 1 initial + 2 retries = 3 total attempts
        assert mock_client.put_object.call_count == MAX_RETRIES + 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        mock_client.put_object = AsyncMock(side_effect=Exception("S3 error"))
        _patch_s3_client(service, mock_client)

        sleep_calls = []

        async def mock_sleep(seconds):
            sleep_calls.append(seconds)

        with patch("gapsense.services.media_service.asyncio.sleep", side_effect=mock_sleep):
            with pytest.raises(UploadError):
                await service.upload(
                    b"data",
                    country="GH",
                    student_id="s1",
                    media_type="image",
                    filename="photo.jpg",
                    content_type="image/jpeg",
                )

        # Backoff: 0.5s after attempt 1, 1.0s after attempt 2
        assert len(sleep_calls) == MAX_RETRIES
        assert sleep_calls[0] == BASE_BACKOFF
        assert sleep_calls[1] == BASE_BACKOFF * 2

    @pytest.mark.asyncio
    async def test_succeeds_on_last_retry(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        # Fail first 2 attempts, succeed on 3rd (last)
        mock_client.put_object = AsyncMock(side_effect=[Exception("err"), Exception("err"), {}])
        _patch_s3_client(service, mock_client)

        with patch("gapsense.services.media_service.asyncio.sleep", new_callable=AsyncMock):
            key = await service.upload(
                b"data",
                country="GH",
                student_id="s1",
                media_type="image",
                filename="photo.jpg",
                content_type="image/jpeg",
            )

        assert key.endswith("_photo.jpg")
        assert mock_client.put_object.call_count == 3


# ---------------------------------------------------------------------------
# Presigned download URL
# ---------------------------------------------------------------------------


class TestGenerateDownloadUrl:
    """Req 7.2: Presigned download URL with configurable expiry (default 1 hour)."""

    @pytest.mark.asyncio
    async def test_generates_download_url(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        url = await service.generate_download_url("GH/stu-1/image/123_photo.jpg")

        assert url == "https://s3.example.com/presigned"
        mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "GH/stu-1/image/123_photo.jpg"},
            ExpiresIn=3600,
        )

    @pytest.mark.asyncio
    async def test_custom_expiry(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        await service.generate_download_url("key", expiry_seconds=7200)

        call_kwargs = mock_client.generate_presigned_url.call_args
        assert call_kwargs[1]["ExpiresIn"] == 7200


# ---------------------------------------------------------------------------
# Presigned upload URL
# ---------------------------------------------------------------------------


class TestGenerateUploadUrl:
    """Req 7.3: Presigned upload URL with configurable expiry (default 15 min)."""

    @pytest.mark.asyncio
    async def test_generates_upload_url(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        url = await service.generate_upload_url("GH/stu-1/image/123_photo.jpg", "image/jpeg")

        assert url == "https://s3.example.com/presigned"
        mock_client.generate_presigned_url.assert_called_once_with(
            "put_object",
            Params={
                "Bucket": "test-bucket",
                "Key": "GH/stu-1/image/123_photo.jpg",
                "ContentType": "image/jpeg",
            },
            ExpiresIn=900,
        )

    @pytest.mark.asyncio
    async def test_custom_expiry(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        await service.generate_upload_url("key", "audio/ogg", expiry_seconds=1800)

        call_kwargs = mock_client.generate_presigned_url.call_args
        assert call_kwargs[1]["ExpiresIn"] == 1800


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


class TestDownload:
    """Download file bytes from S3."""

    @pytest.mark.asyncio
    async def test_download_returns_bytes(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        data = await service.download("GH/stu-1/image/123_photo.jpg")

        assert data == b"file-content"
        mock_client.get_object.assert_called_once_with(
            Bucket="test-bucket", Key="GH/stu-1/image/123_photo.jpg"
        )


# ---------------------------------------------------------------------------
# Verify connectivity
# ---------------------------------------------------------------------------


class TestVerifyConnectivity:
    """Health check: verify S3 bucket is accessible."""

    @pytest.mark.asyncio
    async def test_returns_true_when_healthy(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        _patch_s3_client(service, mock_client)

        result = await service.verify_connectivity()

        assert result is True
        mock_client.head_bucket.assert_called_once_with(Bucket="test-bucket")

    @pytest.mark.asyncio
    async def test_returns_false_when_unhealthy(self):
        service = _make_service()
        mock_client = _mock_s3_client()
        mock_client.head_bucket = AsyncMock(side_effect=Exception("unreachable"))
        _patch_s3_client(service, mock_client)

        result = await service.verify_connectivity()

        assert result is False


# ---------------------------------------------------------------------------
# Endpoint URL configuration
# ---------------------------------------------------------------------------


class TestEndpointConfiguration:
    """Req 7.7: Use LocalStack endpoint in dev, default AWS in production."""

    def test_endpoint_url_from_env(self):
        service = _make_service(endpoint_url="http://localstack:4566")
        assert service._endpoint_url == "http://localstack:4566"

    def test_no_endpoint_url_in_production(self):
        with patch.dict("os.environ", {}, clear=True):
            service = MediaService(_make_settings())
        assert service._endpoint_url is None

    def test_client_kwargs_include_endpoint_when_set(self):
        service = _make_service(endpoint_url="http://localstack:4566")
        kwargs = service._client_kwargs()
        assert kwargs["endpoint_url"] == "http://localstack:4566"

    def test_client_kwargs_exclude_endpoint_when_none(self):
        with patch.dict("os.environ", {}, clear=True):
            service = MediaService(_make_settings())
        kwargs = service._client_kwargs()
        assert "endpoint_url" not in kwargs
