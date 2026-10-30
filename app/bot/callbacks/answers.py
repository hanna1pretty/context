"""Answers callbacks (v1)."""
from __future__ import annotations

from .base import build

STYLES = ("short", "detail", "structured")


def answers_start() -> str:
    return build("answers", "start")


def answers_style(style: str) -> str:
    if style not in STYLES:
        raise ValueError(f"unknown answers style: {style!r}")
    return build("answers", "style", style)


def answers_source() -> str:
    return build("answers", "source")


def answers_again() -> str:
    return build("answers", "again")


def answers_export() -> str:
    return build("answers", "export")


def answers_save() -> str:
    return build("answers", "save")


def answers_filter(filter_name: str) -> str:
    if filter_name not in {"domain", "time"}:
        raise ValueError(f"unknown answers filter: {filter_name!r}")
    return build("answers", "filter", filter_name)
