# SECURITY

## Threat model
Attackers: abusive Telegram users (spam, quota draining, SSRF probes),
forged webhooks, and leaked credentials. The bot never executes user input
as shell code, never builds SQL from user text (SQLAlchemy parameters only),
and never trusts callback data / webhook payloads without checks.

## Secrets
- All secrets come from environment / secret manager only. `.env` is
  gitignored and must never be created with real values in the repo.
- `.env.example` contains placeholders only. Startup validation
  (app/config.py + app/security/secrets.py) fails naming only the missing
  variable names, never values. Logs redact secret values.
- Rotation: rotate TELEGRAM_BOT_TOKEN via BotFather, CONTEXT_DEV_API_KEY
  via Context.dev dashboard, CONTEXT_WEBHOOK_SECRET + TELEGRAM_WEBHOOK_SECRET
  together with webhook re-registration; restart services after rotation.

## SSRF
- Scheme allowlist http/https only; reject embedded credentials, localhost,
  .local/.internal-style hosts, and literal private/loopback/link-local/
  reserved/multicast IPs (app/security/validators.py).
- Hostnames are resolved and checked in the worker before Context.dev is
  called (handlers do no-DNS checks only, to stay non-blocking).
- Residual: TOCTOU between DNS check and Context.dev fetch. Mitigate by
  re-checking in the worker and by treating Context.dev as the fetcher
  (it does not run inside your VPC).

## Webhooks
- Telegram: webhook secret token (TELEGRAM_WEBHOOK_SECRET).
- Context.dev: generic HMAC-SHA256 stub (see api/context_webhooks.py header
  + docs/contextdev-feature-matrix.md). Replace with the vendor's exact
  scheme once confirmed; never accept unsigned webhooks.
- Deduplication: webhook_events.event_id is unique; in-memory dedup is
  only for dev (app/api/context_webhooks.py DEDUP).

## Telegram output safety
- All user/API content is HTML-escaped before sending (formatters.py).
- Long messages split at ~3900 chars without cutting URLs or code fences
  (security/validators.py split_message).

## Privacy / deletion
- PII minimisation: logs pseudonymise telegram_user_id (sha256 prefix).
- `/delete_my_data` deletes the user's jobs/results/monitors + user row
  via repositories.delete_user_data, with an audit-log entry.
- Job results expire per plan retention (scheduler.cleanup_expired_results).
- People search: lawful use cases only; low-confidence data is never
  presented as certain fact. See spec section 7H.

## Admin
- Admin checks live in the service layer (api/admin_api.py is_admin_caller,
  bot/handlers/admin.py _is_admin, services/admin_key_service.py
  require_admin) and in repositories' ownership checks,
  not in button visibility alone. All admin actions should be audit-logged.

## Admin-panel API key (Context.dev)
- Set ONLY from /admin, in a private chat. A key sent in a group is
  refused and NOT saved -- it is already in group history -- and the
  admin is told to delete that message and retry in private.
- The bot tries to delete the admin's input message after saving, but
  that delete can fail (permissions, already deleted, etc.), so the
  admin must also delete the key message from their own chat history.
  Telegram chat history is a copy of the key: treat it as sensitive
  until deleted on both sides.
- At rest the key is Fernet-encrypted in admin_settings.encrypted_value
  (see services/admin_key_service.py). Plaintext is never written to
  logs, audit logs (action + admin id + masked form only), job results,
  error messages, or chat replies. Only `****` + last 4 chars is shown.
- No plaintext fallback: if SETTINGS_ENCRYPTION_KEY is missing or
  invalid, setting a key fails and nothing is stored.
- Rotation: rotating SETTINGS_ENCRYPTION_KEY invalidates stored keys
  (re-set via /admin afterwards); rotating the Context.dev key itself
  is done by re-setting it via /admin (or rotating the env fallback).
  Never rotate by pasting a key into a group, a log, or a commit.

## Incident response
1. Rotate affected secrets immediately. 2. Revoke the webhook secret and
   re-register webhooks. 3. Check audit_logs + webhook_events for the
   window. 4. Notify affected users only with facts verified from logs.
