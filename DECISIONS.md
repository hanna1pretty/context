# DECISIONS

- **ARQ over Celery**: all work is async (aiogram + httpx + asyncpg); ARQ is
  natively async, lighter than Celery, and fits Redis which is already
  required for FSM/cache/rate limiting. Workers live in app/workers/.
- **Single ENDPOINTS table** (app/contextdev/endpoint_router.py): only
  scrape + crawl are VERIFIED; the rest follow /v1/web/<feature> as a
  pattern and are labelled PATTERN-INFERRED, with graceful 404 degradation.
  Presenting inferred paths as verified would violate the spec's
  "do not invent endpoints" rule.
- **Handler/worker split for SSRF**: handlers run only the synchronous
  no-DNS checks (validate_url_no_dns); workers re-run full validate_url
  with real DNS before any Context.dev call. This keeps handlers fast and
  non-blocking while still closing DNS-rebinding-style private-IP cases
  at the worker boundary. (Residual risk: DNS change between worker check
  and Context.dev fetch — Context.dev fetches server-side; document and
  accept, do not claim it is eliminated.)
- **Bot billing != Context.dev credits**: plan limits are the bot's own
  daily/job limits; Context.dev credit consumption is read from
  key_metadata.credits_consumed and only estimated beforehand.
- **Generic webhook HMAC stub**: Context.dev's exact signature scheme was
  not verified in this build, so app/api/context_webhooks.py implements a
  generic verifiable HMAC-SHA256 scheme and says so. Unsigned webhooks are
  refused; replace verify_signature() once the real scheme is confirmed.
- **In-memory queue/limiter for dev, ARQ/Redis for prod**: the in-memory
  versions keep the pure test suite dependency-free; production compose
  wires Redis + ARQ. Do not run multi-worker prod on the in-memory queue.
- **Telegram API ID/Hash not required**: Bot API bots do not need them;
  they are optional env vars only, for MTProto if ever genuinely needed.
- **Admin-panel API key, env as fallback**: the user asked for the
  Context.dev key to be input in the bot's admin panel, so that is now
  the primary method and CONTEXT_DEV_API_KEY is optional at startup
  (previously required in production). Resolution at call time is
  stored-key -> env -> clear missing-key error, no live call without a
  key. Env is retained as a fallback so existing deployments that set
  the env var keep working and so a deleted admin-panel key does not
  brick a deployment that still has a valid env key.
- **Fernet for stored keys**: `cryptography` Fernet (AES-128-CBC +
  HMAC, authenticated) is the standard choice for "encrypt a short
  secret at rest with a single server-side key" -- no key-derivation or
  custom crypto needed. The encryption key itself comes from env
  (SETTINGS_ENCRYPTION_KEY), never from the database, and a missing or
  invalid encryption key fails the set operation instead of falling
  back to plaintext. Trade-off, stated plainly: rotating the encryption
  key invalidates stored keys (they must be re-set via /admin); there
  is no re-encryption migration in this build.
- **admin_settings folded into 001_initial**: that migration had never
  been deployed (the repo had not been pushed yet), so the new table
  was added to the initial migration body rather than a second
  migration that would double-create it on fresh installs.
- **Docs over spec on conflict**: where the spec and verified Context.dev
  facts conflict, verified facts win and this file records the change.
  No such conflict was found beyond the inferred-endpoint caveat above.
- **keyboards.py / formatters.py -> packages (inline-keyboard build)**:
  the single files could not coexist with the spec's keyboards/ and
  formatters/ directories, so their content moved into
  keyboards/__init__.py and formatters/__init__.py and the old files
  were deleted locally (REPLACED-BY-DIRECTORY — delete them on GitHub
  too, or the package will be shadowed). Legacy imports
  (main_menu/url_choices/admin_menu/admin_cancel_keyboard/job_actions,
  welcome/format_search_results/format_normalized) keep working via
  re-exports, with identical behaviour for the three formatter functions.
