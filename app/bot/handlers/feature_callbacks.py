"""Feature callback handlers (spec section 4).

Rules, in order, for every callback:
1. answer() first (fake-compatible, failures swallowed);
2. Telegram-user check (the callback's user must match the context user);
3. ownership check for job/monitor/batch/saved items (pure check_owner);
4. entitlement via subscription_service.check_feature (locked -> plan
   screen, NEVER enqueue);
5. expired-callback handling (server-side issued_at + TTL, else home);
6. double-click protection via DoubleClickGuard (in-memory here;
   Redis SET NX EX in production);
7. NO Context.dev network call here — enqueue only, via
   workers.queue.enqueue_job (async wrapper) or an injected
   InMemoryQueue in tests.

``process_callback`` is the pure, sync core (unit-testable without
aiogram). ``handle_callback`` is the async aiogram-facing wrapper.
Legacy admin callbacks return status "legacy" here on purpose: they
belong to handlers/admin.py, which is included BEFORE this router.
"""
from __future__ import annotations

import logging

from .._compat import get_router

logger = logging.getLogger(__name__)
from ..callbacks.base import (
    DoubleClickGuard,
    check_owner,
    is_expired,
    is_legacy,
    parse_callback,
    validate_callback,
)
from ..callbacks.navigation import SCREEN_IDS
from ...services.subscription_service import FEATURE_MIN_PLAN, check_feature
from ...workers.queue import QUEUE, enqueue_job
from .navigation import answer_callback, go_home, render_screen, show_error
from ..formatters import messages as msg

router = get_router()

try:
    from aiogram import F as _F
    _FEATURE_FILTER = (
        _F.data.startswith("scrape:v1:") | _F.data.startswith("search:v1:")
        | _F.data.startswith("crawl:v1:") | _F.data.startswith("map:v1:")
        | _F.data.startswith("answers:v1:") | _F.data.startswith("parse:v1:")
        | _F.data.startswith("intelligence:v1:") | _F.data.startswith("news:v1:")
        | _F.data.startswith("job:v1:") | _F.data.startswith("batch:v1:")
        | _F.data.startswith("monitor:v1:") | _F.data.startswith("plan:v1:")
        | _F.data.startswith("settings:v1:") | _F.data.startswith("admin:v1:")
    )
except Exception:  # pragma: no cover - aiogram absent (stub router)
    _FEATURE_FILTER = None

GUARD = DoubleClickGuard()

# (namespace, action) -> feature name for entitlement checks.
_FEATURE_FOR_ACTION: dict[tuple[str, str], str] = {}
for _ns, _feat in (("scrape", "scrape"), ("search", "search"),
                   ("crawl", "crawl"), ("map", "map"),
                   ("answers", "answers"), ("parse", "parse"),
                   ("news", "news")):
    _FEATURE_FOR_ACTION[(_ns, "*")] = _feat
_FEATURE_FOR_ACTION[("intelligence", "brand")] = "brand"
_FEATURE_FOR_ACTION[("intelligence", "styleguide")] = "styleguide"
_FEATURE_FOR_ACTION[("intelligence", "people")] = "people"
_FEATURE_FOR_ACTION[("intelligence", "company")] = "company"
_FEATURE_FOR_ACTION[("intelligence", "start")] = "brand"
_FEATURE_FOR_ACTION[("intelligence", "search")] = "brand"
_FEATURE_FOR_ACTION[("intelligence", "enrich")] = "people"

# Actions that create a real job (enqueue, guarded by DoubleClickGuard).
_ENQUEUE_ACTIONS: dict[tuple[str, str], str] = {
    ("scrape", "confirm"): "scrape",
    ("crawl", "confirm"): "crawl",
    ("batch", "new"): "batch",
    ("monitor", "new"): "monitor",
    ("job", "retry"): "job_retry",
}

# Actions whose first arg is an owned item id.
_OWNED_ACTIONS = {"status", "result", "cancel", "retry", "delete",
                  "pause", "resume", "confirm_delete", "sources",
                  "export", "refresh"}

_LIST_VIEWS = {"active", "done", "failed", "all"}


