"""Inline-keyboard system tests (spec sections 5-23).

Mocks/fakes only: no live Context.dev, no Postgres/Redis, no aiogram
(the suite runs with aiogram absent; keyboards fall back to dict rows).
"""
import re
import time

import pytest

from app.bot.callbacks import (
    CursorStore,
    DoubleClickGuard,
    NavState,
    is_expired,
    is_recognized,
    parse_callback,
    validate_callback,
)
from app.bot.callbacks.base import LEGACY_CALLBACKS
from app.bot.callbacks.navigation import SCREEN_IDS
from app.bot.formatters import (
    bold,
    code,
    escape_html,
    format_normalized,
    italic,
    link,
    pre,
    quote,
    redact_secrets,
    safe_url,
    split_html_message,
    truncate_for_telegram,
)
from app.bot.formatters import messages as msg
from app.bot.formatters.telegram_markdown import escape_markdown, link_md
from app.bot.handlers.feature_callbacks import process_callback
from app.bot.handlers.navigation import (
    SCREENS,
    edit_or_send,
    get_nav_state,
    go_back,
    go_home,
    render_screen,
    show_error,
)
from app.bot.keyboards import (
    admin_dashboard_keyboard,
    admin_menu,
    answers_menu,
    answers_result_keyboard,
    batches_menu,
    batch_actions,
    brand_menu,
    button_texts,
    company_menu,
    crawl_confirm_keyboard,
    crawl_menu,
    error_keyboard,
    extract_buttons,
    help_menu,
    intelligence_menu,
    iter_callbacks,
    job_actions,
    job_center_menu,
    job_list_keyboard,
    locked_feature_keyboard,
    main_menu,
    map_menu,
    map_results_keyboard,
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
    news_menu,
    news_results_keyboard,
    settings_clear_confirm_keyboard,
    settings_delete_confirm_keyboard,
    settings_language_keyboard,
    settings_menu,
    url_choices,
    usage_keyboard,
)
from app.workers.queue import InMemoryQueue


# ---------------------------------------------------------------- fakes
class FakeUser:
    def __init__(self, uid):
        self.id = uid


class FakeMessage:
    def __init__(self, fail_edit=False):
        self.sent = []
        self.edits = []
        self.fail_edit = fail_edit

    async def answer(self, text, reply_markup=None, parse_mode=None):
        self.sent.append((text, reply_markup))

    async def edit_text(self, text, reply_markup=None, parse_mode=None):
        if self.fail_edit:
            raise RuntimeError("MessageNotModified")
        self.edits.append((text, reply_markup))


class FakeCallback:
    def __init__(self, uid, data, fail_edit=False):
        self.from_user = FakeUser(uid)
        self.data = data
        self.message = FakeMessage(fail_edit=fail_edit)
        self.answered = []

    async def answer(self, text=None, show_alert=False):
        self.answered.append((text, show_alert))


def rows_of(markup):
    rows = getattr(markup, "inline_keyboard", None)
    if rows is None:
        rows = markup
    out = []
    for row in rows:
        if isinstance(row, dict):
            out.append([row])
        else:
            out.append([{"text": getattr(b, "text", b.get("text") if isinstance(b, dict) else ""),
                         "callback_data": getattr(b, "callback_data", b.get("callback_data") if isinstance(b, dict) else "")}
                        for b in row])
    return out


ALL_KEYBOARDS = [
    main_menu(), main_menu(is_admin=True), url_choices("https://example.com"),
    admin_menu(), admin_dashboard_keyboard(),
    scrape_menu(), scrape_confirm_keyboard(), search_menu(),
    search_results_keyboard(1, 3, 3), search_results_keyboard(3, 3, 2),
    crawl_menu(), crawl_confirm_keyboard(), map_menu(), map_menu(export_allowed=True),
    map_results_keyboard(1, 2), answers_menu(), answers_result_keyboard(),
    parse_menu(), parse_result_keyboard(), intelligence_menu(), brand_menu(),
    people_menu(), company_menu(), news_menu(), news_results_keyboard(1, 2, 2),
    batches_menu(), batch_actions("abc123"), job_center_menu(),
    job_list_keyboard(1, 2, ["abc123"]), job_actions("abc123"),
    monitors_menu(), monitor_actions("mon1"), monitor_delete_confirm_keyboard("mon1"),
    monitor_list_keyboard(1, 1, ["mon1"]), usage_keyboard(), plan_keyboard(),
    locked_feature_keyboard(), settings_menu(), settings_language_keyboard(),
    settings_clear_confirm_keyboard(), settings_delete_confirm_keyboard(),
    help_menu(), error_keyboard("validation"), error_keyboard("rate_limit"),
    error_keyboard("quota"), error_keyboard("context_error"),
]


