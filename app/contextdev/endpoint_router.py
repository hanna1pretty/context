"""Single ENDPOINTS table. VERIFIED vs PATTERN-INFERRED is explicit.

VERIFIED: scrape, crawl (from the task's verified facts + user screenshot anchor).
PATTERN-INFERRED: everything else follows /v1/web/<feature> ONLY because the
base URL is https://api.context.dev/v1 and scrape/crawl live under /v1/web/.
Inferred paths MUST be re-checked against docs.context.dev before relying on
them; the client degrades gracefully on 404 (see errors.UNSUPPORTED path:
client surfaces NOT_FOUND with a clear message, workers mark the job failed
with a safe message, never a fake result).
Pricing anchors are per the task (credits), not re-fetched here.
"""
from __future__ import annotations

from dataclasses import dataclass

VERIFIED = "VERIFIED"
PATTERN_INFERRED = "PATTERN-INFERRED"


@dataclass(frozen=True)
class Endpoint:
    feature: str
    method: str
    path: str  # relative to CONTEXT_DEV_BASE_URL, e.g. /web/scrape
    status: str
    min_credits: int
    notes: str = ""


ENDPOINTS: dict[str, Endpoint] = {
    "scrape": Endpoint("scrape", "POST", "/web/scrape", VERIFIED, 1,
                       "Body {url, formats:{markdown:true}}; verified response shape. "
                       "Screenshot VERIFIED: formats:{screenshot:true} (+ optional "
                       "screenshotParams) -> screenshot {requested, success, data} "
                       "with data as a base64 image data URL; older GET "
                       "/web/scrape/screenshot is equivalent. Standard scrape "
                       "is 1 credit; credits_consumed from key_metadata is "
                       "authoritative, no screenshot surcharge is hardcoded."),
    "crawl": Endpoint("crawl", "POST", "/web/crawl", VERIFIED, 1,
                      "1 credit/page, up to 500 pages in one call; larger -> batches."),
    "search": Endpoint("search", "POST", "/web/search", PATTERN_INFERRED, 1, ""),
    "map": Endpoint("map", "POST", "/web/map", PATTERN_INFERRED, 1, ""),
    "answers": Endpoint("answers", "POST", "/web/answers", PATTERN_INFERRED, 10, ""),
    "parse": Endpoint("parse", "POST", "/web/parse", PATTERN_INFERRED, 1, ""),
    "brand": Endpoint("brand", "POST", "/web/brand", PATTERN_INFERRED, 10, ""),
    "styleguide": Endpoint("styleguide", "POST", "/web/styleguide", PATTERN_INFERRED, 10,
                           "Assumed brand-adjacent; may be part of brand endpoint."),
    "people_search": Endpoint("people_search", "POST", "/web/people/search", PATTERN_INFERRED, 10, ""),
    "people_enrich": Endpoint("people_enrich", "POST", "/web/people/enrich", PATTERN_INFERRED, 20, ""),
    "company_search": Endpoint("company_search", "POST", "/web/company/search", PATTERN_INFERRED, 2, ""),
    "news": Endpoint("news", "POST", "/web/news", PATTERN_INFERRED, 1, ""),
    "batches": Endpoint("batches", "POST", "/web/batches", PATTERN_INFERRED, 1,
                        "Batch mode also used for large crawls."),
    "monitors": Endpoint("monitors", "POST", "/web/monitors", PATTERN_INFERRED, 1, ""),
}


def endpoint_for(feature: str) -> Endpoint:
    try:
        return ENDPOINTS[feature]
    except KeyError as exc:
        raise ValueError(f"unknown Context.dev feature: {feature}") from exc


def choose_endpoint_for_input(text: str) -> str:
    """Conversational routing: bare URL -> scrape; question -> answers."""
    t = (text or "").strip()
    if t.startswith(("http://", "https://")):
        return "scrape"
    if t.endswith("?") or t.lower().startswith(("what ", "how ", "why ", "apa ", "bagaimana ")):
        return "answers"
    return "search"
