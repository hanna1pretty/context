""" /start, /help, /language, /cancel, bare-URL conversational flow, /delete_my_data.

/start is the premium welcome (OktaScrape): a banner photo when an
admin has set one, otherwise a text card, then the main-menu inline
keyboard. No channel-join or verification-access content anywhere.
/help is an alias for the inline Bantuan screen, not a raw command dump.
"""
from __future__ import annotations

import os

from .._compat import get_router
from ..formatters import truncate_caption, welcome_text
from ..keyboards import help_menu, main_menu, url_choices
from ...security.validators import escape_html, validate_url_no_dns
from ...services.welcome_service import WELCOME_STORE
from ._common import accept, send_html

router = get_router()

try:
    from aiogram.filters import BaseFilter as _BaseFilter
    from aiogram.filters import Command as _Command
    _START = _Command("start"); _HELP = _Command("help")
    _LANG = _Command("language"); _CANCEL = _Command("cancel")
    _DELETE = _Command("delete_my_data")

    class _NotCommandFilter(_BaseFilter):
        """Bare-text catch-all must NOT swallow commands.

        Live bug: this handler used to match every message, and because
        the start router is included before the scrape/search/... routers,
        "/scrape https://..." was consumed here as a *search* job instead
        of reaching cmd_scrape. Commands now fall through to their own
        handlers.
        """

        async def __call__(self, message) -> bool:
            text = (message.text or "").strip()
            return bool(text) and not text.startswith("/")

    _NOT_COMMAND = _NotCommandFilter()
except Exception:  # pragma: no cover
    _START = _HELP = _LANG = _CANCEL = _DELETE = None
    _NOT_COMMAND = None


def _is_admin(uid: int) -> bool:
    return str(uid) in {p.strip() for p in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",")
                        if p.strip()}


def _display_name() -> str:
    return os.environ.get("BOT_DISPLAY_NAME", "OktaScrape") or "OktaScrape"


def _person(message):
    user = getattr(message, "from_user", None)
    name = getattr(user, "first_name", "") if user is not None else ""
    username = getattr(user, "username", "") if user is not None else ""
    return name or "", username or ""


async def send_welcome(message, is_admin: bool = False, welcome_store=None):
    """Premium /start: banner photo + welcome caption when set,
    otherwise the welcome text card. Always with the main menu."""
    store = welcome_store if welcome_store is not None else WELCOME_STORE
    name, username = _person(message)
    template = store.template if store is not None else None
    text = welcome_text(name, username, display_name=_display_name(), template=template)
    keyboard = main_menu(is_admin=is_admin)
    banner = store.banner_photo_file_id if store is not None else None
    if banner:
        answer_photo = getattr(message, "answer_photo", None)
        if callable(answer_photo):
            try:
                await answer_photo(banner, caption=truncate_caption(text),
                                   reply_markup=keyboard, parse_mode="HTML")
                return "photo"
            except Exception:
                pass  # fall through to the text card, never a dead /start
    await send_html(message, text, reply_markup=keyboard)
    return "text"


@router.message(_START)
async def cmd_start(message):
    # main_menu(is_admin=...) shows the admin button only for admins;
    # hiding alone never authorises (admin actions re-check server-side).
    await send_welcome(message, is_admin=_is_admin(message.from_user.id))


@router.message(_HELP)
async def cmd_help(message):
    # /help is now the inline Bantuan screen, not a raw command dump.
    # The full command list is still reachable from that screen's
    # "Semua Command" button, as an opt-in screen.
    from ..formatters import messages as msg

    await send_html(message, msg.help_text("id"), reply_markup=help_menu())


@router.message(_LANG)
async def cmd_language(message):
    await message.answer("Pilih bahasa: kirim /language id atau /language en. "
                         "Default: id. (Per-user setting stored in users.language.)")


@router.message(_CANCEL)
async def cmd_cancel(message):
    await message.answer("Input dibatalkan. Job yang masih queued dapat dibatalkan "
                         "oleh worker; job yang sudah running tidak dapat dibatalkan.")


@router.message(_DELETE)
async def cmd_delete_my_data(message):
    # Real deletion runs in the service layer (repositories.delete_user_data)
    # with audit logging; this handler only acknowledges + enqueues it.
    await accept(message, "delete_my_data", {})


@router.message(_NOT_COMMAND)
async def on_text(message):
    """Bare URL -> inline choices; otherwise treat as search/ask intent."""
    text = (message.text or "").strip()
    if not text:
        return
    if text.startswith("/"):
        # Direct-call safety net (the filter above already excludes
        # commands in aiogram); never swallow a command as a search.
        return
    if text.startswith(("http://", "https://")):
        try:
            # No DNS here (handlers must not block): literal-IP/host checks
            # only. The worker re-validates with real DNS before Context.dev.
            validate_url_no_dns(text)
        except ValueError as exc:
            await send_html(message, f"URL tidak valid / ditolak (SSRF guard): {escape_html(str(exc))}")
            return
        await message.answer("URL diterima. Pilih aksi:", reply_markup=url_choices(text))
        return
    await accept(message, "search", {"query": text})
