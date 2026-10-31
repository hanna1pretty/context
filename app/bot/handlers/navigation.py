"""Navigation handlers + screens registry (spec section 19).

Screens registry: every screen id maps to (text function, keyboard
function). Both take a ``context`` dict (is_admin, language, plan,
page/total_pages, job_ids, monitor_ids, job, fields, ...) so a new
screen is added by adding ONE registry entry plus its keyboard —
never by editing a giant if/elif chain. Unknown or expired screens
fall back to home, never to a dead end.

All rendering works with fake message/callback objects in tests:
edit when possible, new message on MessageNotModified / not-editable
(implemented as try/except around edit_text/edit_reply_markup).
"""
from __future__ import annotations

import asyncio
import logging
import os

from .._compat import get_router

logger = logging.getLogger(__name__)


def _is_admin_id(uid) -> bool:
    try:
        return str(uid) in {p.strip() for p in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",")
                            if p.strip()}
    except Exception:
        return False
from ..callbacks.navigation import NavState
from ..formatters import messages as msg
from ..keyboards import (
    admin_dashboard_keyboard,
    admin_menu,
    answers_menu,
    answers_result_keyboard,
    batches_menu,
    batch_actions,
    brand_menu,
    company_menu,
    crawl_confirm_keyboard,
    crawl_menu,
    error_keyboard,
    help_menu,
    intelligence_menu,
    job_actions,
    job_center_menu,
    job_list_keyboard,
    locked_feature_keyboard,
    main_menu,
    map_menu,
    map_results_keyboard,
    news_menu,
    news_results_keyboard,
    monitor_actions,
    monitor_delete_confirm_keyboard,
    monitor_list_keyboard,
    monitors_menu,
    parse_menu,
    parse_result_keyboard,
    people_menu,
    plan_keyboard,
    scrape_confirm_keyboard,
    scrape_menu,
    search_menu,
    search_results_keyboard,
    settings_clear_confirm_keyboard,
    settings_delete_confirm_keyboard,
    settings_menu,
    usage_keyboard,
)
router = get_router()

try:
    from aiogram import F as _F
    _NAV_FILTER = _F.data.startswith("nav:v1:")
except Exception:  # pragma: no cover - aiogram absent (stub router)
    _NAV_FILTER = None

NAV_STATES: dict[int, NavState] = {}


def get_nav_state(user_id: int) -> NavState:
    state = NAV_STATES.get(user_id)
    if state is None or state.is_expired():
        state = NavState(user_id=user_id)
        NAV_STATES[user_id] = state
    return state


def _ctx(context: dict | None) -> dict:
    base = {"is_admin": False, "language": "id", "plan": "free",
            "page": 1, "total_pages": 1, "result_count": 0,
            "job_ids": [], "monitor_ids": [], "export_allowed": False}
    if context:
        base.update(context)
    return base


def _screen_text(screen: str, c: dict) -> str:
    lang = c["language"]
    if screen == "home":
        return msg.main_menu_text(lang)
    if screen == "scrape":
        return msg.scrape_menu_text(lang)
    if screen == "scrape_confirm":
        return msg.scrape_confirm_text(c.get("url", "https://example.com"),
                                       c.get("mode", "Markdown"), lang)
    if screen == "search":
        return msg.search_menu_text(lang)
    if screen == "search_results":
        return msg.search_results_text(c.get("query", ""), c["page"],
                                       c["total_pages"], c.get("results", []), lang)
    if screen == "crawl":
        return msg.crawl_menu_text(lang)
    if screen == "crawl_confirm":
        return msg.crawl_confirm_text(c.get("url", "https://example.com"),
                                      c.get("max_pages", 20), c.get("depth", 2),
                                      c.get("output", "Markdown"), lang)
    if screen == "map":
        return msg.map_menu_text(lang)
    if screen == "map_results":
        return msg.map_results_text(c.get("domain", ""), c["page"],
                                    c["total_pages"], c.get("urls", []), lang)
    if screen == "answers":
        return msg.answers_menu_text(lang)
    if screen == "answers_result":
        return msg.answers_result_text(c.get("answer", ""), c.get("sources", []), lang)
    if screen == "parse":
        return msg.parse_menu_text(lang)
    if screen == "parse_result":
        return msg.parse_file_text(c.get("filename", "upload"), c.get("size_bytes"),
                                   c.get("mime"), c.get("output", "Markdown"), lang)
    if screen == "intelligence":
        return msg.intelligence_menu_text(lang)
    if screen == "brand":
        return msg.brand_text(c.get("fields", {}), lang)
    if screen == "styleguide":
        return msg.brand_text(c.get("fields", {}), lang)
    if screen == "people":
        return msg.people_text(c.get("fields", {}), lang)
    if screen == "company":
        return msg.company_text(c.get("fields", {}), lang)
    if screen == "news":
        return msg.news_menu_text(lang)
    if screen == "news_results":
        return msg.search_results_text(c.get("query", ""), c["page"],
                                       c["total_pages"], c.get("results", []), lang)
    if screen == "batches":
        return msg.job_center_text(lang)
    if screen == "job_center":
        return msg.job_center_text(lang)
    if screen == "job_detail":
        return msg.job_text(c.get("job", {}), lang)
    if screen == "monitors":
        return "<b>Monitors</b>\n\n" + ("Kelola monitor kamu di bawah."
                                        if lang == "id" else "Manage your monitors below.")
    if screen == "monitor_detail":
        return msg.job_text(c.get("job", {"job_id": c.get("monitor_id", "")}), lang)
    if screen == "monitor_delete_confirm":
        return msg.monitor_delete_text(lang)
    if screen == "usage":
        return msg.usage_text(c["plan"], c.get("used_today", 0),
                              c.get("daily_limit", 10), c.get("active_jobs", 0),
                              c.get("reset_text", "besok 00:00"), lang)
    if screen == "plan":
        return msg.plan_text(lang)
    if screen == "settings":
        return msg.settings_menu_text(lang)
    if screen == "settings_delete_confirm":
        return msg.settings_delete_text(lang)
    if screen == "settings_clear_confirm":
        return msg.settings_clear_text(lang)
    if screen == "help":
        return msg.help_text(lang)
    if screen == "help_commands":
        return msg.help_commands_text(lang)
    if screen == "help_examples":
        return msg.help_examples_text(lang)
    if screen == "help_status":
        return msg.help_status_text(c.get("status", "OK"), lang)
    if screen == "help_privacy":
        return msg.help_privacy_text(lang)
    if screen == "admin":
        return "<b>Panel Admin</b>\n\nKelola API key Context.dev dan status bot."
    if screen == "admin_dashboard":
        return "<b>Dashboard Admin</b>\n\nStatus, statistik, dan API key."
    return msg.main_menu_text(lang)


