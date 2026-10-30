"""Typed DTOs for Context.dev responses. Pure stdlib (dataclasses).

Verified scrape shape (from the task's verified facts):
  response.markdown.data, response.metadata.title, response.request_id,
  response.key_metadata.credits_consumed, per-format {requested, success, data},
  response.isPartial.
Everything else is treated as best-effort / optional.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CreditInfo:
    consumed: int | None = None
    remaining: int | None = None


@dataclass
class ScrapeResult:
    url: str
    markdown: str | None = None
    html: str | None = None
    title: str | None = None
    request_id: str | None = None
    credits: CreditInfo = field(default_factory=CreditInfo)
    is_partial: bool = False
    formats: dict = field(default_factory=dict)


@dataclass
class SearchHit:
    title: str | None = None
    url: str | None = None
    snippet: str | None = None
    domain: str | None = None
    published_at: str | None = None


@dataclass
class NormalizedResult:
    kind: str  # scrape|search|crawl|map|answers|parse|brand|people|company|news|batch|monitor
    title: str | None = None
    text: str | None = None
    items: list = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    request_id: str | None = None
    credits: CreditInfo = field(default_factory=CreditInfo)
    is_partial: bool = False
    raw_keys: list[str] = field(default_factory=list)


@dataclass
class JobInput:
    kind: str
    user_id: int
    payload: dict = field(default_factory=dict)
    idempotency_key: str | None = None