def _screen_for(parsed) -> str:
    ns, action = parsed.namespace, parsed.action
    table = {
        ("scrape", "confirm"): "job_center",
        ("scrape", "mode"): "scrape",
        ("crawl", "confirm"): "job_center",
        ("search", "page"): "search_results",
        ("search", "open"): "search_results",
        ("search", "read"): "search_results",
        ("map", "page"): "map_results",
        ("news", "page"): "news_results",
        ("news", "open"): "news_results",
        ("news", "read"): "news_results",
        ("job", "list"): "job_center",
        ("job", "status"): "job_detail",
        ("job", "result"): "job_detail",
        ("batch", "list"): "batches",
        ("batch", "new"): "batches",
        ("monitor", "delete"): "monitor_delete_confirm",
        ("monitor", "confirm_delete"): "monitors",
        ("plan", "show"): "plan",
        ("plan", "detail"): "plan",
        ("plan", "faq"): "plan",
        ("plan", "upgrade"): "plan",
        ("settings", "clear_history"): "settings_clear_confirm",
        ("settings", "confirm_clear"): "settings",
        ("settings", "delete_data"): "settings_delete_confirm",
        ("settings", "confirm_delete"): "settings",
        ("settings", "privacy"): "help_privacy",
        ("admin", "dashboard"): "admin_dashboard",
        ("admin", "health"): "admin_dashboard",
        ("admin", "stats"): "admin_dashboard",
    }
    if (ns, action) in table:
        return table[(ns, action)]
    defaults = {"scrape": "scrape", "search": "search", "crawl": "crawl",
                "map": "map", "answers": "answers", "parse": "parse",
                "intelligence": "intelligence", "news": "news",
                "job": "job_center", "batch": "batches",
                "monitor": "monitors", "plan": "plan",
                "settings": "settings", "admin": "admin_dashboard"}
    return defaults.get(ns, "home")


def process_callback(data: str | None, *, user_id: int,
                     context_user_id: int | None = None,
                     is_admin: bool = False, plan: str = "free",
                     owners: dict | None = None, queue=None,
                     guard: DoubleClickGuard | None = None,
                     issued_at: float | None = None,
                     search_result_count: int | None = None) -> dict:
    """Pure callback core. Returns an outcome dict; never raises for
    bad input, never touches the network, never trusts callback data
    without the ownership/entitlement checks above."""
    if is_legacy(data):
        return {"status": "legacy", "data": data}
    if context_user_id is not None and int(context_user_id) != int(user_id):
        return {"status": "forbidden", "reason": "user mismatch"}
    if not validate_callback(data):
        return {"status": "invalid", "data": data}
    if is_expired(issued_at):
        return {"status": "expired", "screen": "home"}
    parsed = parse_callback(data)
    assert parsed is not None  # validate_callback already passed
    if parsed.namespace == "nav":
        screen = parsed.first_arg if parsed.action == "screen" else "home"
        return {"status": "nav", "screen": screen if screen in SCREEN_IDS else "home"}
    if parsed.namespace == "admin" and not is_admin:
        return {"status": "forbidden", "reason": "not admin"}
    # Entitlement (locked -> plan screen, never enqueue).
    feature = _FEATURE_FOR_ACTION.get((parsed.namespace, parsed.action)) or \
        _FEATURE_FOR_ACTION.get((parsed.namespace, "*"))
    if feature is not None:
        ent = check_feature(plan, feature)
        if not ent.allowed:
            return {"status": "locked", "feature": feature,
                    "required_plan": FEATURE_MIN_PLAN[feature], "screen": "plan"}
    # Ownership for job/monitor/batch items.
    if parsed.namespace in {"job", "batch", "monitor"} and parsed.action in _OWNED_ACTIONS:
        item_id = parsed.first_arg
        if item_id is None:
            return {"status": "invalid", "data": data}
        if owners is not None:
            owner = owners.get((parsed.namespace, item_id))
            if owner is None:
                return {"status": "not_found", "item_id": item_id}
            if not check_owner(owner, user_id):
                return {"status": "forbidden", "reason": "not owner", "item_id": item_id}
    # Result-index validation (search/news): indexes, never URLs.
    if parsed.namespace in {"search", "news"} and parsed.action in {"open", "read"}:
        if search_result_count is not None:
            try:
                idx = int(parsed.first_arg or "0")
            except ValueError:
                return {"status": "invalid", "data": data}
            if idx < 1 or idx > search_result_count:
                return {"status": "not_found", "index": idx}
    # Double-click + enqueue for job-creating actions.
    kind = _ENQUEUE_ACTIONS.get((parsed.namespace, parsed.action))
    if kind is not None:
        guard = guard or GUARD
        key = f"{user_id}:{parsed.namespace}:{parsed.action}:{parsed.first_arg or ''}"
        if guard.claim(key) == "duplicate":
            return {"status": "duplicate", "screen": _screen_for(parsed)}
        payload = {"callback": data}
        if queue is not None:
            result = queue.enqueue(kind, user_id, payload, idempotency_key=key)
            return {"status": "ok", "enqueued": True,
                    "job_id": result["job_id"], "duplicate": result["duplicate"],
                    "screen": _screen_for(parsed)}
        return {"status": "ok", "enqueued": False,
                "pending_enqueue": {"kind": kind, "payload": payload,
                                    "idempotency_key": key},
                "screen": _screen_for(parsed)}
    return {"status": "ok", "screen": _screen_for(parsed)}


