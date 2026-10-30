"""Admin-panel Context.dev API key management.

Security invariants (never relax these):
- The full key is NEVER logged, NEVER put in an audit-log payload, NEVER
  put in a job result or an error message, and NEVER echoed back to chat.
  Only a masked form (``****`` + last 4 chars) is ever shown.
- Storage is Fernet-encrypted. If SETTINGS_ENCRYPTION_KEY is missing or
  invalid, setting a key FAILS -- there is no plaintext fallback.
- Admin checks live here, in the service layer (ADMIN_TELEGRAM_IDS),
  not in button visibility. Non-admins get a plain refusal, no hint.
- Resolution order at call time: (1) admin-panel stored key,
  (2) CONTEXT_DEV_API_KEY from env. If neither exists, no live call is
  attempted; callers get API_KEY_MISSING_MESSAGE.

This module is pure stdlib except for the ``cryptography`` import, which
is done lazily inside _fernet() so the module stays importable (and the
admin/permission/resolver logic testable) where cryptography is absent.
Encryption itself hard-fails in that case -- it never degrades to
plaintext.

Stores: two protocols are supported.
- Sync store (dev / in-memory / tests): an object with get_encrypted(name),
  set_encrypted(name, token, updated_by), delete(name). See
  InMemoryAdminKeyStore.
- Async repository (production Postgres): an object with async
  get_encrypted(name) / set_encrypted(name, token, updated_by) /
  delete(name). See app/db/repositories.py AdminSettingRepository and the
  async_* helpers below. The Telegram handler defaults to the in-memory
  store; main.py production wiring must replace it with the DB repository
  (documented gap in README/DECISIONS -- a key stored in-memory is lost
  on restart and is not shared between workers).
"""
from __future__ import annotations

import inspect

KEY_NAME = "context_dev_api_key"

API_KEY_MISSING_MESSAGE = (
    "API key Context.dev belum di-set. "
    "Admin: set di /admin > Set Context API Key."
)

ENCRYPTION_KEY_MISSING_MESSAGE = (
    "SETTINGS_ENCRYPTION_KEY belum di-set di server, jadi API key tidak "
    "bisa disimpan dengan aman. Set SETTINGS_ENCRYPTION_KEY di .env "
    "(lihat README) lalu coba lagi. Key tidak disimpan dalam bentuk "
    "plaintext."
)

NOT_ADMIN_MESSAGE = "Tidak diizinkan."


class ApiKeyMissingError(Exception):
    """Raised when neither a stored nor an env Context.dev key exists."""


def mask_api_key(value: str | None) -> str:
    """Masked form only: ``****`` + last 4 chars. Never the full key."""
    if not value:
        return "<belum di-set>"
    value = str(value)
    if len(value) <= 4:
        return "****"
    return "****" + value[-4:]


def require_admin(user_id: int, admin_ids) -> None:
    if user_id not in set(admin_ids or []):
        raise PermissionError(NOT_ADMIN_MESSAGE)


def _fernet(encryption_key: str | None):
    if not encryption_key:
        raise RuntimeError(ENCRYPTION_KEY_MISSING_MESSAGE)
    try:
        from cryptography.fernet import Fernet  # type: ignore
    except Exception as exc:  # pragma: no cover - missing dependency
        raise RuntimeError(
            "Paket 'cryptography' belum terinstall, jadi API key tidak "
            "bisa dienkripsi. Install requirements.txt lalu coba lagi. "
            "Key tidak disimpan dalam bentuk plaintext."
        ) from exc
    try:
        return Fernet(encryption_key.encode() if isinstance(encryption_key, str)
                      else encryption_key)
    except Exception as exc:
        raise ValueError(
            "SETTINGS_ENCRYPTION_KEY tidak valid. Generate yang baru "
            "(lihat README: Fernet.generate_key) lalu set ulang API key."
        ) from exc


def generate_encryption_key() -> str:
    from cryptography.fernet import Fernet  # type: ignore
    return Fernet.generate_key().decode()


def encrypt_api_key(plaintext: str, encryption_key: str | None) -> str:
    if not plaintext or not str(plaintext).strip():
        raise ValueError("API key kosong.")
    return _fernet(encryption_key).encrypt(str(plaintext).strip().encode()).decode()


def decrypt_api_key(token: str, encryption_key: str | None) -> str:
    from cryptography.fernet import InvalidToken  # type: ignore
    try:
        return _fernet(encryption_key).decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError(
            "Gagal mendekripsi API key tersimpan: SETTINGS_ENCRYPTION_KEY "
            "salah atau data rusak. Rotasi kunci enkripsi membuat key "
            "tersimpan lama tidak bisa dibaca -- set ulang API key."
        ) from exc


class InMemoryAdminKeyStore:
    """Dev/test store. NEVER use in multi-worker production (see module doc)."""

    def __init__(self):
        self._tokens: dict[str, str] = {}
        self._updated_by: dict[str, int] = {}

    def get_encrypted(self, name: str):
        return self._tokens.get(name)

    def set_encrypted(self, name: str, token: str, updated_by: int | None = None) -> None:
        self._tokens[name] = token
        if updated_by is not None:
            self._updated_by[name] = updated_by

    def delete(self, name: str) -> None:
        self._tokens.pop(name, None)
        self._updated_by.pop(name, None)


