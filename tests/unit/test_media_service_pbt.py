"""
Property-based tests for MediaService.

# Feature: mvp-core-services, Property 13: Media Upload Validation
# Feature: mvp-core-services, Property 14: S3 Key Format
# Feature: mvp-core-services, Property 15: Media Upload Retry
"""

from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gapsense.services.media_service import (
    ALLOWED_AUDIO_TYPES,
    ALLOWED_IMAGE_TYPES,
    MAX_AUDIO_SIZE,
    MAX_IMAGE_SIZE,
    ContentTypeError,
    FileSizeError,
    MediaService,
    UploadError,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_media_service() -> MediaService:
    mock_settings = MagicMock()
    mock_settings.S3_MEDIA_BUCKET = "test-bucket"
    mock_settings.AWS_REGION = "af-south-1"
    mock_settings.AWS_ACCESS_KEY_ID = "test"
    mock_settings.AWS_SECRET_ACCESS_KEY = "test"
    return MediaService(mock_settings)


# ---------------------------------------------------------------------------
# Property 13: Media Upload Validation
# **Validates: Requirements 7.4, 7.5, 7.8**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    content_type=st.text(min_size=1, max_size=30).filter(lambda ct: ct not in ALLOWED_IMAGE_TYPES),
)
def test_media_rejects_invalid_image_content_type(content_type: str):
    """Property 13a: Invalid image content types are rejected."""
    svc = _make_media_service()
    with pytest.raises(ContentTypeError):
        svc._validate_content_type(content_type, "image")


@settings(max_examples=100, deadline=None)
@given(
    content_type=st.text(min_size=1, max_size=30).filter(lambda ct: ct not in ALLOWED_AUDIO_TYPES),
)
def test_media_rejects_invalid_audio_content_type(content_type: str):
    """Property 13b: Invalid audio content types are rejected."""
    svc = _make_media_service()
    with pytest.raises(ContentTypeError):
        svc._validate_content_type(content_type, "audio")


@settings(max_examples=50, deadline=None)
@given(
    size=st.integers(min_value=MAX_IMAGE_SIZE + 1, max_value=MAX_IMAGE_SIZE + 1_000_000),
)
def test_media_rejects_oversized_images(size: int):
    """Property 13c: Images exceeding 10 MB are rejected."""
    svc = _make_media_service()
    content = b"\x00" * size
    with pytest.raises(FileSizeError):
        svc._validate_size(content, "image")


@settings(max_examples=50, deadline=None)
@given(
    size=st.integers(min_value=MAX_AUDIO_SIZE + 1, max_value=MAX_AUDIO_SIZE + 1_000_000),
)
def test_media_rejects_oversized_audio(size: int):
    """Property 13d: Audio exceeding 25 MB is rejected."""
    svc = _make_media_service()
    content = b"\x00" * size
    with pytest.raises(FileSizeError):
        svc._validate_size(content, "audio")


# ---------------------------------------------------------------------------
# Property 14: S3 Key Format
# **Validates: Requirements 7.1**
# ---------------------------------------------------------------------------


@settings(max_examples=100, deadline=None)
@given(
    country=st.sampled_from(["GH", "UG", "KE", "NG"]),
    student_id=st.uuids().map(str),
    media_type=st.sampled_from(["image", "audio"]),
    filename=st.text(
        min_size=1,
        max_size=30,
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="._-"),
    ),
)
def test_s3_key_format(country: str, student_id: str, media_type: str, filename: str):
    """Property 14: S3 Key Format

    For any upload params, S3 key matches
    {country}/{student_id}/{media_type}/{timestamp}_{filename}.
    """
    key = MediaService._build_s3_key(country, student_id, media_type, filename)

    # Verify format: country/student_id/media_type/timestamp_filename
    pattern = re.compile(
        rf"^{re.escape(country)}/{re.escape(student_id)}/{re.escape(media_type)}/\d+_{re.escape(filename)}$"
    )
    assert pattern.match(key), f"S3 key '{key}' does not match expected format"

    # Verify timestamp is a valid integer
    parts = key.split("/")
    assert len(parts) == 4
    ts_and_name = parts[3]
    timestamp_str = ts_and_name.split("_", 1)[0]
    assert timestamp_str.isdigit(), f"Timestamp '{timestamp_str}' is not a valid integer"


# ---------------------------------------------------------------------------
# Property 15: Media Upload Retry
# **Validates: Requirements 7.6**
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@settings(max_examples=50, deadline=None)
@given(
    num_failures=st.integers(min_value=0, max_value=10),
)
async def test_media_upload_retry(num_failures: int):
    """Property 15: Media Upload Retry

    For any sequence of S3 failures, at most 3 total attempts
    (1 initial + 2 retries).
    """
    svc = _make_media_service()
    max_total_attempts = 3  # 1 initial + 2 retries

    call_count = 0

    async def mock_put_object(**kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= num_failures:
            raise Exception(f"S3 failure {call_count}")
        return {}

    # Mock the S3 client
    mock_client = AsyncMock()
    mock_client.put_object = mock_put_object
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch.object(svc._session, "create_client", return_value=mock_client):
        with patch("gapsense.services.media_service.asyncio.sleep", new_callable=AsyncMock):
            if num_failures >= max_total_attempts:
                with pytest.raises(UploadError):
                    await svc.upload(
                        content=b"test",
                        country="GH",
                        student_id="student-1",
                        media_type="image",
                        filename="test.jpg",
                        content_type="image/jpeg",
                    )
                assert (
                    call_count == max_total_attempts
                ), f"Expected {max_total_attempts} attempts, got {call_count}"
            else:
                result = await svc.upload(
                    content=b"test",
                    country="GH",
                    student_id="student-1",
                    media_type="image",
                    filename="test.jpg",
                    content_type="image/jpeg",
                )
                assert result is not None
                expected_attempts = num_failures + 1
                assert (
                    call_count == expected_attempts
                ), f"Expected {expected_attempts} attempts, got {call_count}"
