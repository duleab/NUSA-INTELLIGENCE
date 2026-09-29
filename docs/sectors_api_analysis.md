# Sectors API analysis for NUSA Intelligence

**Research date:** 22 September 2026
**Scope:** Official Sectors Hackathon, API v2, MCP documentation, and one authenticated Playground validation. The API key is deliberately not stored, copied, logged, or placed in this repository.

## Authenticated validation

**REAL DATA ACCESS: YES.** On 22 September 2026, the authenticated Sectors API Playground showed **600 credits remaining** and returned **HTTP 200** from `GET /v2/subsectors/`. The response contained 33 actual IDX sector/subsector slug pairs, including `financials` / `banks`; the Playground explicitly distinguishes this signed-in response from Demo Mode mock data. No additional live endpoint was executed in this pass.

This validates authenticated API access and the taxonomy required by the Banks MVP. It does **not** yet validate the exact live schema, returned-row count, or observed charge for Screener, Company Report, Quarterly Financials, or Daily Transaction Data; those remain the next controlled tests after an environment-safe API-key setup.

## Stage 4.5 controlled Screener attempt

On 25 September 2026, one bounded structured request was made to `GET /v2/companies/` with `where=sub_sector = 'Banks'`, `order_by=-market_cap`, `limit=50`, `offset=0`, and `include_query_values=true`. It returned **HTTP 403**. Retries were disabled and no second request was made. No response rows, schema, metrics, or anomaly results were available to inspect. No credit-balance header was exposed; the API error table above documents 403 responses as free, so the documented expected consumption is zero, but the account balance was not independently observed.

The failed response was not retained as a fixture. The key was read from the project environment file into the request process and was not printed or stored by this validation. `.gitignore` contains a `.env` rule, but this workspace is not a Git worktree, so `git check-ignore` could not be run. The live Screener schema and metric coverage remain unverified; the earlier authenticated `/v2/subsectors/` result does not establish Screener authorization.

## Playground comparison and second controlled attempt

The user subsequently reported a successful authenticated Playground request returning 48 Banks and the top market-cap rows. Its deterministic parameters were `where=sub_sector = 'Banks' and market_cap IS NOT NULL`, `order_by=-market_cap`, `limit=3`, null/omitted `offset`, and `include_query_values=true`. The reported row shape was `symbol`, `company_name`, and `query_values` (`sub_sector`, `market_cap`), plus `pagination` and `llm_translation`.

The official Screener reference independently documents `GET /v2/companies/`, a required raw API key in the `Authorization` header, the `where`, `order_by`, `limit`, `offset`, and `include_query_values` parameter names, URL-query usage, and bracketed annual/quarterly field syntax. Thus the earlier client already used the documented endpoint and authorization-header form. Its material differences from the Playground request were that it omitted `market_cap IS NOT NULL` and explicitly sent `offset=0` (the documented default); neither difference explains a 403 on its own.

On 25 September 2026, after aligning those base parameters, one additional request was attempted with retries disabled. To request historical values in `query_values`, it used the Playground's Bank/market-cap filter plus an OR group of documented annual metric `IS NOT NULL` predicates for 2025 and 2024, `order_by=-market_cap`, `limit=50`, omitted offset, and `include_query_values=true`. The URL was formed with standard percent-encoding (`urllib.parse.urlencode`); authentication used `Authorization: <key>` with no `Bearer` prefix. The request returned **HTTP 403**. No rows or body schema were available, no response was retained, and no further request was made. No credit-balance header was exposed; the documented structured-query price is one credit, while the API's error semantics say 403 is free, so expected consumption is zero. An actual before/after account balance was not observable.

The 403 does not establish an account-entitlement failure. The large historical-field query was not identical to the successful three-row Playground query, and the direct request's authentication context cannot be compared with the Playground's internal credential handling from available evidence. The cause is unresolved; no further retries are authorized in this validation.

