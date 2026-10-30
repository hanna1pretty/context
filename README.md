# Context Intelligence Bot

Telegram premium bot using Context.dev APIs (scrape, search, crawl, map,
answers, parse, brand/styleguide, people, company, news, batches, monitors).
Python 3.12+, aiogram 3.x, FastAPI, PostgreSQL 16 + SQLAlchemy 2.x async +
Alembic, Redis 7, ARQ, httpx, Pydantic Settings, Docker Compose, Prometheus
(metrics hook: prometheus-client is a dependency; expose via FastAPI in
production wiring), structured JSON logging, pytest + pytest-asyncio.

> **Honest status**: this is a runnable scaffold with real pure-core logic
> (SSRF, retry/429, normalisation, entitlement, splitting, dedup) and full
> handler/API/worker/DB layers. It was built and tested in a VM **without**
> Docker, Telegram, or live Context.dev access. Docker Compose, live
> Telegram, and live Context.dev were **NOT** tested here — see
> "Known limitations" below.

## Local setup (no Docker, tests only)
```bash
python3 -m venv .venv && source .venv/bin/activate   # outside the repo tree is fine; .venv is gitignored
pip install -r requirements.txt pytest pytest-asyncio
cp .env.example .env   # fill placeholders locally; .env is gitignored, never commit it
python -m pytest -q
```

## Admin-panel Context.dev API key (primary method)
The Context.dev API key is set **inside the bot, in the admin panel only**
-- not by editing code, and not in a group chat:
1. Set `ADMIN_TELEGRAM_IDS` to your Telegram user ID and generate an
   encryption key for storage (see below), then start the bot.
2. In a **private chat** with the bot, send `/admin`.
3. Tap **Set Context API Key**. The bot warns you to stay in private chat.
4. Send the key as your next private message. The bot tries to delete
   that input message, saves the key Fernet-encrypted in the
   `admin_settings` table, and replies only with the masked form
   (`****` + last 4 characters). It never shows the full key again.
5. **Lihat Status API Key** shows masked status only.
   **Hapus API Key** deletes the stored key (env fallback, if any, then applies).
6. Rotate: tap Set again and send the new key. Delete the old key message
   from your own chat history manually too -- the bot's delete attempt can
   fail, and Telegram chat history is otherwise a copy of the key.

