import asyncio, random
import pytest
from app.contextdev.retry import CircuitBreaker, backoff_seconds, parse_retry_after
from app.contextdev.client import ContextDevClient, _Response
from app.contextdev.errors import ContextDevError

def test_parse_retry_after():
    assert parse_retry_after("5") == 5.0
    assert parse_retry_after("garbage") is None
    assert parse_retry_after(None) is None
def test_backoff_bounded_and_grows():
    rng = random.Random(1)
    vals = [backoff_seconds(i, base=1.0, cap=60.0, jitter=0.0, rng=rng) for i in range(6)]
    assert vals == [1, 2, 4, 8, 16, 32]
    assert backoff_seconds(20, jitter=0.0) == 60.0
def test_circuit_breaker():
    t = [0.0]
    cb = CircuitBreaker(failure_threshold=2, reset_seconds=10, clock=lambda: t[0])
    assert cb.allow()
    cb.record_failure(); cb.record_failure()
    assert cb.state == "open" and not cb.allow()
    t[0] = 11.0
    assert cb.state == "half-open" and cb.allow()
    cb.record_success(); assert cb.state == "closed"

class FakeTransport:
    def __init__(self, responses): self.responses = responses; self.calls = 0
    async def post(self, url, *, json, headers, timeout):
        r = self.responses[min(self.calls, len(self.responses)-1)]; self.calls += 1
        return _Response(r[0], r[1], r[2])

@pytest.mark.asyncio
async def test_client_honours_429_then_succeeds(monkeypatch):
    # patch asyncio.sleep in client module to avoid real waiting
    import app.contextdev.client as cm
    async def nosleep(_): return None
    monkeypatch.setattr(cm.asyncio, "sleep", nosleep)
    tr = FakeTransport([(429, {"retry-after": "1"}, "rate limited"),
                        (200, {}, {"markdown": {"data": "# hi"}, "metadata": {"title": "T"},
                                    "request_id": "r1", "url": "https://example.com"})])
    client = ContextDevClient(api_key="k", http_client=tr)
    res = await client.scrape("https://example.com")
    assert tr.calls == 2 and res.text == "# hi" and res.title == "T"

@pytest.mark.asyncio
async def test_client_401_not_retried(monkeypatch):
    import app.contextdev.client as cm
    async def nosleep(_): return None
    monkeypatch.setattr(cm.asyncio, "sleep", nosleep)
    tr = FakeTransport([(401, {}, "unauthorized")])
    client = ContextDevClient(api_key="k", http_client=tr)
    with pytest.raises(ContextDevError) as ei:
        await client.scrape("https://example.com")
    assert tr.calls == 1 and ei.value.kind.value == "auth"
