"""Central callback parser/validator.

Callback format (all NEW callbacks): ``<namespace>:v1:<action>[:<arg>...]``
- Total length must stay under Telegram's 64-byte limit.
- Job/monitor/batch callbacks carry only a short server-side ID
  (never a raw URL or a long cursor). Long cursors live server-side in
  :class:`CursorStore` and are referenced by a short ``cursor_id``.
- Legacy admin callbacks (``admin:set_api_key`` etc.) are recognised
  for backward compatibility only; see ``LEGACY_CALLBACKS``. They are
  NOT versioned and no new callback may use that shape.

Pure stdlib: no aiogram import, so tests run without aiogram installed.
When aiogram *is* installed, the string builders in the sibling modules
produce exactly the same strings that aiogram ``CallbackData.pack()``
would produce for ``prefix=<namespace>`` with fields
``version, action, ...args`` joined by ``:``.
"""
from __future__ import annotations

import re
import time
import uuid

MAX_CALLBACK_BYTES = 64
VERSION = "v1"

NAMESPACES = {
    "nav", "scrape", "search", "crawl", "map", "answers", "parse",
    "intelligence", "news", "job", "batch", "monitor", "plan",
    "settings", "admin",
}

# First action token allowed per namespace. Anything else is rejected by
# validate_callback(), so a typo'd button can never silently become a
# dead button that "looks" valid.
_NAMESPACE_ACTIONS: dict[str, set[str]] = {
    "nav": {"home", "back", "screen"},
    "scrape": {"start", "mode", "confirm", "cancel", "options", "help", "browser"},
    "search": {"start", "filter", "page", "open", "read", "save", "export", "results"},
    "crawl": {"start", "param", "confirm", "cancel", "options"},
    "map": {"start", "filter", "export", "page", "results"},
    "answers": {"start", "style", "source", "again", "export", "save", "ask", "filter"},
    "parse": {"start", "upload", "url", "output", "ocr", "pages", "view", "export"},
    "intelligence": {"start", "brand", "styleguide", "people", "company", "search", "enrich"},
    "news": {"start", "search", "company", "filter", "page", "open", "read", "save"},
    "job": {"status", "result", "cancel", "retry", "delete", "list", "refresh", "sources", "export", "page"},
    "batch": {"list", "status", "result", "cancel", "retry", "delete", "new", "page"},
    "monitor": {"new", "list", "changes", "pause", "resume", "delete",
                "confirm_delete", "pause_all", "help", "page"},
    "plan": {"show", "upgrade", "detail", "faq", "list"},
    "settings": {"language", "timezone", "notifications", "output",
                 "clear_history", "confirm_clear", "delete_data",
                 "confirm_delete", "privacy", "set_language",
                 "set_timezone", "set_output", "toggle_notifications"},
    "admin": {"dashboard", "health", "stats"},
}

# Deliberate backward-compat deviation: these pre-v1 callbacks are wired
# in app/bot/handlers/admin.py and must keep working. They are the ONLY
# non-v1 callbacks the parser recognises.
LEGACY_CALLBACKS = {
    "admin:set_api_key",
    "admin:api_key_status",
    "admin:delete_api_key",
    "admin:cancel_api_key",
}

_SHORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
_PAGE_RE = re.compile(r"^\d+$")


class CallbackParts:
    """Parsed form of one callback_data string."""

    def __init__(self, namespace: str, version: str, action: str, args: tuple[str, ...]):
        self.namespace = namespace
        self.version = version
        self.action = action
        self.args = args

    @property
    def first_arg(self) -> str | None:
        return self.args[0] if self.args else None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"CallbackParts({self.namespace!r}, {self.version!r}, "
                f"{self.action!r}, {self.args!r})")


def build(namespace: str, action: str, *args: str) -> str:
    """Build one v1 callback string, enforcing the 64-byte limit."""
    data = ":".join([namespace, VERSION, action, *[str(a) for a in args]])
    if len(data.encode("utf-8")) > MAX_CALLBACK_BYTES:
        raise ValueError(f"callback data exceeds {MAX_CALLBACK_BYTES} bytes: {data!r}")
    return data


