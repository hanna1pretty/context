"""Admin-panel Context.dev API key: masking, Fernet storage, admin-only
access, resolver order, and no-key-leak in formatted/logged output.

All keys below are obviously fake test values. No live Context.dev call,
no Postgres/Redis required.
"""
import asyncio
import os

import pytest

from app.contextdev.client import ContextDevClient
from app.contextdev.errors import ContextDevError
from app.services import admin_key_service as aks

FAKE_KEY = "ctxt_test_FAKEKEY_0001abcd"
FAKE_KEY_2 = "ctxt_test_FAKEKEY_0002wxyz"
ENV_KEY = "ctxt_test_ENVKEY_0003mnop"
ADMIN_ID = 111
OTHER_ID = 222
ADMINS = [ADMIN_ID]


@pytest.fixture()
def enc_key():
    return aks.generate_encryption_key()


@pytest.fixture()
def store():
    return aks.InMemoryAdminKeyStore()


def test_mask_shows_only_last_4():
    masked = aks.mask_api_key(FAKE_KEY)
    assert masked == "****abcd"
    assert FAKE_KEY not in masked
    assert "0001" not in masked
    assert aks.mask_api_key(None) == "<belum di-set>"
    assert aks.mask_api_key("abc") == "****"


def test_encrypt_decrypt_roundtrip_and_wrong_key_fails(enc_key, store):
    masked = aks.set_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                             plaintext=FAKE_KEY, encryption_key=enc_key)
    assert masked == "****abcd"
    token = store.get_encrypted(aks.KEY_NAME)
    assert token and token != FAKE_KEY and FAKE_KEY not in token
    assert aks.decrypt_api_key(token, enc_key) == FAKE_KEY
    with pytest.raises(ValueError, match="Gagal mendekripsi"):
        aks.decrypt_api_key(token, aks.generate_encryption_key())


def test_set_without_encryption_key_fails_and_stores_nothing(enc_key, store):
    with pytest.raises(RuntimeError, match="SETTINGS_ENCRYPTION_KEY"):
        aks.set_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                        plaintext=FAKE_KEY, encryption_key="")
    assert store.get_encrypted(aks.KEY_NAME) is None
    with pytest.raises(RuntimeError, match="SETTINGS_ENCRYPTION_KEY"):
        aks.set_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                        plaintext=FAKE_KEY, encryption_key=None)
    assert store.get_encrypted(aks.KEY_NAME) is None


def test_non_admin_refused_everywhere(enc_key, store):
    with pytest.raises(PermissionError, match="Tidak diizinkan"):
        aks.set_api_key(store, admin_id=OTHER_ID, admin_ids=ADMINS,
                        plaintext=FAKE_KEY, encryption_key=enc_key)
    with pytest.raises(PermissionError, match="Tidak diizinkan"):
        aks.get_masked_status(store, admin_id=OTHER_ID, admin_ids=ADMINS,
                              encryption_key=enc_key, env_key=ENV_KEY)
    with pytest.raises(PermissionError, match="Tidak diizinkan"):
        aks.delete_api_key(store, admin_id=OTHER_ID, admin_ids=ADMINS)
    assert store.get_encrypted(aks.KEY_NAME) is None


def test_resolver_prefers_stored_over_env(enc_key, store):
    aks.set_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                    plaintext=FAKE_KEY, encryption_key=enc_key)
    resolved = aks.resolve_api_key_from_store(store, enc_key, ENV_KEY)
    assert resolved == FAKE_KEY
    assert resolved != ENV_KEY


def test_resolver_falls_back_to_env(enc_key, store):
    assert aks.resolve_api_key_from_store(store, enc_key, ENV_KEY) == ENV_KEY


def test_resolver_errors_clearly_when_neither_exists(enc_key, store):
    with pytest.raises(aks.ApiKeyMissingError) as excinfo:
        aks.resolve_api_key_from_store(store, enc_key, "")
    assert "belum di-set" in str(excinfo.value)
    assert "/admin > Set Context API Key" in str(excinfo.value)


def test_client_attempts_no_call_without_key():
    # A fake transport that records calls: it must never be invoked.
    calls = []

    class FakeTransport:
        async def post(self, *a, **kw):
            calls.append(1)
            raise AssertionError("live call attempted without a key")

    client = ContextDevClient(api_key="", http_client=FakeTransport())
    with pytest.raises(ContextDevError, match="belum di-set"):
        asyncio.run(client.scrape("https://example.com"))
    assert calls == []


def test_set_status_output_never_contains_key(enc_key, store):
    masked = aks.set_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                             plaintext=FAKE_KEY, encryption_key=enc_key)
    saved = aks.saved_message(masked)
    status = aks.get_masked_status(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                                   encryption_key=enc_key, env_key=ENV_KEY)
    status_text = aks.status_message(status)
    audit = aks.audit_entry("admin_api_key_set", ADMIN_ID, masked)
    for text in (saved, status_text, str(audit)):
        assert FAKE_KEY not in text
        assert "0001" not in text
    assert "****abcd" in saved
    assert "****abcd" in status_text