def audit_entry(action: str, admin_id: int, masked: str) -> dict:
    """Safe audit payload: action + admin id + masked form only. Never a key."""
    return {"action": action, "admin_id": admin_id, "api_key": masked}


def set_api_key(store, *, admin_id: int, admin_ids, plaintext: str,
                encryption_key: str | None) -> str:
    """Admin-only, encrypted save. Returns the masked form only."""
    require_admin(admin_id, admin_ids)
    token = encrypt_api_key(plaintext, encryption_key)
    store.set_encrypted(KEY_NAME, token, updated_by=admin_id)
    return mask_api_key(plaintext)


def get_api_key_status(store, *, admin_id: int, admin_ids) -> dict:
    require_admin(admin_id, admin_ids)
    token = store.get_encrypted(KEY_NAME)
    if not token:
        return {"configured": False, "masked": "<belum di-set>"}
    # Masking needs the plaintext, so status must NOT decrypt just to
    # display: we report configured-ness here; the masked form shown to
    # admins comes from set time / from resolve (see get_masked_status).
    return {"configured": True, "masked": "<tersimpan, terenkripsi>"}


def get_masked_status(store, *, admin_id: int, admin_ids,
                      encryption_key: str | None, env_key: str | None = None) -> dict:
    """Status with a real masked form (last 4 chars) when a key resolves."""
    require_admin(admin_id, admin_ids)
    try:
        key = resolve_api_key_from_store(store, encryption_key, env_key)
    except ApiKeyMissingError:
        return {"configured": False, "masked": "<belum di-set>", "source": None}
    return {"configured": True, "masked": mask_api_key(key),
            "source": "admin-panel" if store.get_encrypted(KEY_NAME) else "env"}


def delete_api_key(store, *, admin_id: int, admin_ids) -> None:
    require_admin(admin_id, admin_ids)
    store.delete(KEY_NAME)


def resolve_api_key(*, stored_encrypted: str | None,
                    encryption_key: str | None, env_key: str | None) -> str:
    """Order: stored (decrypted) -> env -> ApiKeyMissingError. No live call
    is attempted by callers when this raises."""
    if stored_encrypted:
        return decrypt_api_key(stored_encrypted, encryption_key)
    env = (env_key or "").strip()
    if env:
        return env
    raise ApiKeyMissingError(API_KEY_MISSING_MESSAGE)


def resolve_api_key_from_store(store, encryption_key: str | None,
                               env_key: str | None = None) -> str:
    return resolve_api_key(stored_encrypted=store.get_encrypted(KEY_NAME),
                           encryption_key=encryption_key, env_key=env_key)


async def resolve_api_key_from_repository(repository, encryption_key: str | None,
                                          env_key: str | None = None) -> str:
    """Async (Postgres) variant: repository.get_encrypted(KEY_NAME)."""
    token = repository.get_encrypted(KEY_NAME)
    if inspect.isawaitable(token):
        token = await token
    return resolve_api_key(stored_encrypted=token,
                           encryption_key=encryption_key, env_key=env_key)


async def set_api_key_in_repository(repository, *, admin_id: int, admin_ids,
                                    plaintext: str,
                                    encryption_key: str | None) -> str:
    require_admin(admin_id, admin_ids)
    token = encrypt_api_key(plaintext, encryption_key)
    result = repository.set_encrypted(KEY_NAME, token, updated_by=admin_id)
    if inspect.isawaitable(result):
        await result
    return mask_api_key(plaintext)


async def delete_api_key_in_repository(repository, *, admin_id: int,
                                       admin_ids) -> None:
    require_admin(admin_id, admin_ids)
    result = repository.delete(KEY_NAME)
    if inspect.isawaitable(result):
        await result


class AdminKeyInputState:
    """Which admins are mid-way through entering a key (in-process only;
    production multi-worker deployments must move this to Redis FSM --
    see README/DECISIONS)."""

    def __init__(self):
        self._awaiting: set[int] = set()

    def start(self, admin_id: int) -> None:
        self._awaiting.add(admin_id)

    def cancel(self, admin_id: int) -> None:
        self._awaiting.discard(admin_id)

    def is_awaiting(self, admin_id: int) -> bool:
        return admin_id in self._awaiting


def set_prompt_text() -> str:
    return (
        "Kirim API key Context.dev di CHAT PRIBADI ini saja.\n"
        "JANGAN kirim di grup -- key yang terkirim di grup tidak bisa "
        "ditarik kembali.\n"
        "Bot akan mencoba menghapus pesan input kamu setelah tersimpan, "
        "tapi hapus juga manual dari riwayat chat kamu untuk aman.\n"
        "Bot TIDAK PERNAH menampilkan kembali key lengkapnya, hanya "
        "bentuk tersamar (**** + 4 karakter terakhir).\n"
        "Tekan Batal atau kirim /cancel untuk membatalkan."
    )


def saved_message(masked: str) -> str:
    return f"API key tersimpan: {masked}"


def status_message(status: dict) -> str:
    if not status["configured"]:
        return ("Status API key Context.dev: belum di-set.\n"
                "Admin: set di /admin > Set Context API Key.")
    return (f"Status API key Context.dev: tersimpan "
            f"(sumber: {status.get('source') or 'tersimpan'}).\n"
            f"Bentuk tersamar: {status['masked']}\n"
            "Key lengkap tidak pernah ditampilkan.")
