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
from ..keyboards import admin_cancel_keyboard, admin_menu
from ...services import admin_key_service as aks

router = get_router()

KEY_STORE = aks.InMemoryAdminKeyStore()
INPUT_STATE = aks.AdminKeyInputState()

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

    _CMD = _C("admin")
    _SET = _F.data == "admin:set_api_key"
    _STATUS = _F.data == "admin:api_key_status"
    _DELETE = _F.data == "admin:delete_api_key"
    _CANCEL_CB = _F.data == "admin:cancel_api_key"
    _AWAITING = _AwaitingApiKeyFilter()
    _CANCEL = _CancelApiKeyFilter()
except Exception:  # pragma: no cover - aiogram absent (stub router)
    _CMD = _SET = _STATUS = _DELETE = _CANCEL_CB = _AWAITING = _CANCEL = None


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