async def handle_callback(callback, *, context: dict | None = None) -> dict:
    """aiogram-facing wrapper: answer first, run the core, render.

    Any failure after the answer is surfaced as a visible error
    screen (and logged), never swallowed into a dead button.
    """
    await answer_callback(callback)
    try:
        return await _handle_callback_inner(callback, context=context)
    except Exception as exc:
        logger.exception("feature callback failed for %r: %s",
                         getattr(callback, "data", None), exc)
        await answer_callback(callback, "Terjadi kesalahan, coba lagi.", show_alert=True)
        try:
            await show_error(callback, msg.error_validation_text(
                (context or {}).get("language", "id")), kind="validation")
        except Exception:
            logger.exception("feature error message also failed")
            raise
        return {"status": "error", "reason": str(exc)}


async def _handle_callback_inner(callback, *, context: dict | None = None) -> dict:
    ctx = dict(context or {})
    user = getattr(callback, "from_user", None)
    user_id = getattr(user, "id", None)
    if user_id is None:
        user_id = ctx.get("user_id")
    outcome = process_callback(
        getattr(callback, "data", None),
        user_id=int(user_id) if user_id is not None else -1,
        context_user_id=ctx.get("context_user_id"),
        is_admin=ctx.get("is_admin", False),
        plan=ctx.get("plan", "free"),
        owners=ctx.get("owners"),
        queue=ctx.get("queue"),
        guard=ctx.get("guard"),
        issued_at=ctx.get("issued_at"),
        search_result_count=ctx.get("search_result_count"),
    )
    status = outcome["status"]
    if status == "legacy":
        return outcome  # handlers/admin.py owns these
    if status == "nav":
        return outcome  # handlers/navigation.py owns these
    if status == "invalid":
        await show_error(callback, msg.error_validation_text(ctx.get("language", "id")),
                         kind="validation")
        return outcome
    if status == "expired":
        await render_screen(callback, "home", ctx, navigate=False)
        return outcome
    if status == "forbidden":
        await answer_callback(callback, "Tidak diizinkan.", show_alert=True)
        return outcome
    if status == "not_found":
        await show_error(callback, msg.error_validation_text(ctx.get("language", "id")),
                         kind="validation")
        return outcome
    if status == "locked":
        render_ctx = dict(ctx)
        render_ctx["required_plan"] = outcome["required_plan"]
        await render_screen(callback, "plan", render_ctx)
        return outcome
    if status == "duplicate":
        await render_screen(callback, outcome.get("screen", "job_center"), ctx)
        return outcome
    # Enqueue via workers.queue.enqueue_job when no test queue was given.
    pending = outcome.get("pending_enqueue")
    if pending:
        result = await enqueue_job(pending["kind"], int(user_id),
                                   pending["payload"],
                                   idempotency_key=pending["idempotency_key"])
        outcome["job_id"] = result["job_id"]
        outcome["enqueued"] = True
    await render_screen(callback, outcome.get("screen", "home"), ctx)
    return outcome


@router.callback_query(_FEATURE_FILTER)
async def on_feature_callback(callback):
    await handle_callback(callback)
