"""Formatter package (REPLACED-BY-DIRECTORY: former formatters.py).

The three legacy functions keep their exact behaviour so existing
imports (``from app.bot.formatters import format_normalized``) keep
working; the new helpers live in telegram_html.py, telegram_markdown.py
and messages.py.
"""
from __future__ import annotations

from ...security.validators import escape_html, split_message
from .messages import (
    answers_result_text,
    crawl_confirm_text,
    error_context_text,
    error_quota_text,
    error_rate_limit_text,
    error_validation_text,
    help_examples_text,
    job_center_text,
    job_text,
    main_menu_text,
    map_results_text,
    monitor_delete_text,
    news_menu_text,
    parse_file_text,
    plan_text,
    scrape_confirm_text,
    scrape_menu_text,
    search_results_text,
    settings_menu_text,
    usage_text,
)
from .telegram_html import (
    bold,
    code,
    italic,
    link,
    pre,
    quote,
    redact_secrets,
    safe_url,
    split_html_message,
    truncate_for_telegram,
    underline,
)

WELCOME_ID = (
    "Selamat datang di <b>Context Intelligence Bot</b>. "
    "Saya membantu kamu membaca, mencari, merayapi, mengekstrak, dan memantau "
    "informasi dari web menggunakan Context.dev. "
    "Pilih fitur di bawah atau kirim URL dan pertanyaanmu."
)
WELCOME_EN = (
    "Welcome to <b>Context Intelligence Bot</b>. "
    "I help you read, search, crawl, extract, and monitor web information "
    "using Context.dev. Pick a feature below or send a URL or question."
)


def welcome(language: str = "id") -> str:
    return WELCOME_ID if language == "id" else WELCOME_EN


def format_search_results(items: list[dict]) -> list[str]:
    lines = []
    for i, it in enumerate(items, 1):
        title = escape_html(it.get("title") or "Untitled")
        url = escape_html(it.get("url") or "")
        snippet = escape_html((it.get("snippet") or "")[:300])
        lines.append(f"{i}. <a href=\"{url}\">{title}</a>\n{snippet}")
    text = "\n\n".join(lines) if lines else "No results found."
    return split_message(text)


def format_normalized(kind: str, result, *, language: str = "id") -> list[str]:
    """Render a NormalizedResult safely, with partial-result honesty."""
    header = f"<b>{escape_html(kind)}</b>"
    if result.is_partial:
        header += "\n⚠️ <i>Partial result — data may be incomplete.</i>"
    if result.title:
        header += f"\n<b>{escape_html(result.title)}</b>"
    body = result.text or ""
    if result.items:
        body = "\n\n".join(
            f"• {escape_html(str(it.get('title') or it.get('url') or it))}"
            + (f"\n  {escape_html(str(it.get('url')))}" if it.get("url") else "")
            for it in result.items[:20])
    if result.sources:
        body += "\n\nSumber:\n" + "\n".join(escape_html(s) for s in result.sources[:10])
    if kind == "answers":
        body += "\n\n<i>Please verify important information against the sources above.</i>"
    return split_message(header + "\n\n" + body if body else header)


__all__ = [
    "WELCOME_ID", "WELCOME_EN", "welcome", "format_search_results",
    "format_normalized", "escape_html", "split_message", "bold", "code",
    "italic", "link", "pre", "quote", "redact_secrets", "safe_url",
    "split_html_message", "truncate_for_telegram", "underline",
    "main_menu_text", "scrape_menu_text", "scrape_confirm_text",
    "search_results_text", "crawl_confirm_text", "map_results_text",
    "answers_result_text", "parse_file_text", "job_center_text", "job_text",
    "monitor_delete_text", "news_menu_text", "usage_text", "plan_text",
    "settings_menu_text", "error_validation_text", "error_rate_limit_text",
    "error_quota_text", "error_context_text", "help_examples_text",
]
