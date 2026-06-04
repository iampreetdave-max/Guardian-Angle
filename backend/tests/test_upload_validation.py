"""Unit tests for upload content validation (magic-number + ext + size)."""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.upload_validation import validate_image_bytes, validate_video_head


# ------------------------------------------------------------------- video
def _mp4_head() -> bytes:
    # ISO-BMFF: 4-byte box size, then b"ftyp" at offset 4.
    return b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 8


def _mkv_head() -> bytes:
    return b"\x1aE\xdf\xa3" + b"\x00" * 12


def test_good_mp4_head_passes():
    # Should not raise.
    validate_video_head("clip.mp4", _mp4_head())


def test_good_mkv_head_passes():
    validate_video_head("clip.mkv", _mkv_head())
    # .webm shares the Matroska/EBML magic.
    validate_video_head("clip.webm", _mkv_head())


def test_bad_extension_rejected():
    with pytest.raises(HTTPException) as ei:
        validate_video_head("evil.exe", _mp4_head())
    assert ei.value.status_code == 400


def test_gif_magic_rejected_as_video():
    # GIF87a header in a file claiming to be mp4.
    with pytest.raises(HTTPException) as ei:
        validate_video_head("fake.mp4", b"GIF89a" + b"\x00" * 10)
    assert ei.value.status_code == 400


def test_mismatched_magic_rejected():
    # .mkv extension but mp4 (ftyp) content -> magic mismatch.
    with pytest.raises(HTTPException) as ei:
        validate_video_head("mismatch.mkv", _mp4_head())
    assert ei.value.status_code == 400


# ------------------------------------------------------------------- image
def test_jpeg_and_png_accepted():
    validate_image_bytes(b"\xff\xd8\xff" + b"\x00" * 64)        # JPEG
    validate_image_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)   # PNG


def test_gif_image_rejected():
    with pytest.raises(HTTPException) as ei:
        validate_image_bytes(b"GIF89a" + b"\x00" * 64)
    assert ei.value.status_code == 400


def test_oversize_image_rejected():
    from app.config import get_settings
    over = get_settings().max_image_upload_mb * 1024 * 1024 + 1
    # Valid JPEG magic but over the size cap -> still rejected.
    data = b"\xff\xd8\xff" + b"\x00" * (over - 3)
    with pytest.raises(HTTPException) as ei:
        validate_image_bytes(data)
    assert ei.value.status_code == 400
