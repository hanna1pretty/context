import hashlib, hmac
from app.api.context_webhooks import DEDUP, WebhookDedup, verify_signature

def test_signature_ok_and_bad():
    body = b'{"event_id":"e1"}'; secret = "s3cret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_signature(body, sig, secret)
    assert not verify_signature(body, "0"*64, secret)
    assert not verify_signature(body, None, secret)
    assert not verify_signature(body, sig, "")  # no secret configured -> refuse
def test_dedup():
    d = WebhookDedup()
    assert not d.is_duplicate("e1")
    assert d.is_duplicate("e1")
    assert not d.is_duplicate("e2")
def test_module_dedup_singleton_behaves():
    assert not DEDUP.is_duplicate("unique-test-event-xyz")
