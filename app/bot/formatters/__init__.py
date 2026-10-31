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


# --- Premium /start welcome (OktaScrape, no channel-join content) ---
import html as _html
import re as _re

DEFAULT_WELCOME_TEMPLATE = (
    "Halo, {nama} 👋\n"
    "Selamat datang di {bot}\n\n"
    "<blockquote><b>{bot}</b> membantumu membaca, mencari, merayapi, "
    "mengekstrak, dan memantau informasi dari web lewat Context.dev.</blockquote>\n\n"
    "────────────────────\n"
    "<b>Cara pakai:</b>\n"
    "1. Pilih menu di bawah\n"
    "2. Kirim URL untuk di-scrape / di-crawl\n"
    "3. Atau kirim pertanyaan langsung\n\n"
    "Pilih fitur di bawah untuk mulai ✨"
)

_ALLOWED_TAGS = ("b", "i", "code", "blockquote", "u")


def _sanitize_template(template: str, name: str, username: str,
                       display_name: str) -> str:
    """Render a template safely: placeholders are escaped values, and
    only a small tag set survives. Every other tag is dropped (its
    inner text stays), so an admin template can never inject a
    script-like tag or a raw secret into chat."""
    display = (name or "").strip() or (username or "").strip() or "kamu"
    user_display = ("@" + username.strip()) if username and username.strip() else display
    text = _html.escape(template)
    text = text.replace("{nama}", escape_html(display))
    text = text.replace("{username}", escape_html(user_display))
    text = text.replace("{bot}", escape_html(display_name))
    for tag in _ALLOWED_TAGS:
        text = text.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        text = text.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    text = _re.sub(r'&lt;a href=&quot;(https?://[^&"\s]+)&quot;&gt;',
                   r'<a href="\1">', text)
    text = text.replace("&lt;/a&gt;", "</a>")
    return text


def welcome_text(name: str = "", username: str = "", *,
                 display_name: str = "OktaScrape", template: str | None = None,
                 language: str = "id") -> str:
    """Premium welcome text. ``template`` may use {nama}, {username},
    {bot}; when None, the default OktaScrape template is used."""
    return _sanitize_template(template if template is not None else DEFAULT_WELCOME_TEMPLATE,
                              name, username, display_name)


def truncate_caption(text: str, limit: int = 1024) -> str:
    """Truncate a Telegram photo caption without leaving a dangling tag."""
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rstrip()
    if cut.count("<") > cut.count(">"):
        cut = cut[:cut.rfind("<")].rstrip()
    return cut + "…" if cut else text[:limit - 1] + "…"


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
    "WELCOME_ID", "WELCOME_EN", "welcome", "welcome_text",
    "DEFAULT_WELCOME_TEMPLATE", "truncate_caption", "format_search_results",
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
