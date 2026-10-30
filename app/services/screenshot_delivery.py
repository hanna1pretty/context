"""Turn a normalized scrape result into a Telegram photo (or fallback).

This module is transport-agnostic: it returns a plain dict that the
Telegram layer (aiogram send_photo) can consume, it never sends
anything itself and never logs a data URL or screenshot bytes.

Photo caption contents (escaped, never the raw data URL): title,
final URL (http/https only), credits_consumed (authoritative, from
key_metadata), and request_id. Caption is capped for Telegram's
1024-character caption limit.

Fallback text (Indonesian, ID-primary like the rest of the bot)
explains why there is no photo — missing, failed, corrupt, or
oversized — and includes the markdown text when available, so a
failed screenshot still leaves a usable result.

Size caveat (see DECISIONS.md): a full-page screenshot data URL can
be several MB. The worker result dict may carry screenshot_data_url
for this helper in single-process dev, but production ARQ results
should prefer passing the screenshot via temporary storage (a
signed temp URL / object store) instead of as a routine multi-MB
job-result payload.
"""
from __future__ import annotations

import html

from ..contextdev.screenshot import (
    MAX_DECODED_BYTES,
    ScreenshotError,
    ScreenshotOversizeError,
    parse_data_url,
)

_CAPTION_LIMIT = 1024


def _get(obj, key: str, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _credits(obj) -> int | None:
    credits = _get(obj, "credits")
    if isinstance(credits, dict):
        return credits.get("consumed")
    return getattr(credits, "consumed", None) if credits is not None else None


def _url(obj) -> str | None:
    sources = _get(obj, "sources") or []
    url = sources[0] if sources else _get(obj, "url")
    if isinstance(url, str) and url.startswith(("http://", "https://")):
        return url
    return None


def _caption(obj) -> str:
    lines: list[str] = []
    title = _get(obj, "title")
    if isinstance(title, str) and title.strip() and "data:image/" not in title:
        lines.append(f"Screenshot: {html.escape(title.strip())}")
    else:
        lines.append("Screenshot")
    url = _url(obj)
    if url:
        lines.append(f"URL: {html.escape(url)}")
    credits = _credits(obj)
    if credits is not None:
        lines.append(f"Kredit: {html.escape(str(credits))}")
    request_id = _get(obj, "request_id")
    if isinstance(request_id, str) and request_id.strip():
        lines.append(f"Request ID: {html.escape(request_id.strip())}")
    caption = "\n".join(lines)
    # Telegram caption limit: truncate safely (plain text, no tags cut
    # mid-entity risk beyond an escaped value, which is acceptable here
    # because values are escaped before joining).
    return caption[:_CAPTION_LIMIT]


def _fallback_text(obj, reason: str) -> str:
    text = _get(obj, "text")
    body = f"Screenshot tidak tersedia: {reason}"
    if isinstance(text, str) and text.strip():
        body += "\n\n" + text.strip()[:3500]
    return body


def prepare_screenshot_message(result) -> dict:
    """Return {"kind": "photo", "bytes", "mime", "caption"} on success,
    otherwise {"kind": "fallback_text", "text": ...}.

    Input may be a NormalizedResult / ScrapeResult or a dict with the
    same keys. A dict coming from workers/jobs.py carries only
    screenshot_data_url_present (bool), not the data URL itself, so
    it can only produce a fallback unless screenshot_data_url is
    present — callers that have the full result should pass the
    NormalizedResult itself, not the worker summary dict.
    """
    data_url = _get(result, "screenshot_data_url")
    success = _get(result, "screenshot_success")
    if success is False:
        return {"kind": "fallback_text",
                "text": _fallback_text(result, "Context.dev melaporkan screenshot gagal.")}
    if not isinstance(data_url, str) or not data_url:
        if success is None:
            reason = "screenshot tidak diminta atau tidak dikembalikan oleh Context.dev."
        else:
            reason = "screenshot tidak dikembalikan oleh Context.dev."
        return {"kind": "fallback_text", "text": _fallback_text(result, reason)}
    try:
        mime, decoded = parse_data_url(data_url)
    except ScreenshotOversizeError:
        return {"kind": "fallback_text",
                "text": _fallback_text(
                    result,
                    f"screenshot melebihi batas foto Telegram ({MAX_DECODED_BYTES} byte).")}
    except ScreenshotError:
        return {"kind": "fallback_text",
                "text": _fallback_text(result, "data screenshot tidak valid atau rusak.")}
    return {"kind": "photo", "bytes": decoded, "mime": mime, "caption": _caption(result)}