# ---------------------------------------------------------------- menus
def test_main_menu_buttons_and_two_column_layout():
    rows = rows_of(main_menu())
    texts = button_texts(main_menu())
    for label in ("Scrape URL", "Search Web", "Crawl Website", "Map URLs",
                  "Ask / Answers", "Parse File", "Brand Intel", "People",
                  "Company", "News", "Batches", "Monitors", "Usage & Paket",
                  "Pengaturan", "Bantuan"):
        assert label in texts, label
    assert all(len(r) <= 2 for r in rows), "max 2 buttons per row"
    assert "Menu Admin" not in texts


def test_main_menu_admin_button_only_for_admins():
    assert "Menu Admin" in button_texts(main_menu(is_admin=True))
    assert "Menu Admin" not in button_texts(main_menu(is_admin=False))
    assert "Menu Admin" not in button_texts(main_menu())


def test_every_submenu_has_back_and_home():
    submenu_keyboards = [scrape_menu(), search_menu(), crawl_menu(), map_menu(),
                         answers_menu(), parse_menu(), intelligence_menu(),
                         news_menu(), batches_menu(), monitors_menu(),
                         usage_keyboard(), settings_menu(), help_menu()]
    for kb in submenu_keyboards:
        callbacks = iter_callbacks(kb)
        assert "nav:v1:back" in callbacks, kb
        assert "nav:v1:home" in callbacks, kb


def test_admin_menu_keeps_legacy_callbacks_reachable():
    callbacks = iter_callbacks(admin_menu())
    for legacy in LEGACY_CALLBACKS:
        if legacy != "admin:cancel_api_key":
            assert legacy in callbacks, legacy
    assert "admin:cancel_api_key" in iter_callbacks(
        __import__("app.bot.keyboards", fromlist=["admin_cancel_keyboard"]).admin_cancel_keyboard())


def test_every_callback_in_every_keyboard_is_recognized_and_short():
    for kb in ALL_KEYBOARDS:
        for cb in iter_callbacks(kb):
            assert is_recognized(cb), cb
            # validate_callback is strictly v1; legacy admin callbacks
            # are recognised via is_recognized() instead, by design.
            assert validate_callback(cb) or cb in LEGACY_CALLBACKS, cb
            assert len(cb.encode("utf-8")) <= 64, cb


def test_invalid_callbacks_rejected():
    assert not validate_callback("foo:v1:bar")
    assert not validate_callback("nav:v1:explode")
    assert not validate_callback("nav:v1:home:" + "x" * 100)
    assert not validate_callback(None)
    assert not validate_callback("admin:made_up")
    assert is_recognized("admin:set_api_key")  # legacy, deliberate
    parsed = parse_callback("job:v1:status:abc123")
    assert (parsed.namespace, parsed.action, parsed.args) == ("job", "status", ("abc123",))


def test_nav_screen_targets_all_exist_in_registry():
    assert SCREEN_IDS <= set(SCREENS), SCREEN_IDS - set(SCREENS)
    for kb in ALL_KEYBOARDS:
        for cb in iter_callbacks(kb):
            parsed = parse_callback(cb)
            if parsed and parsed.namespace == "nav" and parsed.action == "screen":
                assert parsed.first_arg in SCREENS, parsed.first_arg


# ---------------------------------------------------------------- handlers
def test_other_user_cannot_open_someone_elses_job_monitor_batch():
    owners = {("job", "abc123"): 111, ("monitor", "mon1"): 111, ("batch", "b9"): 111}
    assert process_callback("job:v1:status:abc123", user_id=222, owners=owners)["status"] == "forbidden"
    assert process_callback("monitor:v1:pause:mon1", user_id=222, owners=owners)["status"] == "forbidden"
    assert process_callback("batch:v1:status:b9", user_id=222, owners=owners)["status"] == "forbidden"
    assert process_callback("job:v1:status:abc123", user_id=111, owners=owners)["status"] == "ok"
    assert process_callback("job:v1:status:missing", user_id=111, owners=owners)["status"] == "not_found"


def test_expired_callback_handled_and_nav_state_falls_back_home():
    old = time.time() - 7200
    assert is_expired(old, ttl_seconds=3600) is True
    assert is_expired(time.time(), ttl_seconds=3600) is False
    out = process_callback("search:v1:start", user_id=1, issued_at=old)
    assert out["status"] == "expired" and out["screen"] == "home"
    state = NavState(user_id=7, current_screen="scrape", stack=["home"])
    state.updated_at = old
    assert state.is_expired() is True
    assert state.go_back() == "home"


