"""Async Context.dev client. httpx is imported lazily so this module is
importable (and its pure helpers testable) without httpx installed.

Transport injection: pass `http_client` with async post(url, json, headers,
timeout) returning an object with .status_code, .headers (dict-like) and
.json() / .text. Real runs use httpx.AsyncClient via _HttpxTransport.
"""
from __future__ import annotations

import asyncio

from .endpoint_router import endpoint_for
from .errors import ContextDevError, ErrorKind, classify_status
from .result_normalizer import normalize_generic
from .retry import CircuitBreaker, backoff_seconds, parse_retry_after


class _Response:
    def __init__(self, status, headers, body):
        self.status_code = status
        self.headers = headers or {}
        self._body = body

    def json(self):
        if isinstance(self._body, dict):
            return self._body
        raise ValueError("not json")

    @property
    def text(self):
        return str(self._body)


class _HttpxTransport:
    def __init__(self, timeout: float):
        import httpx  # lazy
        self._client = httpx.AsyncClient(timeout=timeout)

    async def post(self, url, *, json, headers, timeout):
        resp = await self._client.post(url, json=json, headers=headers, timeout=timeout)
        try:
            body = resp.json()
        except Exception:
            body = resp.text
        return _Response(resp.status_code, dict(resp.headers), body)

    async def aclose(self):
        await self._client.aclose()


API_KEY_MISSING_MESSAGE = (
    "API key Context.dev belum di-set. "
    "Admin: set di /admin > Set Context API Key."
)


class ContextDevClient:
    def __init__(self, *, api_key: str = "", base_url: str = "https://api.context.dev/v1",
                 timeout: float = 60.0, max_retries: int = 3, http_client=None,
                 breaker: CircuitBreaker | None = None):
        # Empty is allowed at construction: the key is resolved at call
        # time (admin-panel stored key, then env fallback) by
        # services/admin_key_service.py, and request() below is where a
        # missing key is reported -- no live call is attempted without one.
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._transport = http_client
        self.breaker = breaker or CircuitBreaker()

    async def _transport_for(self):
        if self._transport is None:
            self._transport = _HttpxTransport(self.timeout)
        return self._transport

    def _headers(self, idempotency_key: str | None = None) -> dict:
        h = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        return h

    async def request(self, feature: str, body: dict, *,
                      idempotency_key: str | None = None):
        """One feature call with retry/429/circuit-breaker. Returns (payload, meta)."""
        if not self.api_key:
            # Fail BEFORE any transport call, with the user-facing message
            # the admin-panel flow promises. Never attempt a live call keyless.
            raise ContextDevError(ErrorKind.AUTH, API_KEY_MISSING_MESSAGE)
        if not self.breaker.allow():
            raise ContextDevError(ErrorKind.UPSTREAM, "Context.dev circuit breaker is open")
        ep = endpoint_for(feature)
        transport = await self._transport_for()
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await transport.post(
                    self.base_url + ep.path, json=body,
                    headers=self._headers(idempotency_key), timeout=self.timeout)
            except Exception as exc:  # network/timeout from transport
                last_exc = ContextDevError(ErrorKind.TIMEOUT, f"transport error: {exc}")
                if attempt < self.max_retries:
                    await asyncio.sleep(backoff_seconds(attempt))
                    continue
                raise last_exc from exc
            status = resp.status_code
            if 200 <= status < 300:
                self.breaker.record_success()
                try:
                    payload = resp.json()
                except Exception:
                    payload = {"text": resp.text}
                return payload, {"feature": feature, "endpoint_status": ep.status,
                                 "status_code": status}
            kind = classify_status(status, resp.text if isinstance(resp.text, str) else "")
            retry_after = parse_retry_after(resp.headers.get("retry-after")
                                            or resp.headers.get("Retry-After"))
            err = ContextDevError(kind, f"Context.dev {feature} failed: HTTP {status}",
                                  status=status, retry_after=retry_after)
            if status == 429 and attempt < self.max_retries:
                await asyncio.sleep(retry_after if retry_after is not None
                                    else backoff_seconds(attempt))
                continue
            if kind in (ErrorKind.RETRYABLE, ErrorKind.UPSTREAM, ErrorKind.TIMEOUT) \
                    and attempt < self.max_retries:
                self.breaker.record_failure()
                await asyncio.sleep(backoff_seconds(attempt))
                continue
            self.breaker.record_failure()
            raise err
        raise last_exc or ContextDevError(ErrorKind.UPSTREAM, "request failed")

    # Convenience wrappers (all return NormalizedResult via normalize_generic)
    async def scrape(self, url: str, *, formats=None, idempotency_key=None):
        payload, _ = await self.request(
            "scrape", {"url": url, "formats": formats or {"markdown": True}},
            idempotency_key=idempotency_key)
        return normalize_generic("scrape", payload)

    async def search(self, query: str, **kwargs):
        payload, _ = await self.request("search", {"query": query, **kwargs})
        return normalize_generic("search", payload)

    async def crawl(self, url: str, **kwargs):
        payload, _ = await self.request("crawl", {"url": url, **kwargs})
        return normalize_generic("crawl", payload)

    async def map_urls(self, url: str, **kwargs):
        payload, _ = await self.request("map", {"url": url, **kwargs})
        return normalize_generic("map", payload)

    async def answers(self, question: str, **kwargs):
        payload, _ = await self.request("answers", {"question": question, **kwargs})
        return normalize_generic("answers", payload)

    async def parse(self, **kwargs):
        payload, _ = await self.request("parse", kwargs)
        return normalize_generic("parse", payload)

    async def brand(self, domain: str, **kwargs):
        payload, _ = await self.request("brand", {"domain": domain, **kwargs})
        return normalize_generic("brand", payload)

    async def people(self, query: str, **kwargs):
        payload, _ = await self.request("people_search", {"query": query, **kwargs})
        return normalize_generic("people", payload)

    async def company(self, query: str, **kwargs):
        payload, _ = await self.request("company_search", {"query": query, **kwargs})
        return normalize_generic("company", payload)

    async def news(self, query: str, **kwargs):
        payload, _ = await self.request("news", {"query": query, **kwargs})
        return normalize_generic("news", payload)

    async def close(self):
        if self._transport is not None and hasattr(self._transport, "aclose"):
            await self._transport.aclose()
