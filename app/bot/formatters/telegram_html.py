"""Telegram HTML helpers (the bot's primary parse mode).

Rule, enforced everywhere: escape variable content FIRST, then wrap it
in a tag. Never mix this module's output with MarkdownV2 in one message
(see telegram_markdown.py, which is for Markdown-only messages).
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from ...security.validators import escape_html as _escape_html

__all__ = [
    "escape_html", "bold", "strong", "italic", "underline", "strike",
    "code", "pre", "quote", "link", "safe_url", "truncate_for_telegram",
    "split_html_message", "redact_secrets",
]

_OPEN_TAGS = {"b", "strong", "i", "u", "s", "code", "pre", "blockquote", "a"}
_TAG_RE = re.compile(r"</?([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>")
_TOKEN_RE = re.compile(r"(<[^>]*>)")
_SECRET_PATTERNS = [
    # key=value style secrets (api_key, token, password, secret, api_hash)
    re.compile(r"(?i)\b(api[_-]?key|token|password|secret|api[_-]?hash)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\bBearer\s+\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
]


def escape_html(value: str) -> str:
    """Escape user/API content for Telegram HTML (reuses validators)."""
    return _escape_html("" if value is None else str(value))


def bold(value: str) -> str:
    return f"<b>{escape_html(value)}</b>"


def strong(value: str) -> str:
    return f"<strong>{escape_html(value)}</strong>"


def italic(value: str) -> str:
    return f"<i>{escape_html(value)}</i>"


def underline(value: str) -> str:
    return f"<u>{escape_html(value)}</u>"


def strike(value: str) -> str:
    return f"<s>{escape_html(value)}</s>"


def code(value: str) -> str:
    return f"<code>{escape_html(value)}</code>"


def pre(value: str, language: str | None = None) -> str:
    body = escape_html(value)
    if language:
        return f'<pre language="{escape_html(language)}">{body}</pre>'
    return f"<pre>{body}</pre>"


def quote(value: str) -> str:
    return f"<blockquote>{escape_html(value)}</blockquote>"


def safe_url(url: str) -> str:
    """Return the URL only if it is a plain http/https URL with no
    embedded credentials; otherwise return "" (callers fall back to
    plain text, never to a javascript:/data: link)."""
    if not url or not isinstance(url, str):
        return ""
    cleaned = url.strip()
    if len(cleaned) > 2048 or " " in cleaned:
        return ""
    try:
        parsed = urlparse(cleaned)
    except ValueError:
        return ""
    if parsed.scheme.lower() not in {"http", "https"}:
        return ""
    if not parsed.hostname or parsed.username or parsed.password:
        return ""
    return cleaned


def link(label: str, url: str) -> str:
    safe = safe_url(url)
    if not safe:
        return escape_html(label)
    return f'<a href="{escape_html(safe)}">{escape_html(label)}</a>'


def redact_secrets(text: str) -> str:
    """Mask secret-looking values before they can reach a message.

    This is a defence-in-depth net, not the primary control: handlers
    must never put keys/tokens in message text in the first place.
    """
    if not text:
        return ""
    out = str(text)
    for pattern in _SECRET_PATTERNS:
        def _mask(match: "re.Match") -> str:
            whole = match.group(0)
            if whole.lower().startswith("bearer"):
                return "Bearer ****"
            if whole.startswith("sk-"):
                return "****"
            # key=value form: keep the key name, mask the value.
            sep = ":" if ":" in whole else "="
            key = whole.split(sep, 1)[0]
            return f"{key}{sep} ****"
        out = pattern.sub(_mask, out)
    return out


def _open_tag_stack(text: str) -> list[str]:
    """Tag names left open at the end of ``text`` (innermost last)."""
    stack: list[str] = []
    for match in _TAG_RE.finditer(text):
        raw = match.group(0)
        name = match.group(1).lower()
        if name not in _OPEN_TAGS:
            continue
        if raw.startswith("</"):
            if name in stack:
                while stack and stack[-1] != name:
                    stack.pop()
                stack.pop()
        elif raw.endswith("/>") or name == "br":
            continue
        else:
            stack.append(name)
    return stack


def _close_stack(stack: list[str]) -> str:
    return "".join(f"</{name}>" for name in reversed(stack))


def truncate_for_telegram(text: str, limit: int = 3900) -> str:
    """Truncate to ``limit`` chars without ever cutting an HTML tag or
    an HTML entity in half; open tags at the cut are closed."""
    if text is None:
        return ""
    text = str(text)
    if len(text) <= limit:
        return text
    cut = limit
    # Never cut inside a tag: if the last '<' before cut has no '>' yet,
    # cut just before it.
    lt = text.rfind("<", 0, cut)
    if lt != -1 and ">" not in text[lt:cut]:
        cut = lt
    # Never cut inside an entity: '&...;' must stay whole.
    amp = text.rfind("&", 0, cut)
    if amp != -1 and ";" not in text[amp:cut]:
        cut = amp
    # Prefer a readable boundary (newline, then space) near the cut.
    for sep in ("\n", " "):
        idx = text.rfind(sep, max(0, cut - 200), cut)
        if idx > cut // 2:
            cut = idx
            break
    body = text[:cut].rstrip()
    return body + _close_stack(_open_tag_stack(body))


def split_html_message(text: str, limit: int = 3900) -> list[str]:
    """Split into chunks of at most ``limit`` chars that never cut an
    HTML tag: tags are atomic tokens, and tags open at a chunk boundary
    are closed at the end of the chunk and reopened at the next chunk's
    start. Every chunk is therefore balanced HTML."""
    if text is None:
        return [""]
    text = str(text)
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    stack: list[str] = []

    def _flush() -> None:
        nonlocal current
        if current:
            chunks.append(current + _close_stack(stack))
        current = ""

    def _reopen() -> str:
        return "".join(f"<{name}>" if name != "a" else "<a>" for name in stack)

    # NOTE: <a> reopening cannot recover the original href, so a link
    # that straddles a chunk boundary is closed and NOT reopened: the
    # visible text stays, the link simply ends at the boundary. That is
    # safer than fabricating an href. Track it by dropping 'a' on flush.
    for token in _TOKEN_RE.split(text):
        if not token:
            continue
        if token.startswith("<") and token.endswith(">"):
            match = _TAG_RE.match(token)
            name = match.group(1).lower() if match else ""
            if len(current) + len(token) > limit and current:
                _flush()
                stack = [n for n in stack if n != "a"]
                current = _reopen()
            current += token
            if match and name in _OPEN_TAGS:
                if token.startswith("</"):
                    if name in stack:
                        while stack and stack[-1] != name:
                            stack.pop()
                        stack.pop()
                elif not token.endswith("/>"):
                    stack.append(name)
            continue
        # Plain text token: may need splitting at a word boundary.
        rest = token
        while rest:
            room = limit - len(current)
            if len(rest) <= room:
                current += rest
                rest = ""
                break
            if room <= 0:
                _flush()
                stack = [n for n in stack if n != "a"]
                current = _reopen()
                continue
            window = rest[:room]
            cut = room
            for sep in ("\n", " "):
                idx = window.rfind(sep)
                if idx > room // 2:
                    cut = idx + 1
                    break
            current += rest[:cut]
            rest = rest[cut:].lstrip() if cut < len(rest) else ""
            if rest:
                _flush()
                stack = [n for n in stack if n != "a"]
                current = _reopen()
    if current:
        chunks.append(current)
    return [c for c in chunks if c]