## Documented Screener metric/query capability (not live coverage)

The current Companies Screener reference documents annual values as `field[YYYY]`, quarterly values as `field[Qn-YYYY]`, arithmetic and field-to-field query expressions, and `include_query_values`. It lists bank-relevant annual fields including `revenue`, `earnings`, `eps`, `net_interest_income`, interest and non-interest income, `gross_loan`, `net_loan`, `total_deposit`, loan-loss allowance, assets, liabilities, equity, capital, risk-weighted assets, `roa`, `roe`, `net_interest_margin`, `capital_adequacy_ratio`, `casa_ratio`, `leverage_ratio`, `loan_to_deposit_ratio`, `liquidity_coverage_ratio`, and `efficiency_ratio`; annual `pe` and `pb` are also documented. General cash-flow fields (`operating_cash_flow`, `free_cash_flow`) and general margins are documented, but their interpretation/comparability for banks needs care. The API reference describes monetary fundamental fields in IDR; query values themselves do not carry unit metadata.

The Screener documentation does not expose a separate `select`/`columns` query parameter. The attempted client therefore referenced metric fields in an OR-of-non-null `where` predicate and set `include_query_values=true`; whether that produces all referenced historical values while preserving the full 48-bank universe remains **unverified** because the request returned 403. The predicate may exclude a bank if all requested annual metrics are null. Documented field availability is not evidence of live coverage or peer comparability.

No live Screener fixture was saved. The official rules and the API reference inspected for this pass do not specify whether raw Screener responses may be retained in a public development fixture. No LLM, agent, evidence, memory, or UI work was started.

## Executive finding

Sectors API v2 can support a focused, evidence-backed NUSA MVP. Its strongest fit is a **subsector-bounded discovery workflow** paired with autonomous single-company investigations. The decisive sources are the structured Companies Screener, quarterly financials, the company report's `financials`, `valuation`, and `peers` sections, and the daily transaction feed.

Do not build an all-IDX historical-fundamental scan for the MVP: quarterly financials cost one credit *per returned quarter*, so wide historical retrieval will exhaust a 1,000-credit grant. Use a 20--50 company subsector universe or an index-defined universe, cache it, and make investigation-on-click the normal detailed path.

## Access, onboarding, and rules

| Topic | Official finding | NUSA implication |
| --- | --- | --- |
| API access | API keys are created in the Sectors API page for authenticated eligible access; requests use `Authorization: <key>`. | Read `SECTORS_API_KEY` only from the environment; never send it to the browser or logs. |
| Hackathon credit grant | Registered teams can claim 1,000 credits after every member completes onboarding. | Treat 1,000 credits as a hard shared build/demo budget. |
| Track 01 | Custom agent logic/orchestration and an AI/LLM component are mandatory; a prompt-only MCP client does not qualify. | Keep the Python planner, tool registry/router, deterministic analytics, evidence validator, and structured memory visible in the repo/UI. |
| MCP | Cloud-hosted Streamable HTTP server at `https://sectors-mcp.supertype.ai/mcp`; documentation states 65+ tools. | REST is recommended for the MVP's deterministic and credit-aware data layer. MCP may be a supplementary adapter, never the complete agent implementation. |

## Billing and error semantics

| Status | Credit effect | Required client behavior |
| --- | --- | --- |
| 2xx | Endpoint's stated cost | Cache normalized response plus request fingerprint. |
| 400 | Free, except a natural-language screener query that reached the model costs 1 | Validate symbols, dates, sections, and structured filters locally. |
| 401 / 403 | Free | Report missing/invalid authorization without retrying. |
| 404 | Costs 1 | Resolve symbols through screener before specific-resource endpoints. |
| 429 | Free | Exponential backoff; surface rate-limit state. |
| 5xx | Free | Retry a bounded number of times and preserve the failure in execution trace. |

