# Context.dev feature matrix — verified vs inferred

Source of truth for this build: the verified facts supplied with the task
(scrape shape, crawl limits, pricing anchors, concurrency caps). No live
Context.dev docs re-fetch was performed in this VM for the other endpoints,
so they are marked PATTERN-INFERRED and the client degrades gracefully on
404/unsupported instead of presenting inferred paths as verified.

| Feature | Endpoint (base https://api.context.dev/v1) | Status | Min credits (anchor) |
|---|---|---|---|
| Scrape | POST /web/scrape, body {url, formats:{markdown:true}}, header Authorization: Bearer <API_KEY>; response markdown.data, metadata.title, request_id, key_metadata.credits_consumed, per-format {requested,success,data}, isPartial | VERIFIED | 1 |
| Scrape — Screenshot | POST /web/scrape, body {url, formats:{screenshot:true, markdown:true}, screenshotParams? (optional, only with formats.screenshot:true)}; response screenshot {requested, success, data} where data is a base64 image data URL; older GET /web/scrape/screenshot is equivalent to formats.screenshot:true. Normalizer only accepts screenshot when success==true and data starts with "data:image/"; otherwise it reports success=false/None, never a fake success. Delivery: Telegram photo via services/screenshot_delivery.py (png/jpeg/webp only, max 10 MB decoded), with markdown text fallback when the screenshot is missing/failed/oversized. | VERIFIED | 1 (standard scrape credit; key_metadata.credits_consumed is authoritative — no screenshot surcharge is hardcoded) |
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
