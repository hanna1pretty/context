"""Map callbacks (v1). Export is entitlement-gated at handler level."""
from __future__ import annotations

from .base import build

FILTERS = ("path", "subdomain", "limit", "topic")


def map_start() -> str:
    return build("map", "start")


def map_filter(filter_name: str) -> str:
    if filter_name not in FILTERS:
        raise ValueError(f"unknown map filter: {filter_name!r}")
    return build("map", "filter", filter_name)


def map_export(fmt: str) -> str:
    if fmt not in {"json", "csv"}:
        raise ValueError(f"unknown map export format: {fmt!r}")
    return build("map", "export", fmt)


def map_page(page: int) -> str:
    if int(page) < 1:
        raise ValueError("page must be >= 1")
    return build("map", "page", str(int(page)))