def test_delete_then_resolver_falls_back_or_errors(enc_key, store):
    aks.set_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS,
                    plaintext=FAKE_KEY, encryption_key=enc_key)
    aks.delete_api_key(store, admin_id=ADMIN_ID, admin_ids=ADMINS)
    assert aks.resolve_api_key_from_store(store, enc_key, ENV_KEY) == ENV_KEY
    with pytest.raises(aks.ApiKeyMissingError):
        aks.resolve_api_key_from_store(store, enc_key, "")


def test_admin_input_state_start_cancel():
    state = aks.AdminKeyInputState()
    assert not state.is_awaiting(ADMIN_ID)
    state.start(ADMIN_ID)
    assert state.is_awaiting(ADMIN_ID)
    state.cancel(ADMIN_ID)
    assert not state.is_awaiting(ADMIN_ID)


def test_handler_flow_masks_and_deletes_input(monkeypatch):
    """Drive the real handler functions with fake Telegram objects."""
    from app.bot.handlers import admin as admin_mod

    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", str(ADMIN_ID))
    enc = aks.generate_encryption_key()
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", enc)
    monkeypatch.setenv("CONTEXT_DEV_API_KEY", "")
    admin_mod.KEY_STORE = aks.InMemoryAdminKeyStore()
    admin_mod.INPUT_STATE = aks.AdminKeyInputState()

    class FakeChat:
        type = "private"

    class FakeUser:
        id = ADMIN_ID

    class FakeMessage:
        def __init__(self, text):
            self.text = text
            self.from_user = FakeUser()
            self.chat = FakeChat()
            self.answers = []
            self.deleted = False

        async def answer(self, text, **kw):
            self.answers.append(text)

        async def delete(self):
            self.deleted = True

    admin_mod.INPUT_STATE.start(ADMIN_ID)
    msg = FakeMessage(FAKE_KEY)
    asyncio.run(admin_mod.on_admin_api_key_input(msg))
    assert msg.deleted is True
    assert not admin_mod.INPUT_STATE.is_awaiting(ADMIN_ID)
    assert any("****abcd" in a for a in msg.answers)
    assert all(FAKE_KEY not in a for a in msg.answers)
    # Stored value is ciphertext, resolvable back to the fake key.
    assert aks.resolve_api_key_from_store(admin_mod.KEY_STORE, enc, "") == FAKE_KEY


def test_handler_refuses_group_input_and_non_admin(monkeypatch):
    from app.bot.handlers import admin as admin_mod

    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", str(ADMIN_ID))
    monkeypatch.setenv("SETTINGS_ENCRYPTION_KEY", aks.generate_encryption_key())
    admin_mod.KEY_STORE = aks.InMemoryAdminKeyStore()
    admin_mod.INPUT_STATE = aks.AdminKeyInputState()

    class FakeChat:
        def __init__(self, t):
            self.type = t

    class FakeUser:
        def __init__(self, uid):
            self.id = uid

    class FakeMessage:
        def __init__(self, text, uid, chat_type):
            self.text = text
            self.from_user = FakeUser(uid)
            self.chat = FakeChat(chat_type)
            self.answers = []

        async def answer(self, text, **kw):
            self.answers.append(text)

        async def delete(self):
            pass

    # Group input from a real admin: NOT saved.
    admin_mod.INPUT_STATE.start(ADMIN_ID)
    msg = FakeMessage(FAKE_KEY_2, ADMIN_ID, "group")
    asyncio.run(admin_mod.on_admin_api_key_input(msg))
    assert admin_mod.KEY_STORE.get_encrypted(aks.KEY_NAME) is None
    assert any("TIDAK disimpan" in a for a in msg.answers)

    # Non-admin /admin: plain refusal.
    msg2 = FakeMessage("/admin", OTHER_ID, "private")
    asyncio.run(admin_mod.cmd_admin(msg2))
    assert msg2.answers == ["Tidak diizinkan."]


def test_worker_uses_resolver_and_missing_key_errors():
    """Worker path: resolver -> client; no resolver/key -> clear error, no call."""
    from app.workers.jobs import run_job

    class FakeClient:
        # Search (not scrape) so the test does not depend on DNS: the
        # worker re-validates URLs with real DNS, and this VM's resolver
        # maps example.com to a blocked IP, which the SSRF guard rejects.
        async def search(self, query, **kw):
            class R:
                title = "t"
                text = "body"
                items = []
                sources = []
                is_partial = False
                request_id = "r1"
                credits = None
            return R()

    async def _run(ctx, plan="pro"):
        return await run_job(ctx, kind="search", user_id=ADMIN_ID,
                             payload={"query": "test query"}, plan=plan)

    result = asyncio.run(_run({"context_api_key": FAKE_KEY,
                               "http_client": None, "client": FakeClient()}))
    assert result["kind"] == "search"
    with pytest.raises(ContextDevError, match="belum di-set"):
        asyncio.run(_run({}))
