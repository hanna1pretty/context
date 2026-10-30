"""Intelligence callbacks: brand / styleguide / people / company (v1)."""
from __future__ import annotations

from .base import build


def intelligence_start() -> str:
    return build("intelligence", "start")


def brand_lookup() -> str:
    return build("intelligence", "brand", "lookup")


def brand_search() -> str:
    return build("intelligence", "brand", "search")


def styleguide() -> str:
    return build("intelligence", "styleguide")


def people_search() -> str:
    return build("intelligence", "people", "search")


def people_enrich() -> str:
    return build("intelligence", "people", "enrich")


def company_search() -> str:
    return build("intelligence", "company", "search")
