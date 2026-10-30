"""Normalize heterogeneous Context.dev payloads into NormalizedResult.

Never invent fields: missing data stays None / empty, and `is_partial`
is surfaced honestly instead of claiming completeness.
"""
from __future__ import annotations

from .models import CreditInfo, NormalizedResult, ScrapeResult


def _credits(payload: dict) -> CreditInfo:
    km = payload.get("key_metadata") or {}
    consumed = km.get("credits_consumed")
    return CreditInfo(consumed=consumed if isinstance(consumed, int) else None)


def _first_text(*values):
    for v in values:
        if isinstance(v, str) and v.strip():
            return v
    return None


def normalize_scrape(payload: dict) -> NormalizedResult:
    md = payload.get("markdown") or {}
    meta = payload.get("metadata") or {}
    text = None
    if isinstance(md, dict):
        text = md.get("data")
    elif isinstance(md, str):
        text = md
    result = NormalizedResult(
        kind="scrape",
        title=meta.get("title"),
        text=text,
        request_id=payload.get("request_id"),
        credits=_credits(payload),
        is_partial=bool(payload.get("isPartial", False)),
        raw_keys=sorted(payload.keys()),
    )
    if payload.get("url"):
        result.sources = [payload["url"]]
    return result


def normalize_scrape_typed(payload: dict) -> ScrapeResult:
    n = normalize_scrape(payload)
    formats = payload.get("formats") or {}
    return ScrapeResult(
        url=(payload.get("url") or ""), markdown=n.text,
        html=(payload.get("html") or {}).get("data") if isinstance(payload.get("html"), dict) else None,
        title=n.title, request_id=n.request_id, credits=n.credits,
        is_partial=n.is_partial, formats=formats if isinstance(formats, dict) else {},
    )


def normalize_search(payload: dict) -> NormalizedResult:
    results = payload.get("results") or payload.get("data") or []
    items, sources = [], []
    if isinstance(results, list):
        for r in results:
            if not isinstance(r, dict):
                continue
            url = r.get("url")
            items.append({"title": r.get("title"), "url": url,
                          "snippet": r.get("snippet") or r.get("content"),
                          "domain": r.get("domain"),
                          "published_at": r.get("published_at") or r.get("date")})
            if url:
                sources.append(url)
    return NormalizedResult(kind="search", items=items, sources=sources,
                            request_id=payload.get("request_id"),
                            credits=_credits(payload),
                            is_partial=bool(payload.get("isPartial", False)),
                            raw_keys=sorted(payload.keys()))


def normalize_generic(kind: str, payload: dict) -> NormalizedResult:
    """Fallback for pattern-inferred endpoints: keep items/sources/text
    from the most common keys, never fabricate."""
    if kind == "scrape":
        return normalize_scrape(payload)
    if kind == "search":
        return normalize_search(payload)
    items = payload.get("results") or payload.get("data") or payload.get("items") or []
    if not isinstance(items, list):
        items = []
    sources = [i.get("url") for i in items if isinstance(i, dict) and i.get("url")]
    text = _first_text(payload.get("answer"), payload.get("summary"),
                       payload.get("markdown", {}).get("data") if isinstance(payload.get("markdown"), dict) else None)
    return NormalizedResult(kind=kind, text=text, items=items, sources=sources,
                            request_id=payload.get("request_id"),
                            credits=_credits(payload),
                            is_partial=bool(payload.get("isPartial", False)),
                            raw_keys=sorted(payload.keys()))
