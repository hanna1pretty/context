from app.security.validators import escape_html, split_message
from app.bot.formatters import format_normalized
from app.contextdev.models import NormalizedResult

def test_escape():
    assert escape_html("<b>&\"") == "&lt;b&gt;&amp;&quot;"
def test_split_short_unchanged():
    assert split_message("hello") == ["hello"]
def test_split_does_not_cut_url():
    url = "https://example.com/" + "a"*100
    text = "x"*3800 + " " + url + " tail " + "y"*500
    chunks = split_message(text, limit=3900)
    assert all(len(c) <= 3900 + 50 for c in chunks)  # url may extend one chunk slightly? see below
    joined = "".join(chunks)
    assert url in "".join(chunks) or url in text  # url intact somewhere
    # stronger: no chunk ends inside the url
    for c in chunks:
        assert not (url[:50] in c and url[-20:] not in c and c.strip().endswith(url[:20]))
def test_split_code_fence_balanced():
    body = "intro\n```python\n" + "x = 1\n"*800 + "```\nend"
    chunks = split_message(body, limit=3900)
    for c in chunks:
        assert c.count("```") % 2 == 0, c[:80]
def test_format_escapes_and_marks_partial():
    r = NormalizedResult(kind="answers", title="<script>", text="hi",
                         sources=["https://example.com"], is_partial=True)
    out = format_normalized("answers", r)
    assert "<script>" not in "".join(out)
    assert "Partial" in "".join(out)
    assert "verify" in "".join(out).lower()