- **Legacy admin callbacks retained (deliberate deviation)**: the new
  system is fully v1-namespaced, EXCEPT admin:set_api_key,
  admin:api_key_status, admin:delete_api_key, admin:cancel_api_key,
  which handlers/admin.py is wired to. They stay reachable from the new
  admin menu; all NEW admin buttons use admin:v1:*. The old url:* and
  job:* callbacks were NOT retained because no handler consumed them —
  url_choices() and job_actions() now emit v1 callbacks.
- **In-memory lock/cursor, Redis documented for production**: the spec
  asks for Redis locks and Redis/Postgres cursors, but the test suite
  runs without Redis/Postgres, so DoubleClickGuard and CursorStore are
  in-memory with TTL and the exact Redis contract is documented on each
  class (SET NX EX / SET EX). Do not run multi-worker prod on them.
- **Fallback keyboard shape is row-preserving**: the old keyboards.py
  fallback flattened buttons into one list; the new common._mk keeps
  rows (list of row lists) so 2-column layout is testable without aiogram.
- **News callbacks live in callbacks/search.py**: the spec's callbacks/
  file list has no news.py, so news builders share the search module
  (same result-index model); keyboards/news buttons live in
  keyboards/search.py for the same reason.
- **Pagination indicator is a refresh, not a dead button**: the middle
  "1 / 5" button re-requests the current page (a recognised, harmless
  handler), because a button with no handler would violate the
  no-dead-buttons rule.
- **No new env vars for the keyboard system**: none were needed; the
  existing DEFAULT_LANGUAGE / MAX_TELEGRAM_MESSAGE_LENGTH settings
  already cover language and the 3900-char split limit.
- **Screenshot = formats.screenshot + markdown together (VERIFIED)**:
  POST /web/scrape with `formats: {"screenshot": true, "markdown": true}`
  (docs.context.dev/api-reference/web-scraping/scrape; older GET
  /web/scrape/screenshot is equivalent). Markdown is requested
  alongside so the photo caption has title/final URL/credits/
  request_id and a failed screenshot still leaves text, with
  isPartial surfaced honestly. A standard scrape is 1 credit and
  `key_metadata.credits_consumed` is authoritative — no screenshot
  surcharge is hardcoded anywhere.
- **Screenshot data-URL rules (strict, pure stdlib)**:
  `contextdev/screenshot.py::parse_data_url` accepts only
  image/png, image/jpeg, image/webp, valid base64 (validate=True),
  and at most 10,000,000 decoded bytes (the Telegram photo limit);
  anything else raises, and the normalizer only reports success
  when success==true AND data starts with "data:image/...".
  Never log a data URL or its bytes.
- **Delivery helper vs ARQ result caveat**: the worker result dict
  carries `screenshot_data_url` so the single-process delivery
  helper (`services/screenshot_delivery.py`) can build the Telegram
  photo, plus the log-safe `screenshot_data_url_present` bool.
  A full-page screenshot data URL can be several MB, so production
  ARQ results should prefer temporary storage (signed temp URL /
  object store) over a routine multi-MB payload — documented in
  README, not yet implemented.
- **Menu confirm-flow gap (honest, not papered over)**:
  `handlers/feature_callbacks.py::process_callback` for
  scrape/crawl confirm still enqueues only `{"callback": data}`;
  it has no FSM store to recover the URL/mode the user picked on
  the Scrape menu, so the Screenshot button reaches the confirm
  screen but confirm cannot yet turn that mode into a worker
  payload. The mapping (`contextdev/formats.py`, re-exported from
  `callbacks/scrape.py`), the `/scrape` wiring
  (`handlers/scrape.py::scrape_job_payload`), the client
  (`scrape_screenshot`), the worker (mode->formats translation +
  screenshot fields), and the delivery helper are all implemented
  and tested; the remaining step is passing FSM URL/mode into the
  confirm handler and calling `scrape_job_payload(url, mode)`.
  Likewise, `main.py` has no aiogram `send_photo` call yet, so the
  delivery helper's photo dict is not yet consumed by production
  Telegram code (live Telegram was not tested in this VM anyway).

