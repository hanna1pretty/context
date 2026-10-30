"""Parse callbacks (v1). No server path ever appears in a callback."""
from __future__ import annotations

from .base import build

OUTPUTS = ("markdown", "html")


def parse_start() -> str:
    return build("parse", "start")


def parse_upload() -> str:
    return build("parse", "upload")


def parse_url() -> str:
    return build("parse", "url")


def parse_output(output: str) -> str:
    if output not in OUTPUTS:
        raise ValueError(f"unknown parse output: {output!r}")
    return build("parse", "output", output)


def parse_ocr() -> str:
    return build("parse", "ocr")


def parse_pages() -> str:
    return build("parse", "pages")


def parse_view() -> str:
    return build("parse", "view")


def parse_export() -> str:
    return build("parse", "export")
