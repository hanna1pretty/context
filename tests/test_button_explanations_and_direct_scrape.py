"""Regression tests for the 2026-10-31 user report:
- /scrape of a previously scraped URL stayed at "Antrian diterima"
  forever (fake dup- job id, nothing ever enqueued).
- Main-menu buttons showed no explanation of what the feature is.
- Scrape had no visible running progress, only a static queue ack.
Fakes only, no network, no aiogram (suite runs with aiogram absent).
"""
import asyncio

import pytest

from app.bot.handlers import scrape as scrape_mod
from app.bot.handlers._common import accept
from app.bot.handlers.feature_callbacks import process_callback
from app.bot.handlers.navigation import render_screen
from app.workers.queue import QUEUE, InMemoryQueue


def test_queue_releases_key_when_job_is_popped():
    q = InMemoryQueue()
    first = q.enqueue("scrape", 7, {"url": "https://example.com"})
    assert first["duplicate"] is False
    again = q.enqueue("scrape", 7, {"url": "https://example.com"})
    assert again["duplicate"] is True
    assert again["job_id"] == first["job_id"]
    assert not again["job_id"].startswith("dup-")
    q.pop()
    third = q.enqueue("scrape", 7, {"url": "https://example.com"})
    assert third["duplicate"] is False


def test_accept_does_not_lie_about_a_duplicate():
    async def run():
        class FakeUser:
            id = 4242

        class FakeMessage:
            def __init__(self):
                self.from_user = FakeUser()
                self.sent = []

            async def answer(self, text, reply_markup=None, parse_mode=None):
                self.sent.append(text)

        msg = FakeMessage()
        await accept(msg, "search", {"query": "same query"})
        await accept(msg, "search", {"query": "same query"})
        assert "Antrian diterima" in msg.sent[0]
        assert "sudah berjalan" in msg.sent[1]
        assert "Antrian diterima" not in msg.sent[1]
        QUEUE.pop()

    asyncio.run(run())


def test_scrape_mode_button_returns_a_visible_notice():
    outcome = process_callback("scrape:v1:mode:markdown", user_id=5)
    assert outcome["status"] == "ok"
    assert "Mode" in outcome["notice"]
    assert "/scrape" in outcome["notice"]


class FakeProgress:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.edits.append(text)


class FakeScrapeMessage:
    def __init__(self):
        class U:
            id = 99

        self.from_user = U()
        self.text = "/scrape https://example.com"
        self.sent = []
        self.progress = None

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append(text)
        if self.progress is None:
            self.progress = FakeProgress()
            return self.progress
        return FakeProgress()


def test_scrape_runs_directly_with_staged_progress_and_result(monkeypatch):
    async def fake_run(ctx, kind, user_id, payload):
        assert kind == "scrape"
        assert payload["url"] == "https://example.com"
        return {"title": "Example", "text": "Hello world", "sources": ["https://example.com"]}

    monkeypatch.setattr(scrape_mod, "run_job_with_timeout", fake_run)
    msg = FakeScrapeMessage()
    asyncio.run(scrape_mod.cmd_scrape(msg))
    all_text = "\n".join(msg.sent) + "\n" + "\n".join(msg.progress.edits)
    assert "Tahap 2/3" in all_text
    assert "Hasil scrape" in all_text
    assert "Example" in all_text
    assert "Antrian diterima" not in all_text
    assert "mengantre" not in all_text


class FakePhotoMessage:
    def __init__(self):
        self.photo = ["photo-id"]
        self.captions = []
        self.edits = []

    async def edit_caption(self, caption=None, reply_markup=None, parse_mode=None):
        self.captions.append(caption)

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        self.edits.append(text)

    async def answer(self, text, reply_markup=None, parse_mode=None):
        pass


class FakeCallback:
    def __init__(self, message):
        class U:
            id = 77

        self.from_user = U()
        self.message = message
        self.data = "nav:v1:screen:scrape"

    async def answer(self, text=None, show_alert=False):
        pass


def test_nav_from_photo_welcome_edits_caption_not_text():
    msg = FakePhotoMessage()
    cb = FakeCallback(msg)
    asyncio.run(render_screen(cb, "scrape", {"user_id": 77}))
    assert msg.captions, "photo welcome must be updated via caption"
    assert not msg.edits
    assert "Scrape URL" in msg.captions[0]
    assert "ini apa" in msg.captions[0]


def test_brand_screen_is_not_empty_when_no_fields():
    class FakeTextMessage:
        def __init__(self):
            self.edits = []

        async def edit_text(self, text, reply_markup=None, parse_mode=None):
            self.edits.append(text)

        async def answer(self, text, reply_markup=None, parse_mode=None):
            pass

    msg = FakeTextMessage()
    cb = FakeCallback(msg)
    asyncio.run(render_screen(cb, "brand", {"user_id": 77}))
    assert msg.edits
    assert "Brand" in msg.edits[0]
    assert "/brand" in msg.edits[0]
