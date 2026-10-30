"""Telegram MarkdownV2 helpers.

NEVER mix these with HTML helpers in one message: a message is either
HTML (telegram_html.py, the default) or MarkdownV2 (this module).
"""
from __future__ import annotations

import re

from .telegram_html import safe_url

_MD2_CHARS = re.compile(r"([\\_\*\[\]\(\)\~\`\>\#\+\-\=\|\{\}\.\!])")


def escape_markdown(value: str) -> str:
    """Escape every MarkdownV2 special character."""
    return _MD2_CHARS.sub(r"\\\1", "" if value is None else str(value))


def bold_md(value: str) -> str:
    return f"*{escape_markdown(value)}*"


def italic_md(value: str) -> str:
    return f"_{escape_markdown(value)}_"


def code_md(value: str) -> str:
    return f"`{escape_markdown(value)}`"


def pre_md(value: str, language: str | None = None) -> str:
    body = escape_markdown(value)
    if language:
        return f"```{escape_markdown(language)}\n{body}```"
    return f"```{body}```"


def link_md(label: str, url: str) -> str:
    safe = safe_url(url)
    if not safe:
        return escape_markdown(label)
    return f"[{escape_markdown(label)}]({safe})"