- **Live bug fixes + premium /start (2026-10-31, after first live run)**:
  - **parse_mode**: `handlers/_common.py::send_html` is now the single
    HTML send site (always `parse_mode="HTML"`); /start, /help, admin
    welcome previews, and all HTML-text sends use it. Audit result:
    admin service texts and the small command handlers send plain
    text (no HTML tags), so they intentionally keep plain answers;
    every send containing `<b>`/`<code>`/`<a>` now goes through
    send_html or `edit_or_send` (which already set HTML).
  - **Dead buttons**: `callback.answer()` first, whole handler body
    in logged try/except with a visible error message, `edit_or_send`
    falls back to a new message and raises/logs if that also fails,
    router include failures are logged (not `except: pass`). Root
    causes found beyond the silent-failure path: (a) start.py's bare
    catch-all swallowed commands (a `/scrape` message became a search
    job — now excluded by filter + early return); (b) nav context
    never carried `is_admin`, so Menu Admin vanished after any
    navigation (now filled from ADMIN_TELEGRAM_IDS).
  - **Job execution**: `workers/consumer.py` (`consume_one` /
    `consume_forever`) is the single-process consumer started by
    `main.py::run_bot_polling` as an asyncio task. It resolves the
    key from the bot process's admin KEY_STORE (env fallback) — this
    works precisely because it shares the bot process; a separate
    worker process would NOT see the in-memory store. Progress ->
    result/failure delivery via `bot.send_message` (+ `send_photo`
    for screenshots) is now the production path for the docker-compose
    `bot` service; ARQ/Redis remains an unwired future gap and must
    not be claimed as running these jobs.
  - **Premium /start (OktaScrape, no channel-join content)**:
    `formatters.welcome_text` (escaped name/username, {nama}/
    {username}/{bot} placeholders, safe tag set only) + `start.py::
    send_welcome` (banner photo + caption <=1024 chars, else text
    card, always main menu). `BOT_DISPLAY_NAME` env (default
    OktaScrape) controls the in-message name only; the BotFather
    display name (Kaguya in live screenshots) is changed in
    BotFather, not by this code.
  - **Admin welcome/banner**: `services/welcome_service.py`
    WelcomeStore (in-memory, same DB gap as the key store) +
    WelcomeInputState; admin menu gains Atur/Lihat/Reset Sambutan
    and Atur/Hapus Banner (v1 callbacks `admin:v1:welcome_*` /
    `banner_*`, admin-only, private chat for input). Template max
    2000 chars; banner confirmation never echoes the file_id.
  - **/help**: now the inline Bantuan screen (`help_text` +
    `help_menu`, HTML mode); the raw command dump lives only behind
    the "Semua Command" button. Command handlers (/scrape etc.) are
    kept as the working test path, with clear accept/progress wording.
  - **Tests**: `tests/test_premium_start_and_consumer.py`, 16 tests
    (welcome escaping/placeholders, caption cap, send_welcome text +
    photo paths, edit fallback, nav answer-first on edit failure,
    every main-menu/help screen renders with HTML mode, on_text
    command exclusion, consumer result / missing-key failure /
    screenshot photo, admin welcome+ banner flows incl. non-admin
    refusal). Full suite after this change: 109 passed.
  - **Still open after this change**: ARQ Redis consumer; DB-backed
    welcome/key stores (both in-memory, lost on restart, not shared
    between workers); live Telegram test still needed (VM has no
    aiogram/Postgres/Redis, so all of the above is fake-object
    verified only); screenshot menu confirm-flow gap (unchanged);
    DoubleClickGuard/CursorStore/NavState still in-memory.