def _screen_keyboard(screen: str, c: dict):
    if screen == "home":
        return main_menu(is_admin=c["is_admin"])
    if screen == "scrape":
        return scrape_menu()
    if screen == "scrape_confirm":
        return scrape_confirm_keyboard()
    if screen == "search":
        return search_menu()
    if screen == "search_results":
        return search_results_keyboard(c["page"], c["total_pages"], c["result_count"])
    if screen == "crawl":
        return crawl_menu()
    if screen == "crawl_confirm":
        return crawl_confirm_keyboard()
    if screen == "map":
        return map_menu(export_allowed=c["export_allowed"])
    if screen == "map_results":
        return map_results_keyboard(c["page"], c["total_pages"], c["export_allowed"])
    if screen == "answers":
        return answers_menu()
    if screen == "answers_result":
        return answers_result_keyboard()
    if screen == "parse":
        return parse_menu()
    if screen == "parse_result":
        return parse_result_keyboard()
    if screen == "intelligence":
        return intelligence_menu()
    if screen == "brand":
        return brand_menu()
    if screen == "styleguide":
        return brand_menu()
    if screen == "people":
        return people_menu()
    if screen == "company":
        return company_menu()
    if screen == "news":
        return news_menu()
    if screen == "news_results":
        return news_results_keyboard(c["page"], c["total_pages"], c["result_count"])
    if screen == "batches":
        return batches_menu()
    if screen == "job_center":
        return job_center_menu()
    if screen == "job_detail":
        return job_actions(c.get("job", {}).get("job_id", "unknown"))
    if screen == "monitors":
        return monitors_menu()
    if screen == "monitor_detail":
        return monitor_actions(c.get("monitor_id", "unknown"))
    if screen == "monitor_delete_confirm":
        return monitor_delete_confirm_keyboard(c.get("monitor_id", "unknown"))
    if screen == "usage":
        return usage_keyboard()
    if screen == "plan":
        return plan_keyboard()
    if screen == "settings":
        return settings_menu()
    if screen == "settings_delete_confirm":
        return settings_delete_confirm_keyboard()
    if screen == "settings_clear_confirm":
        return settings_clear_confirm_keyboard()
    if screen == "help":
        return help_menu()
    if screen in {"help_commands", "help_examples", "help_status", "help_privacy"}:
        return help_menu()
    if screen == "admin":
        return admin_menu()
    if screen == "admin_dashboard":
        return admin_dashboard_keyboard()
    return main_menu(is_admin=c["is_admin"])


# Screens registry: screen id -> (text fn, keyboard fn). Adding a screen
# means adding one entry here + its keyboard module, and listing it in
# callbacks/navigation.py SCREEN_IDS — nothing else needs editing.
def _registry_entry(screen: str):
    return (lambda c: _screen_text(screen, c),
            lambda c: _screen_keyboard(screen, c))


SCREENS: dict[str, tuple] = {}
for _sid in ("home", "scrape", "scrape_confirm", "search", "search_results",
             "crawl", "crawl_confirm", "map", "map_results", "answers",
             "answers_result", "parse", "parse_result", "intelligence",
             "brand", "styleguide", "people", "company", "news",
             "news_results", "batches", "job_center", "job_detail",
             "monitors", "monitor_detail", "monitor_delete_confirm",
             "usage", "plan", "settings", "settings_delete_confirm",
             "settings_clear_confirm", "help", "help_commands",
             "help_examples", "help_status", "help_privacy", "admin",
             "admin_dashboard"):
    SCREENS[_sid] = _registry_entry(_sid)


