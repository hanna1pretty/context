"""Screenshot support: normalizer, data-URL parser, client, worker,
mode mapping, and photo-delivery helper. Mocks/fakes only, no live
Context.dev, no Postgres/Redis. Test data URLs are tiny fake 1x1 PNGs.
"""
import asyncio
import base64

import pytest

from app.bot.callbacks.scrape import scrape_mode_to_formats as cb_mode_to_formats
from app.bot.handlers.scrape import scrape_job_payload
from app.contextdev.client import ContextDevClient, _Response
from app.contextdev.formats import scrape_mode_to_formats
from app.contextdev.result_normalizer import normalize_scrape, normalize_scrape_typed
from app.contextdev.screenshot import (
    MAX_DECODED_BYTES,
    ScreenshotError,
    ScreenshotOversizeError,
    parse_data_url,
)
from app.services.screenshot_delivery import prepare_screenshot_message

# Tiny fake 1x1 PNG (transparent), JPEG/WebP are represented by the
# same 1x1 PNG bytes under a different mime in the data URL — the
# parser validates mime + base64 + size, not image magic bytes.
PNG_1X1_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAwMCAO+ip1sAAAAASUVORK5CYII="
)


def _data_url(mime="image/png", b64=PNG_1X1_B64):
    return f"data:{mime};base64,{b64}"


def _shot_payload(data_url=None, success=True, **extra):
    shot = {"requested": True, "success": success}
    if data_url is not None:
        shot["data"] = data_url
    shot.update(extra)
    return {"url": "https://example.com", "markdown": {"data": "# Hi"},
            "metadata": {"title": "Example"}, "request_id": "req-shot",
            "key_metadata": {"credits_consumed": 1},
            "screenshot": shot, "isPartial": False}


# --- normalizer ---

def test_normalizer_screenshot_success():
    n = normalize_scrape(_shot_payload(_data_url()))
    assert n.screenshot_success is True
    assert n.screenshot_data_url == _data_url()
    assert n.text == "# Hi" and not n.is_partial
    t = normalize_scrape_typed(_shot_payload(_data_url()))
    assert t.screenshot_success is True and t.screenshot_data_url == _data_url()


def test_normalizer_screenshot_failed_never_claims_success():
    n = normalize_scrape(_shot_payload(_data_url(), success=False))
    assert n.screenshot_success is False and n.screenshot_data_url is None


def test_normalizer_screenshot_not_requested():
    n = normalize_scrape({"markdown": {"data": "x"}})
    assert n.screenshot_success is None and n.screenshot_data_url is None


def test_normalizer_screenshot_non_image_data_url_rejected():
    # success=True but data is not a data:image/... URL: unusable.
    n = normalize_scrape(_shot_payload("https://example.com/shot.png", success=True))
    assert n.screenshot_success is False and n.screenshot_data_url is None
    n2 = normalize_scrape(_shot_payload("data:text/plain;base64,aGk=", success=True))
    assert n2.screenshot_success is False and n2.screenshot_data_url is None
    n3 = normalize_scrape(_shot_payload(None, success=True))
    assert n3.screenshot_success is False and n3.screenshot_data_url is None


def test_normalizer_partial_still_honest_with_screenshot():
    payload = _shot_payload(_data_url())
    payload["isPartial"] = True
    n = normalize_scrape(payload)
    assert n.is_partial and n.screenshot_success is True


# --- parse_data_url ---

def test_parse_valid_png_jpeg_webp():
    for mime in ("image/png", "image/jpeg", "image/webp"):
        m, raw = parse_data_url(_data_url(mime))
        assert m == mime and raw == base64.b64decode(PNG_1X1_B64)


def test_parse_corrupt_base64_rejected():
    with pytest.raises(ScreenshotError):
        parse_data_url("data:image/png;base64,!!!not-base64!!!")


def test_parse_non_image_mime_rejected():
    with pytest.raises(ScreenshotError):
        parse_data_url("data:text/plain;base64,aGk=")
    with pytest.raises(ScreenshotError):
        parse_data_url("data:image/svg+xml;base64,aGk=")


def test_parse_non_base64_and_missing_payload_rejected():
    with pytest.raises(ScreenshotError):
        parse_data_url("data:image/png,aaaa")
    with pytest.raises(ScreenshotError):
        parse_data_url("data:image/png;base64,")
    with pytest.raises(ScreenshotError):
        parse_data_url("https://example.com/shot.png")


def test_parse_oversized_rejected():
    big = base64.b64encode(b"\x00" * (MAX_DECODED_BYTES + 1)).decode()
    with pytest.raises(ScreenshotOversizeError):
        parse_data_url(f"data:image/png;base64,{big}")


# --- client ---

class _FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.last_json = None
        self.last_url = None

    async def post(self, url, *, json, headers, timeout):
        self.last_url = url
        self.last_json = json
        return _Response(200, {}, self.payload)


@pytest.mark.asyncio
async def test_client_scrape_screenshot_sends_exact_formats():
    tr = _FakeTransport(_shot_payload(_data_url()))
    client = ContextDevClient(api_key="k", http_client=tr)
    res = await client.scrape_screenshot("https://example.com")
    assert tr.last_url.endswith("/web/scrape")
    assert tr.last_json == {"url": "https://example.com",
                            "formats": {"screenshot": True, "markdown": True}}
    assert res.screenshot_success is True
    assert res.screenshot_data_url == _data_url()
    assert res.credits.consumed == 1


