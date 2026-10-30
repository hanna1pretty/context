"""Crawl callbacks (v1)."""
from __future__ import annotations

from .base import build

PARAMS = ("pages", "depth", "paths", "subdomain", "output")


def crawl_start() -> str:
    return build("crawl", "start")


def crawl_param(param: str) -> str:
    if param not in PARAMS:
        raise ValueError(f"unknown crawl param: {param!r}")
    return build("crawl", "param", param)


def crawl_confirm() -> str:
    return build("crawl", "confirm")


def crawl_cancel() -> str:
    return build("crawl", "cancel")


def crawl_options() -> str:
    return build("crawl", "options")
