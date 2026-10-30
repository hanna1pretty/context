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

## Troubleshooting
- "Missing required secret(s)": set the named env vars; values are never printed.
- 429s: the client honours Retry-After with bounded exponential backoff +
  jitter and a circuit breaker; check CONTEXT_DEV_MAX_CONCURRENCY.
- 404 on a feature: it is likely PATTERN-INFERRED — check the feature matrix.

## Backup / restore (Postgres)
`pg_dump` the context_bot database on a schedule; restore with `psql`.
Redis holds only queue/FSM/cache state and can be rebuilt.
