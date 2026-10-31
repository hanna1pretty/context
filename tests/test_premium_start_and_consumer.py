"""Fake-object tests for the live bug fixes (no aiogram, no network,
no Postgres/Redis, no real secrets anywhere):

- nav callbacks answer first even when edit raises, and fall back
  to a new message instead of a dead button;
- every main-menu / help nav screen renders with parse_mode HTML;
- a queued scrape job is consumed and delivered as a result (not
  stuck at "memproses"), and a missing-key job as a clear failure;
- premium /start (text + banner photo paths) and admin welcome/banner
  flows work with fake objects.
"""
from __future__ import annotations

import asyncio

import pytest

from app.bot.formatters import truncate_caption, welcome_text
from app.bot.handlers import admin as admin_h
from app.bot.handlers import navigation as nav_h
from app.bot.handlers import start as start_h
from app.bot.handlers._common import send_html
from app.services.welcome_service import WelcomeStore
from app.workers.consumer import consume_one
from app.workers.queue import QUEUE, InMemoryQueue

_TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAwMCAO+ip1sAAAAASUVORK5CYII="
)


class FakeUser:
    def __init__(self, uid=111, first_name="Hanna", username="hanna"):
        self.id = uid
        self.first_name = first_name
        self.username = username


class FakeChat:
    def __init__(self, type="private"):
        self.type = type


class FakeMessage:
    def __init__(self, text="", user=None, chat=None, photo=None, fail_edit=False):
        self.text = text
        self.from_user = user or FakeUser()
        self.chat = chat or FakeChat()
        self.photo = photo
        self.fail_edit = fail_edit
        self.sent = []      # (text, reply_markup, parse_mode)
        self.edits = []     # (text, reply_markup, parse_mode)
        self.photos = []    # (file_id, caption, reply_markup, parse_mode)
        self.deleted = False

    async def answer(self, text, reply_markup=None, parse_mode=None, **kw):
        self.sent.append((text, reply_markup, parse_mode))

    async def edit_text(self, text, reply_markup=None, parse_mode=None, **kw):
        if self.fail_edit:
            raise RuntimeError("MessageNotModified")
        self.edits.append((text, reply_markup, parse_mode))

    async def answer_photo(self, file_id, caption=None, reply_markup=None,
                           parse_mode=None, **kw):
        self.photos.append((file_id, caption, reply_markup, parse_mode))

    async def delete(self):
        self.deleted = True


class FakeCallback:
    def __init__(self, data, message=None, user=None):
        self.data = data
        self.message = message or FakeMessage()
        self.from_user = user or FakeUser()
        self.answered = []  # (text, show_alert)

    async def answer(self, text=None, show_alert=False):
        self.answered.append((text, show_alert))


class FakeBot:
    def __init__(self):
        self.messages = []  # (user_id, text, parse_mode)
        self.photos = []    # (user_id, photo, caption, parse_mode)

    async def send_message(self, user_id, text, parse_mode=None, **kw):
        self.messages.append((user_id, text, parse_mode))

    async def send_photo(self, user_id, photo, caption=None, parse_mode=None, **kw):
        self.photos.append((user_id, photo, caption, parse_mode))


def run(coro):
    return asyncio.get_event_loop_policy().new_event_loop().run_until_complete(coro)


# ---------- welcome text ----------
def test_welcome_text_escapes_name_and_has_no_channel_join():
    text = welcome_text("<script>alert(1)</script>", "hanna")
    assert "<script>" not in text
    assert "&lt;script&gt;" in text
    assert "OktaScrape" in text
    assert "Halo" in text
    for banned in ("channel", "verifikasi akses", "join", "bergabung"):
        assert banned.lower() not in text.lower()


def test_welcome_text_template_placeholders():
    text = welcome_text("Hanna", "hanna", template="Hai {nama} (@{username}) di {bot}")
    assert "Hai Hanna" in text
    assert "@hanna" in text
    assert "OktaScrape" in text


