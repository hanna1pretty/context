# Context.dev feature matrix — verified vs inferred

Source of truth for this build: the verified facts supplied with the task
(scrape shape, crawl limits, pricing anchors, concurrency caps). No live
Context.dev docs re-fetch was performed in this VM for the other endpoints,
so they are marked PATTERN-INFERRED and the client degrades gracefully on
404/unsupported instead of presenting inferred paths as verified.

| Feature | Endpoint (base https://api.context.dev/v1) | Status | Min credits (anchor) |
|---|---|---|---|
| Scrape | POST /web/scrape, body {url, formats:{markdown:true}}, header Authorization: Bearer <API_KEY>; response markdown.data, metadata.title, request_id, key_metadata.credits_consumed, per-format {requested,success,data}, isPartial | VERIFIED | 1 |
| Crawl | POST /web/crawl; follows links, up to 500 pages Markdown in one call, page/depth/path/time limits; larger sites use Batches in crawl mode | VERIFIED | 1/page |
| Search | POST /web/search | PATTERN-INFERRED | from 1 |
| Map | POST /web/map | PATTERN-INFERRED | from 1 |
| Answers | POST /web/answers | PATTERN-INFERRED | from 10 |
| Parse | POST /web/parse | PATTERN-INFERRED | from 1 |
| Brand | POST /web/brand | PATTERN-INFERRED | 10 |
| Styleguide | POST /web/styleguide (may be part of brand) | PATTERN-INFERRED | 10 (assumed) |
| People search | POST /web/people/search | PATTERN-INFERRED | from 10 |
| People enrich | POST /web/people/enrich | PATTERN-INFERRED | 20 |
| Company search | POST /web/company/search | PATTERN-INFERRED | 2 |
| News | POST /web/news | PATTERN-INFERRED | from 1 |
| Batches | POST /web/batches | PATTERN-INFERRED | 1 (assumed base) |
| Monitors | POST /web/monitors | PATTERN-INFERRED | 1 (assumed base) |
| JSON extraction | scrape with JSON format | PATTERN-INFERRED (pricing anchor: 5/page) | 5/page |

Concurrency caps (anchor, per account plan): Free 2, Developer 10, Pro 100,
Growth 250, Scale 500. Set CONTEXT_DEV_MAX_CONCURRENCY from your plan —
do not assume 100.

Before relying on any PATTERN-INFERRED row, re-check docs.context.dev
(api-reference for that feature) and update this table + endpoint_router.py.
If a re-check contradicts an inferred path, docs win (spec rule 1/section 1.5).
