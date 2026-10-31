""" /admin -- admin ONLY, enforced in the service layer, never by
button hiding alone.

Admin-panel Context.dev API key flow (the primary way to set the key;
CONTEXT_DEV_API_KEY in env is only a fallback at call time):
  /admin -> [Set Context API Key] -> prompt (private chat only) ->
  next private message from that admin is treated as the key -> the
  bot tries to delete that input message, saves the key Fernet-encrypted
  (services/admin_key_service.py), and confirms ONLY with the masked
  form (**** + last 4 chars). The full key is never echoed, never
  logged, and never put in an audit payload.
  [Lihat Status API Key] shows masked status only.
  [Hapus API Key] deletes the stored key.
  [Batal] or /cancel (while awaiting) cancels the input.

Wiring notes (honest gaps, see README/DECISIONS):
- KEY_STORE defaults to the in-memory store and INPUT_STATE is in-process.
  That is correct for single-process dev, but production main.py wiring
  must replace KEY_STORE with a DB-backed store (AdminSettingRepository
  via the async helpers in admin_key_service) and move INPUT_STATE to
  Redis FSM, or keys will be lost on restart and not shared between
  workers. The service functions themselves are store-agnostic.
- This router is included BEFORE start.py in bot/router.py so the
  awaiting-input and awaiting-cancel filters are evaluated before the
  bare-text catch-all in start.py.
"""
from __future__ import annotations

import os

from .._compat import get_router
from ..callbacks.admin import (
    admin_banner_delete,
    admin_banner_set,
    admin_welcome_cancel,
    admin_welcome_reset,
    admin_welcome_set,
    admin_welcome_show,
)
from ..keyboards import (
    admin_cancel_keyboard,
    admin_menu,
    admin_welcome_cancel_keyboard,
)
from ...services import admin_key_service as aks
from ...services.welcome_service import WELCOME_STORE, WelcomeInputState
from ._common import send_html

router = get_router()

KEY_STORE = aks.InMemoryAdminKeyStore()
INPUT_STATE = aks.AdminKeyInputState()
WELCOME_INPUT = WelcomeInputState()

try:
    from aiogram.filters import BaseFilter as _BaseFilter
    from aiogram.filters import Command as _C
    from aiogram import F as _F

    class _AwaitingApiKeyFilter(_BaseFilter):
        async def __call__(self, message) -> bool:
            text = (message.text or "").strip()
            return (INPUT_STATE.is_awaiting(message.from_user.id)
                    and bool(text) and not text.startswith("/"))

    class _CancelApiKeyFilter(_BaseFilter):
        async def __call__(self, message) -> bool:
            return (INPUT_STATE.is_awaiting(message.from_user.id)
                    and (message.text or "").strip() == "/cancel")

    class _AwaitingWelcomeFilter(_BaseFilter):
        async def __call__(self, message) -> bool:
            text = (message.text or "").strip()
            return (WELCOME_INPUT.is_awaiting_template(message.from_user.id)
                    and bool(text) and not text.startswith("/"))

    class _AwaitingBannerFilter(_BaseFilter):
        async def __call__(self, message) -> bool:
            return (WELCOME_INPUT.is_awaiting_banner(message.from_user.id)
                    and bool(getattr(message, "photo", None)))

    class _CancelWelcomeFilter(_BaseFilter):
        async def __call__(self, message) -> bool:
            return ((WELCOME_INPUT.is_awaiting_template(message.from_user.id)
                     or WELCOME_INPUT.is_awaiting_banner(message.from_user.id))
                    and (message.text or "").strip() == "/cancel")

    _CMD = _C("admin")
    _SET = _F.data == "admin:set_api_key"
    _STATUS = _F.data == "admin:api_key_status"
    _DELETE = _F.data == "admin:delete_api_key"
    _CANCEL_CB = _F.data == "admin:cancel_api_key"
    _AWAITING = _AwaitingApiKeyFilter()
    _CANCEL = _CancelApiKeyFilter()
    _WELCOME_SET = _F.data == admin_welcome_set()
    _WELCOME_SHOW = _F.data == admin_welcome_show()
    _WELCOME_RESET = _F.data == admin_welcome_reset()
    _WELCOME_CANCEL_CB = _F.data == admin_welcome_cancel()
    _BANNER_SET = _F.data == admin_banner_set()
    _BANNER_DELETE = _F.data == admin_banner_delete()
    _AWAITING_WELCOME = _AwaitingWelcomeFilter()
    _AWAITING_BANNER = _AwaitingBannerFilter()
    _CANCEL_WELCOME = _CancelWelcomeFilter()
