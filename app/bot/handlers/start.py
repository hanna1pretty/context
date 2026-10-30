""" /start, /help, /language, /cancel, bare-URL conversational flow, /delete_my_data."""
from __future__ import annotations

import os

from .._compat import get_router
from ..formatters import welcome
from ..keyboards import main_menu, url_choices
from ...security.validators import validate_url_no_dns
from ._common import accept

router = get_router()

try:
    from aiogram.filters import Command as _Command
    from aiogram.types import Message as _Message
    _START = _Command("start"); _HELP = _Command("help")
    _LANG = _Command("language"); _CANCEL = _Command("cancel")
    _DELETE = _Command("delete_my_data")
except Exception:  # pragma: no cover
    _START = _HELP = _LANG = _CANCEL = _DELETE = None
    _Message = object  # type: ignore


def _is_admin(uid: int) -> bool:
    return str(uid) in {p.strip() for p in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",")
                        if p.strip()}


@router.message(_START)
async def cmd_start(message):
    # main_menu(is_admin=...) shows the admin button only for admins;
    # hiding alone never authorises (admin actions re-check server-side).
    await message.answer(welcome("id"),
                         reply_markup=main_menu(is_admin=_is_admin(message.from_user.id)))


@router.message(_HELP)
async def cmd_help(message):
    await message.answer(
        "<b>Bantuan</b>\n"
        "/scrape &lt;url&gt; — ambil konten satu URL\n"
        "/search &lt;query&gt; — pencarian web\n"
        "/crawl &lt;url&gt; — crawl website (limit sesuai paket)\n"
        "/map &lt;domain&gt; — daftar URL pada domain\n"
        "/ask &lt;pertanyaan&gt; — jawaban riset + sumber\n"
        "/parse — kirim file untuk diparse\n"
        "/brand &lt;domain&gt; — profil brand\n"
        "/styleguide &lt;url&gt; — styleguide situs\n"
        "/people &lt;query&gt; — pencarian orang (use case sah saja)\n"
        "/company &lt;query&gt; — pencarian perusahaan\n"
        "/news &lt;query&gt; — pencarian berita\n"
        "/batch, /monitor, /usage, /plan, /language, /cancel\n"
        "Atau kirim URL saja — bot akan menawarkan pilihan aksi.\n"
        "Verifikasi info penting ke sumber aslinya.")


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


@router.message()
async def on_text(message):
    """Bare URL -> inline choices; otherwise treat as search/ask intent."""
    text = (message.text or "").strip()
    if not text:
        return
    if text.startswith(("http://", "https://")):
        try:
            # No DNS here (handlers must not block): literal-IP/host checks
            # only. The worker re-validates with real DNS before Context.dev.
            validate_url_no_dns(text)
        except ValueError as exc:
            await message.answer(f"URL tidak valid / ditolak (SSRF guard): {exc}")
            return
        await message.answer("URL diterima. Pilih aksi:", reply_markup=url_choices(text))
        return
    await accept(message, "search", {"query": text})