def parse_callback(data: str | None) -> CallbackParts | None:
    """Parse a callback string; return None when it is not a v1 callback."""
    if not data or not isinstance(data, str):
        return None
    parts = data.split(":")
    if len(parts) < 3 or parts[1] != VERSION:
        return None
    return CallbackParts(parts[0], parts[1], parts[2], tuple(parts[3:]))


def is_legacy(data: str | None) -> bool:
    return data in LEGACY_CALLBACKS


def is_recognized(data: str | None) -> bool:
    """True for v1 callbacks with a known namespace/action, or legacy admin."""
    if is_legacy(data):
        return True
    return validate_callback(data)


def validate_callback(data: str | None) -> bool:
    """Structural validation: length, namespace, version, action, arg shape."""
    if not data or not isinstance(data, str):
        return False
    if len(data.encode("utf-8")) > MAX_CALLBACK_BYTES or " " in data:
        return False
    parsed = parse_callback(data)
    if parsed is None:
        return False
    allowed = _NAMESPACE_ACTIONS.get(parsed.namespace)
    if allowed is None or parsed.action not in allowed:
        return False
    # Arg-shape checks for the risky shapes: short IDs, page numbers.
    if parsed.namespace in {"job", "batch", "monitor"}:
        for arg in parsed.args:
            if arg in {"active", "done", "failed", "all"}:
                continue
            if not _SHORT_ID_RE.match(arg):
                return False
    if parsed.action == "page":
        if len(parsed.args) != 1 or not _PAGE_RE.match(parsed.args[0]):
            return False
    if parsed.namespace == "plan" and parsed.action == "upgrade":
        if parsed.args and parsed.args[0] not in {"free", "pro", "business"}:
            return False
    return True


def is_expired(issued_at: float | None, *, ttl_seconds: float = 3600,
               now: float | None = None) -> bool:
    """True when a callback's server-side state is older than ``ttl_seconds``.

    ``issued_at`` is a monotonic/epoch timestamp recorded server-side when
    the keyboard was sent (never trusted from callback data itself).
    ``None`` means "no timestamp recorded" and is treated as not expired
    here; the navigation-state expiry in callbacks/navigation.py is the
    layer that falls back to home when state is gone entirely.
    """
    if issued_at is None:
        return False
    return (now if now is not None else time.time()) - issued_at > ttl_seconds


def check_owner(owner_id: int | None, user_id: int) -> bool:
    """Pure ownership check for job/monitor/batch/saved items."""
    if owner_id is None:
        return False
    return int(owner_id) == int(user_id)


class CursorStore:
    """In-memory server-side cursor store with TTL.

    Production note: replace with Redis (SET key cursor EX ttl) or a
    Postgres table with an expires_at column. The interface is identical:
    ``store(cursor) -> short id`` and ``get(id) -> cursor | None``.
    Only short ids ever reach callback data.
    """

    def __init__(self, *, ttl_seconds: float = 3600):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[str, float]] = {}

    def store(self, cursor: str) -> str:
        cursor_id = uuid.uuid4().hex[:12]
        self._store[cursor_id] = (cursor, time.time() + self._ttl)
        return cursor_id

    def get(self, cursor_id: str) -> str | None:
        entry = self._store.get(cursor_id)
        if entry is None:
            return None
        cursor, expires = entry
        if time.time() > expires:
            del self._store[cursor_id]
            return None
        return cursor

    def prune(self) -> None:
        now = time.time()
        for key in [k for k, (_, exp) in self._store.items() if now > exp]:
            del self._store[key]


class DoubleClickGuard:
    """In-memory idempotency lock for double-click protection.

    ``claim(key)`` returns ``"first"`` for the first press and
    ``"duplicate"`` for any press within the TTL window. Production note:
    replace with a Redis lock (``SET key 1 NX EX <ttl>``); the semantics
    are the same and this class documents the contract the Redis version
    must honour.
    """

    def __init__(self, *, ttl_seconds: float = 30):
        self._ttl = ttl_seconds
        self._claims: dict[str, float] = {}

    def claim(self, key: str, *, ttl_seconds: float | None = None,
              now: float | None = None) -> str:
        moment = now if now is not None else time.time()
        expires = self._claims.get(key)
        if expires is not None and moment < expires:
            return "duplicate"
        self._claims[key] = moment + (ttl_seconds if ttl_seconds is not None else self._ttl)
        return "first"

    def release(self, key: str) -> None:
        self._claims.pop(key, None)