Empty list/filter results are valid `200` responses and therefore billable. Documentation exposes a `RATE_LIMIT_EXCEEDED` response but does **not** publish a numeric request-per-minute limit; do not invent one.

## Relevant documented endpoints

All paths below are prefixed by `https://api.sectors.app`; all are `GET` and require the `Authorization` header.

| Purpose | Path and parameters | Response / depth | Cost and paging | NUSA use |
| --- | --- | --- | --- | --- |
| Resolve, constrain universe, and fetch current comparison fields | `/v2/companies/` — `where`, `order_by`, `desc`, `limit` (1--200), `offset`, `include_query_values`; or mutually exclusive natural-language `q` | Paginated `results` with symbol/name and optional requested query values; supports annual/forecast field bracket syntax and arithmetic predicates. | Structured: 1 credit; `q`: 3 credits on success. Offset pagination. | **Primary Discovery entry point.** Use structured filters generated/validated by our planner, not raw LLM text. |
| Company profile, annual history, peer/valuation data | `/v2/company/report/{symbol}/` — required path symbol; optional comma-separated `sections` | Sections: `overview`, `valuation`, `future`, `peers`, `financials`, `dividend`, `management`, `ownership`. Financials include annual history/ratios; valuation includes historical PB/PE/PS/PCF/PEG; peers is within same subsector. | 1 credit per requested section; default 8. No pagination documented. | Investigation backbone. Ask only for `overview,financials,peers,valuation` as needed. |
| Available quarterly reporting dates for one company | `/v2/company/get_quarterly_financial_dates/{symbol}/` | Dates grouped by year. | 1 credit; no paging documented. | Fetch once per company; drives valid financial queries. |
| Latest quarterly date across IDX | `/v2/companies/quarterly-financial-dates/` — documented `since` incremental-polling parameter, paginated | One latest quarter/date per company; about 950 companies; firms without quarterly data omitted. | 1 credit/page; about 32 pages at max 30. | Optional freshness index; avoid full sweep for MVP unless cached. |
| Quarterly fundamentals | `/v2/financials/quarterly/{symbol}/` — optional `report_date`, `approx` (default true), `n_quarters` | Quarter records: revenue, earnings, assets, equity, cash-flow measures; financial-sector extras include interest income/expense, NII, gross/net loan, deposits. Fields vary by sector. | **1 credit per returned quarter**. | Primary historical anomaly source; request only four quarters for a selected company, subject to API validation. |
| Peer/subsector summary | `/v2/subsector/report/{sub_sector}/` — sections `statistics`, `market_cap`, `stability`, `valuation`, `growth`, `companies` | Subsector-level aggregates and company list. Valid slug from `/v2/subsectors/`. | 1 credit/section; default 6. | Cheap peer baseline; request `companies,growth,valuation` only when needed. |
| Taxonomy | `/v2/subsectors/` | Sector/subsector kebab-case pairs. | 1 credit. | Cache long-lived; populate sector controls and validate slugs. |
| Market history | `/v2/daily/{symbol}/` — optional `start`, `end` | OHLC, volume, market cap. Defaults 30 days; maximum 90; wider windows are clamped to latest 90. | 1 credit; no paging documented. | Price, volume, market-cap and price/fundamental-divergence checks. |
| Market-wide daily closes | `/v2/close/` — optional date plus documented pagination | Daily close for all IDX tickers; missing tickers omitted. | 1 credit/page; about 32 pages for ~950 tickers. | Not core MVP; consider only a cached snapshot, not a historic scanner. |
| Top movers | `/v2/companies/top-changes/` — classifications `top_gainers`/`top_losers`, periods `1d,7d,14d,30d,365d` | Ranked movers by selected time windows. | 1 credit per classification × period; default 10. | Optional discovery seed; request a single period/classification. |
| Most traded | `/v2/companies/most-traded/` — date range up to 90 days | Ranked transaction-volume data keyed by date. | Documented in index; validate exact schema/cost after access. | Optional market-attention context. |
| Foreign-flow context | `/v2/foreign-flow/` — date, pagination/order controls in reference | Daily net foreign flow for every ticker; about 20--25 pages for full universe. | 1 credit/page. | Stretch feature only; never pull full universe in normal workflow. |
| Per-company foreign flow | `/v2/foreign-flow/{symbol}/` | Daily net foreign inflow / foreign share, up to 90 days. | Documented in index; validate exact parameters/cost after access. | Useful optional evidence for one-company research. |
| News, filings, actions, suspensions | `/v2/news/`, `/v2/filings/`, corporate-action and suspension endpoints | Paginated/filterable event information. | Schema/cost must be verified after access. | Optional contextual evidence; keep outside base anomaly score. |