Generate the encryption key (do this once, store it in `.env` / your
secret manager, never commit it):
```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
If `SETTINGS_ENCRYPTION_KEY` is missing, setting a key fails with a clear
message and **nothing is stored in plaintext**. Rotating
`SETTINGS_ENCRYPTION_KEY` makes previously stored keys undecryptable --
set the API key again via `/admin` after rotation.
If no admin-panel key and no env key exist, jobs fail with the clear
message "API key Context.dev belum di-set. Admin: set di /admin > Set
Context API Key." and no live Context.dev call is attempted.

## Local setup (Docker, production-like)
```bash
cp .env.example .env   # fill TELEGRAM_BOT_TOKEN, SETTINGS_ENCRYPTION_KEY, CONTEXT_WEBHOOK_SECRET
# then set the Context.dev key via /admin (or set CONTEXT_DEV_API_KEY as fallback)
docker compose up --build
# API: http://localhost:8000/health/live  and  /health/ready
# Bot: polling in local dev (python -m app.main bot); webhook in production
#   (set WEBHOOK_BASE_URL + WEBHOOK_PATH, register the Telegram webhook
#    with TELEGRAM_WEBHOOK_SECRET, then run uvicorn for the API service)
# Migrations: alembic upgrade head   (migration body: app/db/migrations/001_initial.py)
```

## Commands
/start /help /scrape /search /crawl /map /ask /parse /brand /styleguide
/people /company /news /batch /monitor /usage /plan /language /cancel
/admin /delete_my_data — plus bare-URL conversational flow (Scrape Markdown,
Scrape HTML, Screenshot, Extract JSON, Crawl, Map, Ask about URL).

## Environment variables
See `.env.example` (placeholders only). Required in production:
TELEGRAM_BOT_TOKEN. CONTEXT_DEV_API_KEY is now OPTIONAL -- it is only
the fallback at call time if no admin-panel key is stored (see the
admin-panel section above); startup does NOT fail without it, so an
admin can always set a key via /admin afterwards.
SETTINGS_ENCRYPTION_KEY is required before any admin-panel key can be
saved (Fernet key; generate as above). Also: DATABASE_URL, REDIS_URL,
WEBHOOK_BASE_URL/WEBHOOK_PATH, CONTEXT_WEBHOOK_SECRET, ADMIN_TELEGRAM_IDS
(comma-separated Telegram IDs), DEFAULT_LANGUAGE (id), DEFAULT_TIMEZONE
(Asia/Jakarta), MAX_TELEGRAM_MESSAGE_LENGTH (3900),
MAX_CONCURRENT_JOBS_PER_USER (2), MAX_GLOBAL_QUEUE_SIZE (10000),
FREE_DAILY_LIMIT (10), PRO_DAILY_LIMIT (100), BUSINESS_DAILY_LIMIT (1000),
CONTEXT_DEV_BASE_URL, CONTEXT_DEV_TIMEOUT_SECONDS (60),
CONTEXT_DEV_MAX_CONCURRENCY (set from your Context.dev plan: Free 2,
Developer 10, Pro 100, Growth 250, Scale 500 — do not assume 100).
TELEGRAM_API_ID / TELEGRAM_API_HASH are NOT needed for Bot API bots.

## Cost / credit controls
- Estimates use the pricing anchors in docs/contextdev-feature-matrix.md
  (scrape from 1, JSON extraction 5/page, map from 1, crawl 1/page,
  search from 1, answers from 10, brand 10, people search from 10 /
  enrich 20, company search 2, news from 1, parse from 1).
- Actual consumption is read from key_metadata.credits_consumed.
- Per-plan daily limits + per-user concurrency + crawl page caps +
  minimal formats by default. Large crawl/batch/monitor operations require
  Pro/Business entitlement and are queued, never run in handlers.

## Remaining wiring gap (admin-panel key, honest)
The resolver and the client acceptance are implemented and tested:
`services/admin_key_service.py` resolves stored-key -> env, the
Context.dev client accepts an explicit key and fails before any live
call when none exists, and `workers/jobs.py` accepts a
`context_api_key` / `api_key_resolver` in its context. What is NOT yet
wired in `main.py` (no live Postgres/Telegram run was available here):
(1) the ARQ worker context is not yet injected with a resolver backed
by `AdminSettingRepository` + env, so a deployed worker still needs that
one wiring step to use a DB-stored key end to end; (2) the Telegram
handler's key store defaults to the in-memory store and its pending-input
state is in-process -- production `main.py` wiring must replace the
handler store with the DB repository and move pending-input state to
Redis FSM, or keys are lost on restart and not shared between workers.
Until that wiring lands, the in-memory path is correct for
single-process dev only. The `admin_settings` table itself (model +
repository + migration body in `001_initial.py`, folded in before any
deployment of that migration) is ready.
## Context.dev limitations
- Only scrape and crawl endpoints are VERIFIED in this build; all other
  endpoints are PATTERN-INFERRED (/v1/web/<feature>) and must be re-checked
  against docs.context.dev before relying on them. The client degrades
  gracefully on 404/unsupported.
- Webhook signature scheme is a generic HMAC-SHA256 stub, not the vendor's
  verified scheme — replace verify_signature() once confirmed.
- Crawl: up to 500 pages in one call; larger sites must use Batches.

## Project layout
app/config.py, app/logging.py, app/main.py, app/bot/{router,middlewares,
keyboards,formatters,handlers/*}, app/api/{health,context_webhooks,
admin_api}, app/contextdev/{client,models,endpoint_router,errors,retry,
result_normalizer}, app/workers/{queue,jobs,scheduler}, app/db/{models,
repositories,migrations/001_initial.py}, app/services/{usage,subscription,admin_key_service,
credit,job,notification,storage,moderation}, app/security/{secrets,
validators,rate_limit}. Core pure modules (security, contextdev retry/
normalizer/errors, services entitlement) have NO third-party imports so
pytest runs without aiogram/FastAPI/SQLAlchemy installed.

## Inline keyboard system (premium, spec sections 1-25)

All navigation is inline keyboards, Telegram HTML, v1-namespaced
callbacks. No button is dead: every callback in every keyboard is
recognised by `app/bot/callbacks/base.py::validate_callback` (tested in
`tests/test_inline_keyboards.py`).

### Menu diagram (text)

```text
Menu Utama
├── Scrape URL ── Konfirmasi Scrape ── Job Center
├── Search Web ── Hasil Pencarian (per-hasil Buka/Baca, pagination)
├── Crawl Website ── Konfirmasi Crawl ── Job Center
├── Map URLs ── Hasil Map (export gated by entitlement)
├── Ask / Answers ── Hasil Jawaban (sumber, export, simpan)
├── Parse File ── Hasil Parse (nama/ukuran/MIME, tanpa path server)
├── Brand Intel ── Brand / Styleguide / People / Company
├── News ── Hasil Berita (Buka/Baca, pagination)
├── Batches ── Job Center (aktif/selesai/gagal/semua)
├── Monitors ── Monitor Saya / Perubahan / Hapus (2 langkah)
├── Usage & Paket ── Detail Usage / Paket / Upgrade (checkout only)
├── Pengaturan ── Bahasa / Timezone / Notifikasi / Output /
│                 Clear History (2 langkah) / Hapus Data (2 langkah)
├── Bantuan ── Command / Contoh / Status / Privacy
└── Menu Admin (admin only) ── Set/Lihat/Hapus API Key (legacy) + Dashboard
```

Every submenu ends with `‹ Kembali` + `Menu Utama`. Back uses a
bounded stack (max 10, 1-hour expiry) with fallback to home.

### Screens (all in handlers/navigation.py SCREENS)

home, scrape, scrape_confirm, search, search_results, crawl,
crawl_confirm, map, map_results, answers, answers_result, parse,
parse_result, intelligence, brand, styleguide, people, company, news,
news_results, batches, job_center, job_detail, monitors, monitor_detail,
monitor_delete_confirm, usage, plan, settings, settings_delete_confirm,
settings_clear_confirm, help, help_commands, help_examples, help_status,
help_privacy, admin, admin_dashboard.

### Callback namespaces (all `v1`, all under 64 bytes)

| Namespace | Purpose | Examples |
|---|---|---|
| nav | navigation | `nav:v1:home`, `nav:v1:back`, `nav:v1:screen:scrape` |
| scrape | scrape modes/confirm | `scrape:v1:mode:markdown`, `scrape:v1:confirm` |
| search | search filters/pages/results by INDEX | `search:v1:page:2`, `search:v1:open:3` |
| crawl | crawl params/confirm | `crawl:v1:param:depth`, `crawl:v1:confirm` |
| map | map filters/export/pages | `map:v1:export:json`, `map:v1:page:2` |
| answers | answer styles/sources | `answers:v1:style:detail`, `answers:v1:source` |
| parse | parse upload/output | `parse:v1:output:markdown`, `parse:v1:view` |
| intelligence | brand/styleguide/people/company | `intelligence:v1:people:search` |
| news | news filters/pages/results by INDEX | `news:v1:page:2`, `news:v1:read:1` |
| job | Job Center actions by short id | `job:v1:status:abc123`, `job:v1:retry:abc123` |
| batch | batch actions by short id | `batch:v1:new`, `batch:v1:status:b9` |
| monitor | monitor actions by short id | `monitor:v1:pause:mon1`, `monitor:v1:confirm_delete:mon1` |
| plan | plan/upgrade (checkout only, never auto-charge) | `plan:v1:show`, `plan:v1:upgrade:pro` |
| settings | settings + 2-step destructive actions | `settings:v1:language`, `settings:v1:confirm_delete` |
| admin | NEW admin buttons | `admin:v1:dashboard` |
| admin (legacy) | pre-v1 admin key flow, retained | `admin:set_api_key`, `admin:api_key_status`, `admin:delete_api_key`, `admin:cancel_api_key` |

Rules: job/monitor/batch callbacks carry short server-side IDs only
(never raw URLs or long cursors — long cursors live in
`callbacks/base.py::CursorStore` with TTL). Callback handlers answer
first, check user + ownership + entitlement (`check_feature`; locked
routes to the plan screen and never enqueues), handle expiry, guard
double-clicks with `DoubleClickGuard`, and never call Context.dev
directly — they enqueue via `workers.queue.enqueue_job` only.

### How to add a new button / submenu without breaking navigation

1. Add the callback builder in the matching `app/bot/callbacks/*.py`
   (or a new namespace entry in `callbacks/base.py::_NAMESPACE_ACTIONS`
   if it is a genuinely new namespace) — builders raise on overlong data.
2. Add the keyboard factory in the matching `app/bot/keyboards/*.py`,
   ending the rows with `with_back_home(...)` (or `back_home_row()`).
3. Add the screen id to `callbacks/navigation.py::SCREEN_IDS` (and
   `PARENT_SCREEN` if it has a non-home parent) and one entry in
   `handlers/navigation.py::SCREENS` (text fn + keyboard fn).
4. If the button starts a job, add it to
   `handlers/feature_callbacks.py::_ENQUEUE_ACTIONS` so it gets the
   double-click guard; if it needs a plan gate, add it to
   `_FEATURE_FOR_ACTION`. Never add a network call in a callback handler.
5. Run `python -m pytest -q` — the "every callback recognised" and
   "every nav target exists" tests fail loudly on dead buttons.

### Text examples (from formatters/messages.py)

Main menu (ID):
```html
<b>Context Intelligence Bot</b>

<blockquote>Web intelligence cepat untuk membaca, mencari, mengekstrak,
dan memantau informasi dari internet.</blockquote>

<b>Pilih fitur:</b>
Pilih salah satu menu di bawah atau kirim URL dan pertanyaan langsung.
```

Scrape confirmation:
```html
<b>Konfirmasi Scrape</b>

<b>URL:</b> <code>https://example.com/...</code>
<b>Mode:</b> <code>Markdown</code>
<b>Cache:</b> <code>Default</code>

Apakah permintaan ini sudah benar?
```

Search results: title + `<blockquote>` snippet + `domain · date` per
result, with `[N Buka] [N Baca]` buttons and `[‹ Prev] [1 / 5] [Next ›]`
pagination (the `1 / 5` indicator re-requests the current page — it is
a refresh, never a dead button).

Job Center:
```html
<b>Job Center</b>

Di sini kamu dapat melihat pekerjaan aktif, selesai, gagal, atau kadaluarsa.
```
Per job: `<b>Job:</b> <code>abc123</code>` + real stored type/status/
created (never fabricated progress), with Status/Hasil/Batalkan/
Coba Lagi/Hapus/Refresh.

Usage:
```html
<b>Usage & Paket</b>

<b>Paket:</b> <code>PRO</code>
<b>Penggunaan hari ini:</b> <code>24 / 100</code>
<b>Job aktif:</b> <code>1</code>
<b>Reset limit:</b> <code>besok 00:00</code>
```

Error states (each with its own buttons): validation → Coba Lagi/
Kembali; rate limit → Refresh Status/Job Saya; quota → Lihat Usage/
Lihat Paket; Context.dev error → safe internal code only (e.g.
`ERR_1`, never a stack trace) + Coba Lagi.

No new environment variables were added for this system.

## Troubleshooting
- "Missing required secret(s)": set the named env vars; values are never printed.
- 429s: the client honours Retry-After with bounded exponential backoff +
  jitter and a circuit breaker; check CONTEXT_DEV_MAX_CONCURRENCY.
- 404 on a feature: it is likely PATTERN-INFERRED — check the feature matrix.

## Backup / restore (Postgres)
`pg_dump` the context_bot database on a schedule; restore with `psql`.
Redis holds only queue/FSM/cache state and can be rebuilt.
