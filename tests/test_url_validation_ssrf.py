import pytest
from app.security.validators import (check_upload, sanitize_filename,
                                     validate_url, validate_url_no_dns)

def pub(host): return [host]
def test_public_ok():
    assert validate_url("https://example.com/page", resolver=lambda h: ["93.184.216.34"])
def test_rejects_schemes():
    for u in ["ftp://example.com", "file:///etc/passwd", "javascript:alert(1)"]:
        with pytest.raises(ValueError): validate_url(u, resolver=pub)
def test_rejects_localhost_and_private_literal():
    for u in ["http://localhost/admin", "http://127.0.0.1/", "http://10.0.0.5/",
              "http://192.168.1.1/", "http://169.254.1.1/", "http://[::1]/"]:
        with pytest.raises(ValueError): validate_url_no_dns(u)
def test_rejects_private_dns():
    with pytest.raises(ValueError):
        validate_url("https://example.com/", resolver=lambda h: ["10.1.2.3"])
def test_rejects_credentials_and_empty():
    with pytest.raises(ValueError): validate_url("https://user:pass@example.com/", resolver=pub)
    with pytest.raises(ValueError): validate_url("", resolver=pub)
def test_no_dns_version_allows_public_name():
    assert validate_url_no_dns("https://example.com/") == "https://example.com/"
def test_filename_traversal():
    assert sanitize_filename("../../etc/passwd") == "passwd"
    assert sanitize_filename("a/b\\c.pdf") == "c.pdf"
def test_upload_limits():
    with pytest.raises(ValueError): check_upload("x.pdf", "application/pdf", 21*1024*1024)
    with pytest.raises(ValueError): check_upload("x.exe", "application/x-msdownload", 10)
    assert check_upload("doc.pdf", "application/pdf", 100) == "doc.pdf"
