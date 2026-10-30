"""Scrape callbacks (v1). Modes match the spec section 6 menu."""
from __future__ import annotations

from .base import build

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
