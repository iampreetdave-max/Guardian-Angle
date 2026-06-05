"""Upload content validation: extension whitelist + magic-number sniffing.

Lightweight, stdlib-only checks that run before we trust an uploaded file.
The goal is to reject obviously-wrong or mislabeled uploads (e.g. an HTML file
renamed to .mp4) cheaply, before streaming megabytes to disk or handing bytes
to a decoder. Size caps live alongside: image size is checked here, video size
is enforced while streaming in api/routes.py (we never load whole videos into
memory).
"""
from __future__ import annotations

import logging

from fastapi import HTTPException

from .config import get_settings

logger = logging.getLogger("visionscan.upload")

# Keep parity with `_VIDEO_EXTS` in api/routes.py.
_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".ogv"}


def _ext_of(filename: str | None) -> str:
    name = filename or ""
    if "." not in name:
        return ""
    return "." + name.rsplit(".", 1)[-1].lower()


def _video_magic_ok(ext: str, head: bytes) -> bool:
    """Sniff the file header against the format we expect for `ext`.

    `head` should be at least the first 16 bytes of the file.
    - mp4/mov: ISO-BMFF box — `b"ftyp"` at offset 4.
    - avi: RIFF container — `b"RIFF"` prefix and `b"AVI "` at offset 8.
    - mkv/webm: Matroska/WebM EBML — `b"\\x1aE\\xdf\\xa3"` prefix.
    - ogv: Ogg — `b"OggS"` prefix.
    """
    if ext in (".mp4", ".mov"):
        return len(head) >= 8 and head[4:8] == b"ftyp"
    if ext == ".avi":
        return (
            len(head) >= 12
            and head[:4] == b"RIFF"
            and head[8:12] == b"AVI "
        )
    if ext in (".mkv", ".webm"):
        return head[:4] == b"\x1aE\xdf\xa3"
    if ext == ".ogv":
        return head[:4] == b"OggS"
    return False


def validate_video_head(filename: str | None, head: bytes) -> None:
    """Validate a video by extension whitelist + magic number.

    Raises HTTPException 400 on an unsupported extension or a header that does
    not match the claimed container.
    """
    ext = _ext_of(filename)
    if ext not in _VIDEO_EXTS:
        raise HTTPException(400, f"Unsupported video type: {ext or '(none)'}")
    if not _video_magic_ok(ext, head):
        raise HTTPException(
            400, "File content does not match a supported video format"
        )


def validate_image_bytes(data: bytes) -> None:
    """Validate uploaded image bytes by magic number and size.

    Accepts JPEG, PNG, WebP and BMP. Raises HTTPException 400 on an unknown
    format or when the payload exceeds `max_image_upload_mb`.
    """
    settings = get_settings()
    max_bytes = settings.max_image_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(
            400, f"Image exceeds the {settings.max_image_upload_mb} MB limit"
        )

    is_jpeg = data[:3] == b"\xff\xd8\xff"
    is_png = data[:4] == b"\x89PNG"
    is_webp = len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    is_bmp = data[:2] == b"BM"
    if not (is_jpeg or is_png or is_webp or is_bmp):
        raise HTTPException(
            400, "Unsupported image format (expected JPEG, PNG, WebP or BMP)"
        )
