"""Context.dev webhook receiver: HMAC signature verification (generic stub)
+ idempotent event handling.

IMPORTANT (honest limitation): Context.dev's exact signature scheme was NOT
verified in this build (no live docs re-fetch was performed for webhooks).
This implements a GENERIC, verifiable HMAC-SHA256 scheme:
  signature = hex(HMAC(secret, raw_body)), header X-Context-Signature,
compared with hmac.compare_digest. If Context.dev uses a different scheme
(timestamped payload, different header), replace verify_signature() with
that scheme and update SECURITY.md -- do NOT accept unsigned webhooks.
"""
from __future__ import annotations

import hashlib
import hmac
import json

from ._compat import get_router

router = get_router()


def verify_signature(raw_body: bytes, signature: str | None, secret: str) -> bool:
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.strip().lower())


class WebhookDedup:
    """In-memory seen-event store (production: webhook_events table, unique event_id)."""

    def __init__(self):
        self._seen: set[str] = set()

    def is_duplicate(self, event_id: str) -> bool:
        if event_id in self._seen:
            return True
        self._seen.add(event_id)
        return False

    def payload_hash(self, payload: dict) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()).hexdigest()


DEDUP = WebhookDedup()


@router.post("/webhooks/context")
async def context_webhook(request):
    """FastAPI handler (request is a starlette Request in real runs)."""
    raw = await request.body()
    signature = request.headers.get("x-context-signature")
    # Secret is injected by main.py wiring; standalone router refuses unsigned.
    secret = getattr(request.app.state, "context_webhook_secret", "") if hasattr(request, "app") else ""
    if not verify_signature(raw, signature, secret):
        return {"status": "rejected", "reason": "bad signature"}
    try:
        payload = json.loads(raw.decode())
    except Exception:
        return {"status": "rejected", "reason": "bad json"}
    event_id = str(payload.get("event_id") or payload.get("id") or DEDUP.payload_hash(payload))
    if DEDUP.is_duplicate(event_id):
        return {"status": "duplicate", "event_id": event_id}
    return {"status": "accepted", "event_id": event_id}
