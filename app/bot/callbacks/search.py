"""Search callbacks (v1). Results are addressed by INDEX, never by URL."""
from __future__ import annotations

from .base import build

FILTERS = ("domain", "time", "language", "location", "count", "content")


def search_start() -> str:
    return build("search", "start")


def search_filter(filter_name: str) -> str:
    if filter_name not in FILTERS:
        raise ValueError(f"unknown search filter: {filter_name!r}")
    return build("search", "filter", filter_name)


def search_page(page: int) -> str:
    if int(page) < 1:
        raise ValueError("page must be >= 1")
    return build("search", "page", str(int(page)))


def search_open(index: int) -> str:
    return build("search", "open", str(int(index)))


def search_read(index: int) -> str:
    return build("search", "read", str(int(index)))


def search_save() -> str:
    return build("search", "save")


def search_export() -> str:
    return build("search", "export")


# --- News callbacks (kept here: the spec's callbacks/ list has no
# separate news.py; news shares the search result/index model). ---
NEWS_FILTERS = ("date", "domain", "page")


def news_search() -> str:
    return build("news", "search")


def news_company() -> str:
    return build("news", "company")


def news_filter(filter_name: str) -> str:
    if filter_name not in NEWS_FILTERS:
        raise ValueError(f"unknown news filter: {filter_name!r}")
    return build("news", "filter", filter_name)


def news_page(page: int) -> str:
    if int(page) < 1:
        raise ValueError("page must be >= 1")
    return build("news", "page", str(int(page)))


def news_open(index: int) -> str:
    return build("news", "open", str(int(index)))


def news_read(index: int) -> str:
    return build("news", "read", str(int(index)))


def news_save() -> str:
    return build("news", "save")