except Exception:  # pragma: no cover - aiogram absent (stub router)
    _CMD = _SET = _STATUS = _DELETE = _CANCEL_CB = _AWAITING = _CANCEL = None
    _WELCOME_SET = _WELCOME_SHOW = _WELCOME_RESET = _WELCOME_CANCEL_CB = None
    _BANNER_SET = _BANNER_DELETE = _AWAITING_WELCOME = _AWAITING_BANNER = None
    _CANCEL_WELCOME = None


def _admin_ids() -> list[int]:
    return [int(p.strip()) for p in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",")
            if p.strip().isdigit()]


def _encryption_key() -> str:
    return os.environ.get("SETTINGS_ENCRYPTION_KEY", "")


def _env_key() -> str:
    return os.environ.get("CONTEXT_DEV_API_KEY", "")


def _is_admin(uid: int) -> bool:
    return uid in _admin_ids()


async def _refuse(target) -> None:
    """Plain refusal, no hint about the key. Works for messages and callbacks."""
    try:
        await target.answer(aks.NOT_ADMIN_MESSAGE)
    except Exception:
        pass


@router.message(_CMD)
async def cmd_admin(message):
    if not _is_admin(message.from_user.id):
        await message.answer(aks.NOT_ADMIN_MESSAGE)
        return
    await message.answer(
        "Panel Admin\n"
        "Statistik, job, dan health tersedia lewat Admin API internal "
        "(FastAPI /api/admin/*) dengan audit log.\n"
        "API key Context.dev di-set dari panel ini (bukan dari chat umum). "
        "Jangan kirim secret lewat chat selain alur Set di bawah, di chat pribadi.",
        reply_markup=admin_menu())


@router.callback_query(_SET)
async def cb_set_api_key(callback):
    uid = callback.from_user.id
    if not _is_admin(uid):
        await _refuse(callback)
        return
    chat = getattr(callback.message, "chat", None)
    if chat is not None and getattr(chat, "type", "private") != "private":
        await callback.answer(
            "Gunakan chat pribadi dengan bot untuk set API key, bukan grup.",
            show_alert=True)
        return
    INPUT_STATE.start(uid)
    await callback.message.answer(aks.set_prompt_text(),
                                  reply_markup=admin_cancel_keyboard())
    await callback.answer()


@router.callback_query(_STATUS)
async def cb_api_key_status(callback):
    uid = callback.from_user.id
    if not _is_admin(uid):
        await _refuse(callback)
        return
    try:
        status = aks.get_masked_status(KEY_STORE, admin_id=uid, admin_ids=_admin_ids(),
                                       encryption_key=_encryption_key(), env_key=_env_key())
    except PermissionError:
        await _refuse(callback)
        return
    await callback.message.answer(aks.status_message(status))
    await callback.answer()


@router.callback_query(_DELETE)
async def cb_delete_api_key(callback):
    uid = callback.from_user.id
    if not _is_admin(uid):
        await _refuse(callback)
        return
    aks.delete_api_key(KEY_STORE, admin_id=uid, admin_ids=_admin_ids())
    await callback.message.answer("API key Context.dev dihapus dari panel admin.")
    await callback.answer()


