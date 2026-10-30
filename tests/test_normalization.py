from app.contextdev.result_normalizer import normalize_scrape, normalize_search, normalize_generic

def test_scrape_verified_shape():
    payload = {"url": "https://example.com", "markdown": {"data": "# Hello"},
               "metadata": {"title": "Example"}, "request_id": "req_1",
               "key_metadata": {"credits_consumed": 1},
               "formats": {"markdown": {"requested": True, "success": True}},
               "isPartial": False}
    n = normalize_scrape(payload)
    assert n.text == "# Hello" and n.title == "Example"
    assert n.request_id == "req_1" and n.credits.consumed == 1 and not n.is_partial
    assert n.sources == ["https://example.com"]
def test_partial_surfaced():
    n = normalize_scrape({"markdown": {"data": "x"}, "isPartial": True})
    assert n.is_partial
def test_search_items_and_missing_fields():
    n = normalize_search({"results": [{"title": "A", "url": "https://a.example", "snippet": "s"},
                                      {"url": "https://b.example"}]})
    assert len(n.items) == 2 and n.sources[0] == "https://a.example"
    assert n.items[1]["title"] is None
def test_generic_never_invents():
    n = normalize_generic("brand", {"foo": 1})
    assert n.text is None and n.items == [] and n.sources == []
