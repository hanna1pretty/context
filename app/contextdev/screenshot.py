"""Strict parsing of Context.dev screenshot data URLs. Pure stdlib.

Verified shape: screenshot.data is "Screenshot as a base64 image
data URL" (docs.context.dev/api-reference/web-scraping/scrape).
Never log a data URL or its decoded bytes: a full-page screenshot
can be several MB and its bytes are user-visible page content, not
diagnostics.
"""
from __future__ import annotations

import base64
import binascii

ALLOWED_MIMES = ("image/png", "image/jpeg", "image/webp")
# Telegram photo limit (see services/screenshot_delivery.py): a decoded
# screenshot larger than this cannot be sent as a Telegram photo.
MAX_DECODED_BYTES = 10_000_000


class ScreenshotError(ValueError):
    """Base error for an unusable screenshot data URL."""


class ScreenshotOversizeError(ScreenshotError):
    """Decoded screenshot exceeds MAX_DECODED_BYTES."""


def parse_data_url(data_url) -> tuple[str, bytes]:
    """Parse "data:<mime>;base64,<payload>" -> (mime, decoded bytes).

    Strict rules:
    - input must be a string starting with "data:" with a comma separator
    - mime must be image/png, image/jpeg or image/webp
    - the header must declare base64 (a charset parameter is tolerated)
    - payload must be valid base64 (validate=True) and non-empty
    - decoded size must be <= MAX_DECODED_BYTES, else OversizeError
    Anything else raises ScreenshotError (never returns partial bytes).
    """
    if not isinstance(data_url, str) or not data_url.startswith("data:"):
        raise ScreenshotError("screenshot data is not a data URL")
    try:
        header, payload = data_url[5:].split(",", 1)
    except ValueError as exc:
        raise ScreenshotError("screenshot data URL has no payload") from exc
    parts = header.split(";")
    mime = parts[0].strip().lower()
    if mime not in ALLOWED_MIMES:
        raise ScreenshotError(f"unsupported screenshot mime: {mime!r}")
    if "base64" not in [p.strip().lower() for p in parts[1:]]:
        raise ScreenshotError("screenshot data URL is not base64-encoded")
    if not payload.strip():
        raise ScreenshotError("screenshot data URL payload is empty")
    try:
        decoded = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ScreenshotError("screenshot data is corrupt base64") from exc
    if not decoded:
        raise ScreenshotError("screenshot data is empty after decoding")
    if len(decoded) > MAX_DECODED_BYTES:
        raise ScreenshotOversizeError(
            f"screenshot is {len(decoded)} bytes, over the "
            f"{MAX_DECODED_BYTES} byte Telegram photo limit"
        )
    return mime, decoded