def test_truncate_caption_respects_1024_and_no_dangling_tag():
    long_text = "<b>" + "x" * 2000 + "</b>"
    out = truncate_caption(long_text)
    assert len(out) <= 1024
    assert out.count("<") == out.count(">") or out.endswith("…")


# ---------- send_html / send_welcome ----------
def test_send_html_always_sets_parse_mode():
    msg = FakeMessage()
    run(send_html(msg, "<b>halo</b>"))
    assert msg.sent[0][2] == "HTML"
    assert "<b>halo</b>" in msg.sent[0][0]


def test_send_welcome_text_path(monkeypatch):
    monkeypatch.delenv("BOT_DISPLAY_NAME", raising=False)
    msg = FakeMessage(user=FakeUser(first_name="Hanna", username="hanna"))
    result = run(start_h.send_welcome(msg, is_admin=False, welcome_store=WelcomeStore()))
    assert result == "text"
    assert msg.sent and msg.sent[0][2] == "HTML"
    assert "Halo, Hanna" in msg.sent[0][0]
    assert "OktaScrape" in msg.sent[0][0]
    assert msg.sent[0][1] is not None  # main menu keyboard attached


def test_send_welcome_photo_path():
    store = WelcomeStore()
    store.set_banner("banner_file_id_only_in_test")
    msg = FakeMessage(user=FakeUser(first_name="Hanna", username="hanna"))
    result = run(start_h.send_welcome(msg, is_admin=False, welcome_store=store))
    assert result == "photo"
    assert msg.photos
    assert msg.photos[0][0] == "banner_file_id_only_in_test"
    assert len(msg.photos[0][1]) <= 1024
    assert "Halo, Hanna" in msg.photos[0][1]


# ---------- nav failure path ----------
def test_edit_or_send_falls_back_to_new_message_when_edit_raises():
    msg = FakeMessage(fail_edit=True)
    result = run(nav_h.edit_or_send(msg, "<b>layar</b>"))
    assert result == "sent"
    assert msg.sent and msg.sent[0][0] == "<b>layar</b>"
    assert msg.sent[0][2] == "HTML"


def test_nav_callback_answers_first_even_when_edit_raises():
    msg = FakeMessage(fail_edit=True)
    cb = FakeCallback("nav:v1:home", message=msg)
    run(nav_h.on_nav_callback(cb))
    assert cb.answered  # spinner answered, not stuck
    assert msg.sent  # fallback message delivered, not swallowed


def test_every_main_menu_and_help_screen_renders():
    for screen in ("home", "scrape", "search", "crawl", "map", "answers",
                   "parse", "intelligence", "news", "batches", "usage",
                   "plan", "settings", "help", "help_commands",
                   "help_examples", "help_status", "help_privacy"):
        msg = FakeMessage()
        cb = FakeCallback(f"nav:v1:screen:{screen}", message=msg)
        run(nav_h.on_nav_callback(cb))
        assert cb.answered, screen
        rendered = msg.edits or msg.sent
        assert rendered, screen
        assert rendered[0][2] == "HTML", screen


# ---------- on_text must not swallow commands ----------
def test_on_text_ignores_commands():
    msg = FakeMessage(text="/scrape https://example.com")
    run(start_h.on_text(msg))
    assert msg.sent == []


def test_on_text_bare_url_offers_choices():
    msg = FakeMessage(text="https://example.com")
    run(start_h.on_text(msg))
    assert msg.sent and "URL diterima" in msg.sent[0][0]


# ---------- consumer ----------
def test_consumer_delivers_scrape_result_not_memproses():
    q = InMemoryQueue()
    q.enqueue("scrape", 111, {"url": "https://example.com"})
    bot = FakeBot()

    async def fake_run(ctx, *, kind, user_id, payload):
        return {"kind": kind, "title": "Example Domain", "text": "Contoh isi halaman.",
                "items": [], "sources": ["https://example.com"],
                "is_partial": False, "request_id": "req-1", "credits_consumed": 1}

    run(consume_one(bot, queue=q, run_job_fn=fake_run))
    texts = [t for _, t, _ in bot.messages]
    assert any("Mengerjakan" in t for t in texts)
    assert any("Example Domain" in t for t in texts)
    assert any("req-1" in t for t in texts)
    assert q.depth() == 0


