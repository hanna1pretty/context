import time
from app.security.rate_limit import ConcurrencyTracker, SlidingWindowLimiter
from app.contextdev.endpoint_router import ENDPOINTS, endpoint_for, choose_endpoint_for_input

def test_sliding_window():
    t = [0.0]
    lim = SlidingWindowLimiter(2, 60.0, clock=lambda: t[0])
    assert lim.allow("u1") and lim.allow("u1") and not lim.allow("u1")
    t[0] = 61.0
    assert lim.allow("u1")
def test_concurrency_cap():
    c = ConcurrencyTracker(2)
    assert c.acquire(1) and c.acquire(1) and not c.acquire(1)
    c.release(1); assert c.acquire(1)
def test_endpoint_matrix_verified_vs_inferred():
    assert endpoint_for("scrape").status == "VERIFIED"
    assert endpoint_for("crawl").status == "VERIFIED"
    assert endpoint_for("search").status == "PATTERN-INFERRED"
    assert endpoint_for("scrape").path == "/web/scrape"
    assert endpoint_for("crawl").path == "/web/crawl"
    assert all(e.path.startswith("/web/") for e in ENDPOINTS.values())
def test_routing():
    assert choose_endpoint_for_input("https://example.com") == "scrape"
    assert choose_endpoint_for_input("apa itu X?") == "answers"
