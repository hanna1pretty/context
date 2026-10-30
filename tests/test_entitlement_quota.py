from app.services.subscription_service import check_daily_quota, check_feature, plan_limits
from app.services.credit_service import estimate_credits
from app.services.usage_service import UsageStore
from app.services.job_service import Job, can_cancel, can_view, owns

def test_free_cannot_crawl_but_can_scrape():
    assert check_feature("free", "scrape").allowed
    assert not check_feature("free", "crawl").allowed
    assert check_feature("pro", "crawl").allowed
def test_daily_quota_boundary():
    assert check_daily_quota("free", 9).allowed
    assert not check_daily_quota("free", 10).allowed
def test_usage_store():
    s = UsageStore(); s.record(1, "2026-10-30", "scrape", 1); s.record(1, "2026-10-30", "scrape", 2)
    assert s.used_today(1, "2026-10-30") == 2 and s.credits_today(1, "2026-10-30") == 3
    assert s.used_today(2, "2026-10-30") == 0
def test_credit_estimates_anchor():
    assert estimate_credits("scrape") == 1
    assert estimate_credits("answers") == 10
    assert estimate_credits("crawl", pages=500) == 500
def test_ownership():
    j = Job(id="j1", user_id=7, kind="scrape", status="queued")
    assert owns(j, 7) and can_view(j, 7) and can_cancel(j, 7)
    assert not can_view(j, 8) and not can_cancel(j, 8)
    assert can_view(j, 8, admin=True)
    j.status = "done"; assert not can_cancel(j, 7)