def test_consumer_missing_key_becomes_clear_failure():
    q = InMemoryQueue()
    q.enqueue("scrape", 111, {"url": "https://example.com"})
    bot = FakeBot()

    async def fake_run(ctx, *, kind, user_id, payload):
        raise RuntimeError("API key Context.dev belum di-set. Admin: set di /admin > Set Context API Key.")

    run(consume_one(bot, queue=q, run_job_fn=fake_run))
    texts = [t for _, t, _ in bot.messages]
    assert any("/admin" in t for t in texts)
    assert not any("Example Domain" in t for t in texts)


def test_consumer_delivers_screenshot_as_photo():
    q = InMemoryQueue()
    q.enqueue("scrape", 111, {"url": "https://example.com", "mode": "screenshot"})
    bot = FakeBot()

    async def fake_run(ctx, *, kind, user_id, payload):
        return {"kind": kind, "title": "Example Domain", "text": "Contoh isi.",
                "items": [], "sources": [], "is_partial": False,
                "request_id": "req-9", "credits_consumed": 1,
                "screenshot_success": True, "screenshot_data_url_present": True,
                "screenshot_data_url": _TINY_PNG}

    run(consume_one(bot, queue=q, run_job_fn=fake_run))
    assert bot.photos
    caption = bot.photos[0][2]
    assert "Example Domain" in caption
    assert "data:image" not in caption  # raw data URL never captioned
    assert any("Example Domain" in t for _, t, _ in bot.messages)


# ---------- admin welcome / banner flows ----------
def test_admin_welcome_and_banner_flows(monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "111")
    admin_h.WELCOME_STORE.reset()
    admin_h.WELCOME_INPUT.cancel(111)
    try:
        admin = FakeUser(uid=111)
        msg = FakeMessage(user=admin)
        cb = FakeCallback("admin:v1:welcome_set", message=msg, user=admin)
        run(admin_h.cb_welcome_set(cb))
        assert admin_h.WELCOME_INPUT.is_awaiting_template(111)

        text_msg = FakeMessage(text="Hai {nama}, selamat datang 👋", user=admin)
        run(admin_h.on_welcome_text_input(text_msg))
        assert admin_h.WELCOME_STORE.template == "Hai {nama}, selamat datang 👋"
        assert any("tersimpan" in t for t, _, _ in text_msg.sent)

        msg2 = FakeMessage(user=admin)
        cb2 = FakeCallback("admin:v1:banner_set", message=msg2, user=admin)
        run(admin_h.cb_banner_set(cb2))
        assert admin_h.WELCOME_INPUT.is_awaiting_banner(111)

        photo_msg = FakeMessage(user=admin, photo=[{"file_id": "banner_file_id_only_in_test"}])
        run(admin_h.on_banner_photo_input(photo_msg))
        assert admin_h.WELCOME_STORE.banner_photo_file_id == "banner_file_id_only_in_test"
        assert any("Banner tersimpan" in t for t, _, _ in photo_msg.sent)
        assert not any("banner_file_id_only_in_test" in t for t, _, _ in photo_msg.sent)

        show_msg = FakeMessage(user=admin)
        cb3 = FakeCallback("admin:v1:welcome_show", message=show_msg, user=admin)
        run(admin_h.cb_welcome_show(cb3))
        assert any("Teman" in t for t, _, _ in show_msg.sent)
    finally:
        admin_h.WELCOME_STORE.reset()
        admin_h.WELCOME_INPUT.cancel(111)


def test_admin_welcome_rejects_non_admin(monkeypatch):
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "111")
    admin_h.WELCOME_STORE.reset()
    msg = FakeMessage(user=FakeUser(uid=999))
    cb = FakeCallback("admin:v1:welcome_set", message=msg, user=FakeUser(uid=999))
    run(admin_h.cb_welcome_set(cb))
    assert not admin_h.WELCOME_INPUT.is_awaiting_template(999)
    admin_h.WELCOME_STORE.reset()