@pytest.mark.asyncio
async def test_client_scrape_screenshot_params_only_with_screenshot():
    tr = _FakeTransport(_shot_payload(_data_url()))
    client = ContextDevClient(api_key="k", http_client=tr)
    await client.scrape_screenshot("https://example.com",
                                   screenshot_params={"fullPage": True})
    assert tr.last_json["screenshotParams"] == {"fullPage": True}
    assert tr.last_json["formats"]["screenshot"] is True


# --- worker ---

@pytest.mark.asyncio
async def test_worker_scrape_with_screenshot_formats(monkeypatch):
    from app.workers import jobs as jobs_mod
    from app.contextdev.models import NormalizedResult

    monkeypatch.setattr(jobs_mod, "validate_url", lambda url: None)

    class FakeClient:
        async def scrape(self, url, **kw):
            assert kw.get("formats") == {"screenshot": True, "markdown": True}
            return NormalizedResult(
                kind="scrape", title="Example", text="# Hi",
                sources=[url], request_id="req-shot",
                screenshot_data_url=_data_url(), screenshot_success=True)

    out = await jobs_mod.run_job(
        {"client": FakeClient()}, kind="scrape", user_id=1,
        payload={"url": "https://example.com",
                 "formats": {"screenshot": True, "markdown": True}},
        plan="pro")
    assert out["screenshot_success"] is True
    assert out["screenshot_data_url_present"] is True
    assert out["screenshot_data_url"] == _data_url()


@pytest.mark.asyncio
async def test_worker_scrape_mode_translates_to_formats(monkeypatch):
    from app.workers import jobs as jobs_mod
    from app.contextdev.models import NormalizedResult

    monkeypatch.setattr(jobs_mod, "validate_url", lambda url: None)

    seen = {}

    class FakeClient:
        async def scrape(self, url, **kw):
            seen.update(kw)
            return NormalizedResult(kind="scrape", title="T", text="x")

    await jobs_mod.run_job(
        {"client": FakeClient()}, kind="scrape", user_id=1,
        payload={"url": "https://example.com", "mode": "screenshot"},
        plan="pro")
    assert seen["formats"] == {"screenshot": True, "markdown": True}
    assert "mode" not in seen


# --- mode mapping ---

def test_mode_to_formats_all_modes():
    assert scrape_mode_to_formats("markdown") == {"markdown": True}
    assert scrape_mode_to_formats("html") == {"html": True}
    assert scrape_mode_to_formats("screenshot") == {"screenshot": True, "markdown": True}
    assert scrape_mode_to_formats("json") == {"json": True}
    assert scrape_mode_to_formats("highlights") == {"highlights": True}
    assert scrape_mode_to_formats("fresh") == {"markdown": True}
    # Same mapping via the bot callback module (re-exported).
    assert cb_mode_to_formats("screenshot") == {"screenshot": True, "markdown": True}
    with pytest.raises(ValueError):
        scrape_mode_to_formats("bogus")
    # Fresh copies: mutating one result must not pollute the next.
    a = scrape_mode_to_formats("screenshot")
    a["screenshot"] = False
    assert scrape_mode_to_formats("screenshot")["screenshot"] is True


def test_scrape_job_payload_uses_mapping():
    assert scrape_job_payload("https://example.com", "screenshot") == {
        "url": "https://example.com",
        "formats": {"screenshot": True, "markdown": True}}
    assert scrape_job_payload("https://example.com")["formats"] == {"markdown": True}


# --- delivery helper ---

def test_delivery_photo_success_caption_never_contains_data_url():
    from app.contextdev.models import NormalizedResult
    from app.contextdev.models import CreditInfo

    res = NormalizedResult(
        kind="scrape", title="Example", text="# Hi",
        sources=["https://example.com"], request_id="req-shot",
        credits=CreditInfo(consumed=1),
        screenshot_data_url=_data_url(), screenshot_success=True)
    msg = prepare_screenshot_message(res)
    assert msg["kind"] == "photo"
    assert msg["mime"] == "image/png"
    assert msg["bytes"] == base64.b64decode(PNG_1X1_B64)
    assert "data:image/" not in msg["caption"]
    assert "Example" in msg["caption"] and "req-shot" in msg["caption"]


def test_delivery_fallback_failed_includes_markdown():
    from app.contextdev.models import NormalizedResult

    res = NormalizedResult(kind="scrape", title="T", text="# Fallback",
                           screenshot_data_url=None, screenshot_success=False)
    msg = prepare_screenshot_message(res)
    assert msg["kind"] == "fallback_text"
    assert "gagal" in msg["text"] and "# Fallback" in msg["text"]


def test_delivery_fallback_missing_and_oversized():
    from app.contextdev.models import NormalizedResult

    missing = NormalizedResult(kind="scrape", text="# Md")
    msg = prepare_screenshot_message(missing)
    assert msg["kind"] == "fallback_text" and "# Md" in msg["text"]

    big = base64.b64encode(b"\x00" * (MAX_DECODED_BYTES + 1)).decode()
    over = NormalizedResult(
        kind="scrape", text="# Md",
        screenshot_data_url=f"data:image/png;base64,{big}",
        screenshot_success=True)
    msg2 = prepare_screenshot_message(over)
    assert msg2["kind"] == "fallback_text"
    assert "melebihi batas" in msg2["text"] and "# Md" in msg2["text"]
    assert "data:image/" not in msg2["text"]


def test_delivery_fallback_from_worker_summary_dict():
    # Worker summary dicts carry only the bool, not the data URL.
    msg = prepare_screenshot_message(
        {"title": "T", "text": "# Md", "screenshot_data_url_present": True,
         "screenshot_success": True, "screenshot_data_url": None})
    assert msg["kind"] == "fallback_text"