## IDX endpoint inventory

This is a documentation-first inventory of every IDX category shown by the API Playground, supplemented by the official v2 reference. All are `GET`. “Per page” feeds must not be treated as bulk-free calls.

| Category | Endpoint / path | Stated cost | NUSA relevance / limitation |
| --- | --- | ---: | --- |
| Company Screener | Companies Screener — `/v2/companies/` | 1 structured; 3 natural-language | **Core Discovery.** Offset pagination; `where`, `order_by`, `limit`, `offset`, `include_query_values`; can return multiple companies with requested query values in one response. |
| Company Screener | Free Float Market Analysis — `/v2/free-float/` | 1 per 100 returned | Optional liquidity/context signal, not base score. |
| Helper Lists | Companies with Revenue Segments — `/v2/companies/list_companies_with_segments/` | 1 | Availability discovery for segment analysis. |
| Helper Lists | Quarterly Financial Dates — `/v2/company/get_quarterly_financial_dates/{symbol}/` | 1 | Required before exact quarterly retrieval. |
| Helper Lists | Latest Quarterly Financial Dates — `/v2/companies/quarterly-financial-dates/` | 1/page | ~32 pages full IDX; use `since` only for freshness polling. |
| Helper Lists | Industries / Subindustries / Subsectors — `/v2/industries/`, `/v2/subindustries/`, `/v2/subsectors/` | 1 each | Taxonomy cache; subsectors live-validated. |
| Helper Lists | News Tags — `/v2/tags/` | 1 | Optional controlled-news filters. |
| Detailed Reports | Corporate Actions — `/v2/company/corporate-actions/{symbol}/` | 1 | Event context for a selected company only. |
| Detailed Reports | Company Revenue Segments — `/v2/company/get-segments/{symbol}/` | 1 | Optional revenue/cost mix explanation. |
| Detailed Reports | Company Report — `/v2/company/report/{symbol}/` | 1/section; default 8 | **Core Investigation.** Section-select `overview`, `financials`, `peers`, `valuation`. |
| Detailed Reports | Shareholders Composition — `/v2/company/shareholders-composition/{symbol}/` | 1 | Optional ownership evidence. |
| Detailed Reports | Company Quarterly Financials — `/v2/financials/quarterly/{symbol}/` | 1/returned quarter | **Core Investigation.** Company/sector-specific depth and fields. |
| Detailed Reports | Subsector Report — `/v2/subsector/report/{sub_sector}/` | 1/section; default 6 | Peer aggregate / valuation / growth context. |
| Transaction Data | Full-universe close — `/v2/close/` | 1/page | ~32 pages; avoid normal-path full pulls. |
| Transaction Data | Daily Transaction Data — `/v2/daily/{symbol}/` | 1 | **Core Investigation.** OHLC, volume, market cap; max 90 days. |
| Transaction Data | IDX Market Summary — `/v2/idx-total/` | 1 | Optional market-regime context. |
| Transaction Data | Full-universe index close / index history — `/v2/index-daily/`, `/v2/index-daily/{index_code}/` | 1 | Optional benchmark context. |
| Rankings | Top Company Movers — `/v2/companies/top-changes/` | 1/classification × period | Optional discovery seed; default 10 credits. |
| Rankings | Most Traded Stocks — `/v2/most-traded/` | 2 | Optional liquidity-attention context; date range max 90 days. |
| IPO & Performance | Listing Performance — `/v2/listing-performance/{symbol}/` | 1 | Optional IPO-age performance context. |
| News & Filings | Corporate Actions Calendar — `/v2/corporate-actions/` | 1/type; default 7 | Use only a selected type/window. |
| News & Filings | Filings / News / Suspensions — `/v2/filings/`, `/v2/news/`, `/v2/suspensions/` | 1 each | Optional corroborative evidence; paginated/filterable. |
| Brokers | Activity by broker / top activity — `/v2/broker-activity/{broker_code}/`, `/v2/broker-activity/{broker_code}/top/` | 1 / 2 | Stretch research context. |
| Brokers | Symbol broker summary / top buyers-sellers — `/v2/broker-summary/{symbol}/`, `/v2/broker-summary/{symbol}/top/` | 1 / 2 | Stretch single-company context. |
| Brokers | Registry / daily broker ranking — `/v2/brokers/`, `/v2/brokers/top/` | 1 / 2 | Reference/optional context. |
| Brokers | Universe/per-symbol foreign flow — `/v2/foreign-flow/`, `/v2/foreign-flow/{symbol}/` | 1/page / 1 | Per-symbol is viable; universe feed is 20–25 pages. |

