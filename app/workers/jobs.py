"""ARQ worker jobs: the actual Context.dev work. Handlers never do this.

Lifecycle: queued -> running -> done/failed. URL is re-validated WITH DNS
here (workers may do blocking-ish DNS via a thread if needed; in this
implementation validate_url's socket.getaddrinfo is called in the worker,
not in a Telegram handler). Entitlement is checked here, server-side.
Partial results are surfaced as partial, never claimed complete.
"""
from __future__ import annotations

import asyncio

import inspect

from ..contextdev.client import API_KEY_MISSING_MESSAGE, ContextDevClient
from ..contextdev.errors import ContextDevError, ErrorKind
from ..contextdev.formats import scrape_mode_to_formats
from ..security.validators import validate_url
from ..services.credit_service import cost_guard_ok, estimate_credits
from ..services.subscription_service import check_daily_quota, check_feature, plan_limits

FEATURE_TO_CLIENT = {
    "scrape": "scrape", "search": "search", "crawl": "crawl", "map": "map_urls",
    "answers": "answers", "parse": "parse", "brand": "brand",
    "people": "people", "company": "company", "news": "news",
}


async def run_job(ctx: dict, *, kind: str, user_id: int, payload: dict,
                  plan: str = "free", used_today: int = 0):
    """Run one job. Returns a NormalizedResult dict-like summary.

    ctx: {"client": ContextDevClient} in real runs; tests may pass a fake
    client with the same method names.
    """
    feat = check_feature(plan, kind)
    if not feat.allowed:
        raise ContextDevError(ErrorKind.PERMISSION, feat.reason)
    quota = check_daily_quota(plan, used_today)
    if not quota.allowed:
        raise ContextDevError(ErrorKind.QUOTA, quota.reason)
    if kind == "crawl":
        ok, msg = cost_guard_ok("crawl", pages=payload.get("max_pages", 20),
                                plan_max_pages=plan_limits(plan)["max_crawl_pages"])
        if not ok:
            raise ValueError(msg)
    if "url" in payload and payload["url"]:
        validate_url(payload["url"])  # full check incl. DNS, in worker only
    client = ctx.get("client")
    if client is None:
        # Worker-side key resolution (see services/admin_key_service.py):
        # ctx may carry an already-resolved "context_api_key", or an
        # "api_key_resolver" callable (sync or async) that implements the
        # stored-key -> env fallback. Production main.py/ARQ wiring must
        # inject a resolver backed by AdminSettingRepository + env
        # (remaining wiring gap, documented in README/DECISIONS); without
        # either, fail with the user-facing missing-key message and make
        # no live call.
        api_key = ctx.get("context_api_key") or ctx.get("api_key")
        resolver = ctx.get("api_key_resolver")
        if api_key is None and resolver is not None:
            from ..services.admin_key_service import ApiKeyMissingError
            try:
                api_key = resolver()
                if inspect.isawaitable(api_key):
                    api_key = await api_key
            except ApiKeyMissingError as exc:
                raise ContextDevError(ErrorKind.AUTH, API_KEY_MISSING_MESSAGE) from exc
            # Other resolver errors (e.g. decryption failure from a wrong
            # SETTINGS_ENCRYPTION_KEY) propagate as-is, not as "missing".
        if not api_key:
            raise ContextDevError(ErrorKind.AUTH, API_KEY_MISSING_MESSAGE)
        client = ContextDevClient(
            api_key=api_key,
            base_url=ctx.get("context_dev_base_url", "https://api.context.dev/v1"),
            timeout=ctx.get("context_dev_timeout_seconds", 60.0),
            http_client=ctx.get("http_client"))
    method_name = FEATURE_TO_CLIENT.get(kind)
    if method_name is None:
        # batches/monitors/delete_my_data are bookkeeping kinds handled by
        # repositories, not direct Context.dev calls in this worker version.
        return {"kind": kind, "status": "accepted-bookkeeping",
                "estimated_credits": estimate_credits("scrape") if kind == "scrape" else 0}
    method = getattr(client, method_name)
    if kind in ("scrape", "crawl", "map"):
        kwargs = {k: v for k, v in payload.items() if k != "url"}
        if kind == "scrape" and "formats" not in kwargs and "mode" in kwargs:
            # Future FSM confirm path may enqueue {"mode": "screenshot"}
            # instead of explicit formats; translate it here and drop
            # the mode key (the client has no `mode` parameter).
            kwargs["formats"] = scrape_mode_to_formats(kwargs.pop("mode"))
        result = await method(payload["url"], **kwargs)
    else:
        result = await method(payload.get("query") or payload.get("url") or "", **{})
    shot_url = getattr(result, "screenshot_data_url", None)
    return {"kind": kind, "title": result.title, "text": (result.text or "")[:4000],
            "items": result.items, "sources": result.sources,
            "is_partial": result.is_partial, "request_id": result.request_id,
            "credits_consumed": (result.credits.consumed if result.credits else None),
            # Screenshot fields. screenshot_data_url_present is the
            # safe bool for logs/queues; screenshot_data_url itself is
            # carried here ONLY so the delivery helper in the same
            # process can build the Telegram photo. Size caveat: a
            # full-page screenshot data URL can be several MB, so
            # production ARQ results should prefer passing it via
            # temporary storage, not as a routine job-result payload
            # (see services/screenshot_delivery.py + DECISIONS.md).
            "screenshot_success": getattr(result, "screenshot_success", None),
            "screenshot_data_url_present": bool(shot_url),
            "screenshot_data_url": shot_url}


async def run_job_with_timeout(*args, timeout: float = 120.0, **kwargs):
    return await asyncio.wait_for(run_job(*args, **kwargs), timeout=timeout)


# ARQ worker settings (ARQ imported lazily; only used when arq is installed).
def worker_settings():
    try:
        from arq import WorkerSettings as _WS  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("arq is not installed; install requirements.txt") from exc

    class Settings(_WS):
        functions = [run_job]
        redis_settings = None  # set from REDIS_URL in main.py wiring

    return Settings


# ARQ settings object for `arq app.workers.jobs.Settings` (redis_settings is
# injected from REDIS_URL by the deployment wrapper; see README).
try:
    from arq import WorkerSettings as _ARQSettings  # type: ignore

    class Settings(_ARQSettings):  # type: ignore
        functions = [run_job]
except Exception:  # pragma: no cover
    class Settings:  # type: ignore
        functions = [run_job]
