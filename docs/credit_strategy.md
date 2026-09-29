# Credit strategy

## Principle

Spend credits only to answer an analyst action. Reuse an immutable normalized response for the same endpoint/parameters within its freshness window. A cache hit must be shown as a cache hit in the agent trace and must not be represented as a new live retrieval.

## Cost facts from official documentation

| Call | Documented cost | Policy |
| --- | ---: | --- |
| Structured Companies Screener | 1 | Preferred discovery/resolution method. |
| Natural-language Companies Screener | 3 on success; 1 if translation reaches model then fails | Do not expose as the primary tool; translate user intent into validated structured filters. |
| Company Report | 1 per requested section; all sections default to 8 | Always use `sections`; base investigation requests 3--4 sections only. |
| Quarterly Financials | 1 per returned quarter | Request exactly the number of periods required; start at four. |
| Quarterly dates (company) | 1 | Cache by company for 30 days or until freshness index indicates a change. |
| Latest quarterly dates universe | 1/page; about 32 full-universe pages | Do not run automatically. Poll `since` only after an initial intentional load. |
| Daily symbol transaction data | 1 | Request one 90-day window per investigated company. |
| Full-universe close | 1/page; about 32 pages | No normal-path use. |
| Top movers | 1 per classification × period; default 10 | Ask for one classification/period only if used. |

## Cache and call policy

| Data | TTL / invalidation | Normal path |
| --- | --- | --- |
| Taxonomy (`/v2/subsectors/`) | 30 days | Load once; validate UI selections locally. |
| Structured screen result | 1 trading day or user refresh | Reuse across discovery, peer selection, and follow-up. |
| Company overview/peers/valuation | 1 trading day | Fetch sections only when report needs them. |
| Annual financial report section | 7 days or manual refresh | Reuse during the entire research conversation. |
| Quarterly dates / financials | Until a newer report date is known; otherwise 7 days | One company at a time. |
| Daily market data | Same trading day | One 90-day retrieval per company. |
| Research evidence/memory | Session + persisted timestamped snapshot | Never silently refresh during a follow-up; disclose stale evidence. |

## Estimated allocation from the current 600-credit balance

These are conservative design targets, not observed consumption. They must be updated after authorized representative tests.

| Stage | Budget | What it covers |
| --- | ---: | --- |
| Documentation/live schema validation | 30 | One structured Banks screen and one BBRI investigation fixture, including bounded error checks. |
| Discovery calibration | 90 | A small number of bounded Screener requests, scoring tuning, and cache validation. |
| UI/agent integration | 120 | End-to-end work on a controlled company set. |
| Demo rehearsal | 80 | Cached-first rehearsals plus small live fallback. |
| Submission reserve | 180 | Final recording, refresh, and contingency. |
| Emergency reserve | 100 | Valid 404s, schema drift, or required revalidation. |
| **Total** | **600** | Current observed balance; never consume reserve for a broad scan. |

### Illustrative live investigation envelope

One selected bank should normally cost roughly **8--12 credits**: one structured screen/resolution (1), report sections overview/financials/peers/valuation (4), company quarterly dates (1), four quarters (4), daily series (1). The actual total depends on whether cached data exists and whether `n_quarters=4` returns exactly four records; instrument and display the observed count rather than assume it.

## Guardrails

- Cache key: API version + path + sorted query parameters + canonical symbol. Do not include the API key.
- Validate ticker shape, sections, date range, subsector slug, and requested metric before the network call.
- Treat a `404` as billable; resolve ambiguities using the Screener first.
- Enforce a per-investigation credit ceiling in the orchestrator and require explicit user confirmation before expansion.
- Do not retry `4xx` other than a deliberate one-time auth refresh; use capped exponential retries for `429/5xx`.
- Log endpoint, status, record count, cache status, and credit estimate—never credential/header values.
