"""Scrape callbacks (v1). Modes match the spec section 6 menu."""
from __future__ import annotations

from ...contextdev.formats import SCRAPE_MODE_FORMATS, scrape_mode_to_formats
from .base import build

__all__ = ["MODES", "SCRAPE_MODE_FORMATS", "scrape_mode_to_formats",
           "scrape_start", "scrape_mode", "scrape_confirm", "scrape_cancel",
           "scrape_options", "scrape_help", "scrape_browser_actions"]

MODES = ("markdown", "html", "screenshot", "json", "highlights", "fresh")


def scrape_start() -> str:
    return build("scrape", "start")


def scrape_mode(mode: str) -> str:
    if mode not in MODES:
        raise ValueError(f"unknown scrape mode: {mode!r}")
    return build("scrape", "mode", mode)


def scrape_confirm() -> str:
    return build("scrape", "confirm")


def scrape_cancel() -> str:
    return build("scrape", "cancel")


def scrape_options() -> str:
    return build("scrape", "options")


def scrape_help() -> str:
    return build("scrape", "help")


def scrape_browser_actions() -> str:
    return build("scrape", "browser")
