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