### Screener decision

**Yes—use the deterministic Companies Screener as the Discovery backbone.** The official Query Builder supports SQL-like conditions across multiple annual columns and years, arithmetic expressions, ordering, and `include_query_values=true`. Its own Banks example combines `sub_sector="banks"`, multi-year revenue arithmetic, dividend filters, ordering, and a limit in one request. A single structured screen can therefore retrieve a bounded company universe and calculation inputs; local Pandas logic should rank that response before any per-company detailed calls. Do not use the natural-language `q` path in the agent's normal path: it costs 3 credits and delegates query formation to a model.

### Representative requests to run after access exists

```text
GET /v2/companies/?where=sub_sector%20%3D%20'Banks'&order_by=-market_cap&limit=20
GET /v2/company/report/BBRI/?sections=overview,financials,peers,valuation
GET /v2/company/get_quarterly_financial_dates/BBRI/
GET /v2/financials/quarterly/BBRI/?n_quarters=4
GET /v2/daily/BBRI/?start=<90-days-ago>&end=<today>
```

Run that small sequence for **BBRI** first, then only compare BBCA/BMRI/BBNI if response schemas and credits behave as documented. Record status, record count, periods, response keys, and observed balance change without storing credentials.

## Confirmed limitations and design consequences

1. Daily price history is capped at 90 days per call. NUSA cannot claim long-horizon price anomaly history from this endpoint alone.
2. Quarterly field availability varies by sector. The metric registry must be sector-aware; bank-only measures must never be compared with non-financial firms.
3. Full-universe feeds are paginated in ~30-row pages, making broad scans expensive.
4. A company report's annual history and valuation series are useful, but exact coverage must be established from real responses; do not promise a fixed number of years.
5. Peer data is same-subsector, which is appropriate for the MVP but should be labelled as an API-provided peer universe rather than a bespoke economic-peer model.
6. Numeric rate limits and all endpoints not expanded above remain undocumented/untested in this workspace; they are not assumed.

## Sources

- [Sectors API documentation](https://docs.sectors.app/)
- [v2 documentation index](https://docs.sectors.app/llms.txt)
- [Sectors MCP guide](https://docs.sectors.app/recipes/sectors-for-ai-agents/00-sectors-mcp-guide)
- [Hackathon rules](https://hackathon.sectors.app/rules)
- [Track 01 requirements](https://hackathon.sectors.app/tracks/ai-agents-assistants)