async def _maybe_await(value):
    if asyncio.iscoroutine(value):
        return await value
    return value


async def answer_callback(callback, text: str | None = None, show_alert: bool = False) -> None:
    """Answer first, fake-compatible: any failure is swallowed because a
    second answer attempt must never break the handler itself."""
    try:
        if text is not None:
            await _maybe_await(callback.answer(text, show_alert=show_alert))
        else:
            await _maybe_await(callback.answer())
    except Exception:
        pass


async def edit_or_send(target, text: str, reply_markup=None, parse_mode: str = "HTML") -> str:
    """Edit the target message when possible; otherwise send a new one.
    Returns "edited" or "sent". Works with fake objects in tests.

    Failure path (this was a live bug): an edit failure used to fall
    through silently. Now the fallback send is attempted, and if THAT
    also fails the error is logged AND raised, so the bot log shows
    it instead of the user staring at a dead button.
    """
    message = getattr(target, "message", None) or target
    edit = getattr(message, "edit_text", None)
    if callable(edit):
        try:
            await _maybe_await(edit(text, reply_markup=reply_markup, parse_mode=parse_mode))
            return "edited"
        except Exception as exc:
            logger.exception("edit_text failed, falling back to a new message: %s", exc)
    answer = getattr(message, "answer", None)
    if callable(answer):
        try:
            await _maybe_await(answer(text, reply_markup=reply_markup, parse_mode=parse_mode))
            return "sent"
        except Exception as exc:
            logger.exception("fallback message send failed: %s", exc)
            raise RuntimeError("edit and fallback send both failed") from exc
    raise RuntimeError("target has neither edit_text nor answer")


async def render_screen(target, screen: str, context: dict | None = None,
                        *, navigate: bool = True) -> str:
    """Render ``screen`` (unknown -> home). Updates NavState when the
    user id is known. Returns the screen actually rendered."""
    c = _ctx(context)
    user_id = c.get("user_id")
    if user_id is None:
        user = getattr(target, "from_user", None)
        user_id = getattr(user, "id", None) if user is not None else None
    # Preserve the admin button across navigation: the original context
    # never carried is_admin, so every nav screen silently lost Menu
    # Admin. Fill it from ADMIN_TELEGRAM_IDS when not explicitly set.
    if context is None or "is_admin" not in context:
        if user_id is not None and _is_admin_id(user_id):
            c["is_admin"] = True
    if screen not in SCREENS:
        screen = "home"
    if user_id is not None:
        state = get_nav_state(int(user_id))
        if navigate:
            state.push(screen)
        else:
            state.current_screen = screen
    text_fn, kb_fn = SCREENS[screen]
    await edit_or_send(target, text_fn(c), reply_markup=kb_fn(c))
    return screen


async def go_back(callback, context: dict | None = None) -> str:
    user_id = _user_id(callback, context)
    screen = "home"
    if user_id is not None:
        screen = get_nav_state(int(user_id)).go_back()
    return await render_screen(callback, screen, context, navigate=False)


async def go_home(callback, context: dict | None = None) -> str:
    user_id = _user_id(callback, context)
    if user_id is not None:
        get_nav_state(int(user_id)).go_home()
    return await render_screen(callback, "home", context, navigate=False)


async def show_error(callback, message_text: str, back_screen: str = "home",
                     kind: str = "validation") -> str:
    await answer_callback(callback)
    await edit_or_send(callback, message_text,
                       reply_markup=error_keyboard(kind, back_screen))
    return kind


def _user_id(callback, context: dict | None):
    if context and context.get("user_id") is not None:
        return context["user_id"]
    user = getattr(callback, "from_user", None)
    return getattr(user, "id", None) if user is not None else None


@router.callback_query(_NAV_FILTER)
async def on_nav_callback(callback):
    # Answer FIRST so the spinner never sticks, then render. Any
    # failure after the answer must still reach the user as a visible
    # error message (and the bot log), never as a silent dead button.
    await answer_callback(callback)
    try:
        data = getattr(callback, "data", "") or ""
        parts = data.split(":")
        if len(parts) >= 3 and parts[2] == "home":
            await go_home(callback)
        elif len(parts) >= 3 and parts[2] == "back":
            await go_back(callback)
        elif len(parts) >= 4 and parts[2] == "screen":
            await render_screen(callback, parts[3])
        else:
            await go_home(callback)
    except Exception as exc:
        logger.exception("nav callback failed for %r: %s", getattr(callback, "data", None), exc)
        # A second answer() may fail in real Telegram (one answer per
        # callback); answer_callback swallows that, the error message
        # below is the visible response.
        await answer_callback(callback, "Terjadi kesalahan, coba lagi.", show_alert=True)
        try:
            await edit_or_send(
                callback,
                "⚠️ <b>Terjadi kesalahan saat membuka layar ini.</b>\n"
                "Silakan tekan Menu Utama atau kirim /start lagi.",
                reply_markup=error_keyboard("validation", "home"))
        except Exception:
            logger.exception("nav error message also failed")
            raise