def test_double_click_does_not_duplicate_a_job():
    queue, guard = InMemoryQueue(), DoubleClickGuard()
    first = process_callback("scrape:v1:confirm", user_id=5, queue=queue, guard=guard)
    second = process_callback("scrape:v1:confirm", user_id=5, queue=queue, guard=guard)
    assert first["status"] == "ok" and first["enqueued"] is True
    assert second["status"] == "duplicate"
    assert queue.depth() == 1
    assert guard.claim("k") == "first" and guard.claim("k") == "duplicate"


def test_locked_feature_routes_to_upgrade_and_never_enqueues():
    queue = InMemoryQueue()
    out = process_callback("crawl:v1:start", user_id=5, plan="free", queue=queue)
    assert out["status"] == "locked" and out["required_plan"] == "pro" and out["screen"] == "plan"
    assert queue.depth() == 0
    out = process_callback("intelligence:v1:people:search", user_id=5, plan="pro", queue=queue)
    assert out["status"] == "locked" and out["required_plan"] == "business"
    assert process_callback("crawl:v1:start", user_id=5, plan="pro")["status"] == "ok"


def test_admin_button_unusable_by_non_admins():
    assert process_callback("admin:v1:dashboard", user_id=9, is_admin=False)["status"] == "forbidden"
    assert process_callback("admin:v1:dashboard", user_id=9, is_admin=True)["status"] == "ok"


def test_destructive_actions_are_two_step():
    out = process_callback("monitor:v1:delete:mon1", user_id=1,
                           owners={("monitor", "mon1"): 1})
    assert out["status"] == "ok" and out["screen"] == "monitor_delete_confirm"
    out = process_callback("monitor:v1:confirm_delete:mon1", user_id=1,
                           owners={("monitor", "mon1"): 1})
    assert out["screen"] == "monitors"
    assert process_callback("settings:v1:delete_data", user_id=1)["screen"] == "settings_delete_confirm"
    assert process_callback("settings:v1:clear_history", user_id=1)["screen"] == "settings_clear_confirm"


def test_search_result_index_validation_no_urls_in_callbacks():
    assert process_callback("search:v1:open:99", user_id=1, search_result_count=3)["status"] == "not_found"
    assert process_callback("search:v1:read:2", user_id=1, search_result_count=3)["status"] == "ok"
    for cb in iter_callbacks(search_results_keyboard(1, 2, 3)):
        assert "http" not in cb


# ---------------------------------------------------------------- formatting
def test_html_escaping_for_scraped_content():
    nasty = '<script>alert("x")</script> & \'quotes\''
    assert escape_html(nasty) == "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; &#x27;quotes&#x27;"
    text = msg.search_results_text("<b>q</b>", 1, 1,
                                   [{"title": "<img>", "snippet": nasty, "domain": "ex.com"}])
    assert "<script>" not in text and "<img>" not in text
    assert "&lt;script&gt;" in text


def test_bold_italic_code_pre_link_quote_validity():
    assert bold("a<b") == "<b>a&lt;b</b>"
    assert italic("x") == "<i>x</i>"
    assert code("a & b") == "<code>a &amp; b</code>"
    assert pre("x<y", language="python") == '<pre language="python">x&lt;y</pre>'
    assert quote("hi") == "<blockquote>hi</blockquote>"
    assert link("Sumber", "https://example.com/a") == '<a href="https://example.com/a">Sumber</a>'
    assert link("Sumber", "javascript:alert(1)") == "Sumber"
    assert safe_url("ftp://example.com") == ""
    assert safe_url("https://user:pass@example.com") == ""
    assert escape_markdown("a_b*c") == "a\\_b\\*c"
    assert link_md("x", "javascript:alert(1)") == "x"


def test_splitting_never_cuts_html_tags():
    body = "<b>" + "kata " * 200 + "</b> " + "<i>" + "isi " * 200 + "</i>"
    chunks = split_html_message(body, limit=100)
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.count("<b>") == chunk.count("</b>")
        assert chunk.count("<i>") == chunk.count("</i>")
        assert not re.search(r"<[^>]*$", chunk), chunk[-30:]
    assert "".join(c.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "")
                   for c in chunks).replace(" ", "") == body.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", "").replace(" ", "")
    truncated = truncate_for_telegram("<b>" + "x" * 5000 + "</b>", limit=100)
    assert len(truncated) <= 110 and truncated.endswith("</b>")
    assert "<b" not in truncated[len(truncated) - 10:] or truncated.endswith("</b>")