@router.callback_query(_CANCEL_CB)
async def cb_cancel_api_key(callback):
    uid = callback.from_user.id
    if not _is_admin(uid):
        await _refuse(callback)
        return
    INPUT_STATE.cancel(uid)
    await callback.message.answer("Input API key dibatalkan. Key tidak disimpan.")
    await callback.answer()


@router.message(_CANCEL)
async def on_cancel_api_key_input(message):
    INPUT_STATE.cancel(message.from_user.id)
    await message.answer("Input API key dibatalkan. Key tidak disimpan.")


@router.message(_AWAITING)
async def on_admin_api_key_input(message):
    """The next private message from an awaiting admin IS the key."""
    uid = message.from_user.id
    if not _is_admin(uid):
        INPUT_STATE.cancel(uid)
        await message.answer(aks.NOT_ADMIN_MESSAGE)
        return
    chat_type = getattr(getattr(message, "chat", None), "type", "private")
    if chat_type != "private":
        # Never save a key sent in a group: it is already in group history.
        INPUT_STATE.cancel(uid)
        await message.answer(
            "API key TIDAK disimpan karena dikirim di luar chat pribadi. "
            "Hapus pesan itu dari grup, lalu ulangi dari /admin di chat "
            "pribadi dengan bot.")
        return
    # Try to delete the input message; warn if Telegram refuses, so the
    # admin deletes it manually from their own chat history.
    delete_failed = False
    try:
        await message.delete()
    except Exception:
        delete_failed = True
    INPUT_STATE.cancel(uid)
    try:
        masked = aks.set_api_key(KEY_STORE, admin_id=uid, admin_ids=_admin_ids(),
                                 plaintext=message.text or "",
                                 encryption_key=_encryption_key())
    except RuntimeError as exc:
        # Missing/invalid SETTINGS_ENCRYPTION_KEY: nothing was stored.
        await message.answer(str(exc))
        return
    except (ValueError, PermissionError) as exc:
        await message.answer(str(exc))
        return
    text = aks.saved_message(masked)
    if delete_failed:
        text += ("\nPesan input tidak bisa dihapus otomatis oleh bot -- "
                 "hapus manual pesan key itu dari riwayat chat kamu.")
    await message.answer(text)


# --- Welcome / banner admin flows (see services/welcome_service.py) ---
def _chat_type(target) -> str:
    chat = getattr(target, "chat", None)
    return getattr(chat, "type", "private") if chat is not None else "private"


async def _require_private(callback) -> bool:
    if _chat_type(callback.message) != "private":
        await callback.answer(
            "Gunakan chat pribadi dengan bot untuk pengaturan ini, bukan grup.",
            show_alert=True)
        return False
    return True


def _largest_photo_file_id(message):
    photos = getattr(message, "photo", None)
    if not photos:
        return None
    last = photos[-1]
    if isinstance(last, dict):
        return last.get("file_id")
    return getattr(last, "file_id", None)


@router.callback_query(_WELCOME_SET)
async def cb_welcome_set(callback):
    if not _is_admin(callback.from_user.id):
        await _refuse(callback)
        return
    if not await _require_private(callback):
        return
    WELCOME_INPUT.start_template(callback.from_user.id)
    await callback.message.answer(
        "Kirim teks sambutan baru untuk /start.\n"
        "Placeholder yang didukung: {nama}, {username}, {bot}.\n"
        "Tag HTML yang diizinkan: <b>, <i>, <code>, <blockquote>.\n"
        "Maksimal 2000 karakter. Tekan Batal untuk membatalkan.",
        reply_markup=admin_welcome_cancel_keyboard())
    await callback.answer()


