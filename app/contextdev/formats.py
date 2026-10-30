"""Scrape mode -> Context.dev `formats` body mapping. Pure stdlib.

VERIFIED (docs.context.dev/api-reference/web-scraping/scrape):
  POST /web/scrape with formats.screenshot: true returns
  screenshot {requested, success, data} where data is a base64 image
  data URL; screenshotParams is optional and only meaningful when
  formats.screenshot is true. The older GET /web/scrape/screenshot
  route is equivalent to formats.screenshot: true.
Screenshot mode always requests markdown as well, so a photo caption
can show title / final URL / credits / request_id and a failed
screenshot still leaves a text fallback (isPartial is surfaced).
Other modes are single-format mappings. "fresh" is NOT a format: it
is a cache-bypass intent; it maps to markdown here and any real
freshness parameter must be added once the docs confirm its name —
do not invent one.
"""
from __future__ import annotations

SCRAPE_MODES = ("markdown", "html", "screenshot", "json", "highlights", "fresh")

SCRAPE_MODE_FORMATS: dict[str, dict] = {
    "markdown": {"markdown": True},
    "html": {"html": True},
    "screenshot": {"screenshot": True, "markdown": True},
    "json": {"json": True},
    "highlights": {"highlights": True},
    "fresh": {"markdown": True},
}


def scrape_mode_to_formats(mode: str) -> dict:
    """Return a fresh formats dict for a scrape mode (raises on unknown)."""
    if mode not in SCRAPE_MODE_FORMATS:
        raise ValueError(f"unknown scrape mode: {mode!r}")
    return dict(SCRAPE_MODE_FORMATS[mode])