def test_pagination_first_last_and_invalid_cursor():
    first = iter_callbacks(search_results_keyboard(1, 3, 1))
    assert "search:v1:page:0" not in first and "search:v1:page:2" in first
    last = iter_callbacks(search_results_keyboard(3, 3, 1))
    assert "search:v1:page:4" not in last and "search:v1:page:2" in last
    store = CursorStore()
    cid = store.store("opaque-cursor-xyz")
    assert len(cid) <= 12 and store.get(cid) == "opaque-cursor-xyz"
    assert store.get("nope") is None
    expired_store = CursorStore(ttl_seconds=-1)
    assert expired_store.get(expired_store.store("x")) is None


def test_error_states_have_correct_buttons():
    validation = iter_callbacks(error_keyboard("validation"))
    assert "nav:v1:back" in validation
    rate = iter_callbacks(error_keyboard("rate_limit"))
    assert "job:v1:list:active" in rate and "nav:v1:screen:job_center" in rate
    quota = iter_callbacks(error_keyboard("quota"))
    assert "nav:v1:screen:usage" in quota and "plan:v1:show" in quota
    context = iter_callbacks(error_keyboard("context_error"))
    assert "nav:v1:home" in context
    assert "UNKNOWN" in msg.error_context_text("x; DROP TABLE users")
    assert "Traceback" not in msg.error_context_text("ERR_1")
    assert "mencoba lagi" in msg.error_context_text("ERR_1")


def test_keyboards_valid_with_empty_and_null_api_fields():
    assert "Tidak tersedia" in msg.brand_text({"Nama": None, "Domain": "", "Logo": None})
    assert "Tidak tersedia" in msg.company_text({})
    assert "Tidak tersedia" in msg.people_text({})
    assert "Tidak tersedia" in msg.job_text({})
    assert "Tidak tersedia" in msg.parse_file_text("f.pdf", None, None)
    assert "Tidak ada hasil" in msg.search_results_text("q", 1, 1, [])
    assert "Tidak tersedia" in msg.map_results_text("example.com", 1, 1, [])


def test_id_and_en_texts():
    assert "Pilih fitur" in msg.main_menu_text("id")
    assert "Choose a feature" in msg.main_menu_text("en")
    assert "Input belum valid" in msg.error_validation_text("id")
    assert "Input not valid" in msg.error_validation_text("en")
    assert "Limit paket tercapai" in msg.error_quota_text("id")
    assert "Plan limit reached" in msg.error_quota_text("en")
    assert "Paket:" in msg.usage_text("pro", 24, 100, 1, language="id")
    assert "Plan:" in msg.usage_text("pro", 24, 100, 1, language="en")


def test_secrets_never_shown():
    assert "SECRETVALUE" not in redact_secrets("api_key: SECRETVALUE")
    assert "****" in redact_secrets("api_key: SECRETVALUE")
    assert "Bearer ****" in redact_secrets("Bearer abcdef123456")
    text = msg.scrape_confirm_text("https://example.com/?api_key=TOPSECRET", "Markdown")
    assert "TOPSECRET" not in text


def test_legacy_formatter_compat():
    class Result:
        is_partial = True
        title = "T <est>"
        text = ""
        items = [{"title": "A", "url": "https://a.example"}]
        sources = ["https://s.example"]
    chunks = format_normalized("search", Result())
    assert chunks and "&lt;est&gt;" in chunks[0] and "Partial result" in chunks[0]


# ---------------------------------------------------------------- navigation
@pytest.mark.asyncio
async def test_navigation_back_home_and_edit_fallback():
    cb = FakeCallback(42, "nav:v1:screen:scrape")
    rendered = await render_screen(cb, "scrape", {"user_id": 42})
    assert rendered == "scrape" and cb.message.edits
    state = get_nav_state(42)
    assert state.current_screen == "scrape"
    back = await go_back(cb, {"user_id": 42})
    assert back == "home"
    home = await go_home(cb, {"user_id": 42})
    assert home == "home"
    # Unknown screen falls back to home, never to a dead end.
    assert await render_screen(cb, "nope", {"user_id": 42}) == "home"
    # Un-editable message -> new message sent gracefully.
    cb2 = FakeCallback(43, "nav:v1:home", fail_edit=True)
    assert await edit_or_send(cb2, "hello") == "sent"
    assert cb2.message.sent
    assert await show_error(cb2, "oops", kind="validation") == "validation"


def test_nav_stack_capped_at_ten():
    state = NavState(user_id=1)
    screens = ["scrape", "search", "crawl", "map", "answers", "parse",
               "intelligence", "news", "batches", "monitors", "usage",
               "settings", "help", "plan", "admin"]
    for screen in screens:
        state.push(screen)
    assert len(state.stack) <= 10