@router.callback_query(_WELCOME_SHOW)
async def cb_welcome_show(callback):
    if not _is_admin(callback.from_user.id):
        await _refuse(callback)
        return
    preview = WELCOME_STORE.render(name="Teman", username="teman")
    banner = "terpasang" if WELCOME_STORE.banner_photo_file_id else "belum di-set"
    await send_html(callback.message,
                    f"<b>Sambutan saat ini (pratinjau):</b>\n\n{preview}\n\nBanner: {banner}")
    await callback.answer()


@router.callback_query(_WELCOME_RESET)
async def cb_welcome_reset(callback):
    if not _is_admin(callback.from_user.id):
        await _refuse(callback)
        return
    WELCOME_STORE.reset()
    await callback.message.answer("Sambutan dikembalikan ke default. Banner juga dihapus.")
    await callback.answer()


@router.callback_query(_WELCOME_CANCEL_CB)
async def cb_welcome_cancel(callback):
    if not _is_admin(callback.from_user.id):
        await _refuse(callback)
        return
    WELCOME_INPUT.cancel(callback.from_user.id)
    await callback.message.answer("Input sambutan/banner dibatalkan. Tidak ada yang diubah.")
    await callback.answer()


@router.callback_query(_BANNER_SET)
async def cb_banner_set(callback):
    if not _is_admin(callback.from_user.id):
        await _refuse(callback)
        return
    if not await _require_private(callback):
        return
    WELCOME_INPUT.start_banner(callback.from_user.id)
    await callback.message.answer(
        "Kirim foto banner untuk /start di chat pribadi ini.\n"
        "Foto terbesar yang kamu kirim akan dipakai sebagai banner. "
        "Tekan Batal untuk membatalkan.",
        reply_markup=admin_welcome_cancel_keyboard())
    await callback.answer()


@router.callback_query(_BANNER_DELETE)
async def cb_banner_delete(callback):
    if not _is_admin(callback.from_user.id):
        await _refuse(callback)
        return
    WELCOME_STORE.clear_banner()
    await callback.message.answer("Banner dihapus. /start akan kembali memakai kartu teks.")
    await callback.answer()


@router.message(_CANCEL_WELCOME)
async def on_cancel_welcome_input(message):
    WELCOME_INPUT.cancel(message.from_user.id)
    await message.answer("Input sambutan/banner dibatalkan. Tidak ada yang diubah.")


@router.message(_AWAITING_WELCOME)
async def on_welcome_text_input(message):
    uid = message.from_user.id
    if not _is_admin(uid):
        WELCOME_INPUT.cancel(uid)
        await message.answer(aks.NOT_ADMIN_MESSAGE)
        return
    if _chat_type(message) != "private":
        WELCOME_INPUT.cancel(uid)
        await message.answer("Kirim sambutan hanya di chat pribadi dengan bot.")
        return
    WELCOME_INPUT.cancel(uid)
    try:
        WELCOME_STORE.set_template(message.text or "")
    except ValueError as exc:
        await message.answer(str(exc))
        return
    preview = WELCOME_STORE.render(name="Teman", username="teman")
    await send_html(message, f"Sambutan tersimpan ✅\n\n<b>Pratinjau:</b>\n\n{preview}")


@router.message(_AWAITING_BANNER)
async def on_banner_photo_input(message):
    uid = message.from_user.id
    if not _is_admin(uid):
        WELCOME_INPUT.cancel(uid)
        await message.answer(aks.NOT_ADMIN_MESSAGE)
        return
    if _chat_type(message) != "private":
        WELCOME_INPUT.cancel(uid)
        await message.answer("Kirim banner hanya di chat pribadi dengan bot.")
        return
    file_id = _largest_photo_file_id(message)
    WELCOME_INPUT.cancel(uid)
    if not file_id:
        await message.answer("Foto tidak terbaca. Coba kirim ulang foto banner.")
        return
    WELCOME_STORE.set_banner(file_id)
    # Confirmation only: never echo the file_id back in full.
    await message.answer("Banner tersimpan ✅\nBanner akan tampil di /start berikutnya.")
