"""Temporary signed download URLs + TTL helpers. Pure stdlib (HMAC)."""
from __future__ import annotations

import hashlib
import hmac
import time


def signed_url(base: str, path: str, secret: str, *, ttl_seconds: int = 3600,
               now: float | None = None) -> str:
    exp = int((now if now is not None else time.time()) + ttl_seconds)
    msg = f"{path}:{exp}".encode()
    sig = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    return f"{base.rstrip('/')}/{path.lstrip('/')}?exp={exp}&sig={sig}"


def verify_signed_url(path: str, exp: int, sig: str, secret: str,
                      *, now: float | None = None) -> bool:
    if (now if now is not None else time.time()) > exp:
        return False
    expected = hmac.new(secret.encode(), f"{path}:{exp}".encode(),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def is_expired(expires_at, now) -> bool:
    return expires_at is not None and now >= expires_at
