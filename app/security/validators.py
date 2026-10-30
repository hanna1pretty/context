"""URL / file validation, SSRF protection, HTML escaping, message splitting.

Pure stdlib only, so tests run without aiogram/FastAPI/SQLAlchemy installed.
SSRF defence is layered: scheme + host blocklist, then (where feasible)
DNS resolution and IP classification. The Context.dev call itself is
server-to-server, so this validation runs BEFORE any URL is handed to it.
"""
from __future__ import annotations

import html
import ipaddress
import re
import socket
from pathlib import PurePosixPath
from urllib.parse import urlparse

ALLOWED_SCHEMES = {"http", "https"}
MAX_URL_LENGTH = 2048
MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MiB default cap; lower per plan in services
ALLOWED_MIME_PREFIXES = (
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-", "text/", "image/png", "image/jpeg", "image/webp",
)
_BLOCKED_SUFFIXES = (".local", ".internal", ".lan", ".home", ".corp")
_URL_RE = re.compile(r"https?://[^\s<>\")\]]+", re.IGNORECASE)


def is_blocked_ip(ip_text: str) -> bool:
    """True for any non-public address (loopback/private/link-local/reserved)."""
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError:
        return True  # unparseable is not safe to allow
    return bool(
        ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
        or ip.is_multicast or ip.is_unspecified
    )


def _host_is_blocked(host: str) -> str | None:
    h = host.strip().lower().rstrip(".")
    if not h:
        return "empty host"
    if h in {"localhost"} or h.endswith(_BLOCKED_SUFFIXES):
        return f"blocked host: {h}"
    # Literal IP?
    try:
        ipaddress.ip_address(h)
        if is_blocked_ip(h):
            return f"blocked IP host: {h}"
        return None
    except ValueError:
        pass
    return None


def validate_url(raw: str, *, resolver=None) -> str:
    """Validate a user-supplied URL. Returns the cleaned URL or raises ValueError.

    resolver: optional callable(host) -> iterable of IP strings, injected in
    tests so no real DNS lookup is needed. When resolver is None, a real
    getaddrinfo lookup is attempted; failure to resolve is a rejection
    (fail closed) only when DNS was actually attempted and failed.
    """
    if not raw or not isinstance(raw, str):
        raise ValueError("URL is empty")
    url = raw.strip()
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL too long")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("only http/https URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no host")
    reason = _host_is_blocked(host)
    if reason:
        raise ValueError(reason)
    if resolver is not None:
        ips = list(resolver(host))
        if not ips:
            raise ValueError("host does not resolve")
        for ip in ips:
            if is_blocked_ip(ip):
                raise ValueError(f"host resolves to blocked IP: {ip}")
    else:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror as exc:
            raise ValueError(f"host does not resolve: {exc}") from exc
        for info in infos:
            sockaddr = info[4]
            if sockaddr and is_blocked_ip(str(sockaddr[0])):
                raise ValueError("host resolves to a private/reserved IP")
    return url


def sanitize_filename(name: str) -> str:
    """Strip directories / traversal; return a safe basename or 'upload'."""
    base = PurePosixPath(name.replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("._")
    return base or "upload"


def check_upload(filename: str, mime: str, size_bytes: int,
                 *, max_bytes: int = MAX_FILE_BYTES) -> str:
    """Return sanitized filename or raise ValueError. No content is inspected here."""
    if size_bytes < 0 or size_bytes > max_bytes:
        raise ValueError(f"file too large (max {max_bytes} bytes)")
    if not any(mime.lower().startswith(p) for p in ALLOWED_MIME_PREFIXES):
        raise ValueError(f"unsupported file type: {mime}")
    return sanitize_filename(filename)


def escape_html(text: str) -> str:
    """Escape user/API content for Telegram HTML parse mode."""
    return html.escape(str(text), quote=True)


def split_message(text: str, *, limit: int = 3900) -> list[str]:
    """Split long text without cutting URLs or fenced code blocks.

    Strategy: walk forward; prefer a newline/space boundary before `limit`;
    if the boundary would cut a URL, move the cut to just before that URL;
    if inside a ``` fence, close it at the end of the chunk and reopen it
    at the start of the next chunk.
    """
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    rest = text
    in_fence = False
    while len(rest) > limit:
        window = rest[:limit]
        # Track fence state up to the cut (count ``` occurrences).
        fence_marks = window.count("```")
        cut = limit
        # Prefer last double-newline, then newline, then space.
        for sep in ("\n\n", "\n", " "):
            idx = window.rfind(sep)
            if idx > limit // 2:
                cut = idx + (len(sep) if sep != " " else 1)
                break
        # Do not cut a URL: if a URL straddles `cut`, cut before it.
        for m in _URL_RE.finditer(rest):
            if m.start() < cut < m.end():
                if m.start() > 0:
                    cut = m.start()
                break
        chunk = rest[:cut].rstrip()
        # Close an open fence so Telegram renders the chunk correctly.
        open_here = chunk.count("```") % 2 == 1
        if in_fence or open_here:
            if open_here:
                chunk = chunk + "\n```"
                in_fence = False
            else:
                chunk = chunk + "\n```"
        chunks.append(chunk)
        rest = rest[cut:].lstrip()
        if in_fence is False and chunk.endswith("```") and open_here:
            pass
        # Reopen fence if the remainder is still inside one.
        total_fences_before = text[: len(text) - len(rest)].count("```")
        if total_fences_before % 2 == 1:
            rest = "```\n" + rest
            in_fence = True
        else:
            in_fence = False
        if not rest:
            break
    if rest:
        chunks.append(rest)
    return [c for c in chunks if c]


def validate_url_no_dns(raw: str) -> str:
    """Synchronous part of validate_url: scheme, credentials, host blocklist
    and literal-IP checks only. No DNS lookup, so it is safe in a Telegram
    handler. The worker MUST re-run validate_url() (with real DNS) before
    handing the URL to Context.dev."""
    if not raw or not isinstance(raw, str):
        raise ValueError("URL is empty")
    url = raw.strip()
    if len(url) > MAX_URL_LENGTH:
        raise ValueError("URL too long")
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise ValueError("only http/https URLs are allowed")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    host = parsed.hostname
    if not host:
        raise ValueError("URL has no host")
    reason = _host_is_blocked(host)
    if reason:
        raise ValueError(reason)
    return url
