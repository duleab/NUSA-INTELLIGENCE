# NUSA data-feasibility matrix

**Classification:** GREEN = directly supported; YELLOW = achievable with deterministic derivation and validation; RED = insufficiently supported for the MVP.

| Capability | Required Data | Endpoint | Available | Historical Depth | Derived Calculation | Estimated Credits | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Company resolution | ticker/name/classification | `/v2/companies/` | GREEN | Current directory; annual fields queryable | Canonical symbol selection | 1 structured query | Validate user ticker/name then retain canonical symbol. |
| Banking-universe discovery | bank universe and current/annual metrics | Structured Companies Screener + `/v2/subsectors/` | GREEN | Annual/forecast fields documented; `banks` taxonomy live-validated | Query Builder + local dataframe | 1 + cached taxonomy | Start with `sub_sector = 'banks'`; bulk fetch then rank locally. |
| Latest-report freshness | latest quarterly report dates | `/v2/companies/quarterly-financial-dates/` | GREEN | Latest date only | Incremental freshness filtering | 1/page; ~32 full IDX | Optional cached refresh, not per-chat. |
| Revenue / earnings trend | quarterly or annual fundamentals | `/v2/financials/quarterly/{symbol}/`, report `financials` | GREEN | Company-specific | YoY/QoQ and acceleration | 1/quarter; report section 1 | Four-quarter company investigation; annual trend supplemental. |
| Profitability trend | earnings/revenue, ROA/ROE/margins | Quarterly records + report financial ratios | GREEN | Annual ratios; quarterly raw inputs | Margin, ROA/ROE/NIM change | 1 report section + quarters | Sector-aware bank metric registry. |
| Leverage trend | assets/equity/debt; bank loans/deposits | Quarterly financials + report financials | GREEN | Company-specific | Ratio/trend changes | 1/quarter | Use financial-sector fields only for banks. |
| Cash-flow trend | operating/free cash flow | Quarterly financials + annual report financials | GREEN | Company-specific | Cash-flow margin/change | 1/quarter | Flag only non-null fields. |
| Historical deviation | sequential quarterly values | Quarterly financials + quarterly-date helper | YELLOW | Unknown until test; per-quarter billed | Robust z-score / YoY / QoQ | 5–9/company | Require sufficient history or abstain. |
| Peer deviation | peer identity and comparable metrics | report `peers`, subsector report, Screener | GREEN | Latest plus annual report series | Percentile / robust peer z-score | 1–3 sections | Show peer sample size and exclusions. |
| Valuation / historical valuation | PE/PB/PS/PCF + peer/historical references | report `valuation`, `peers`, subsector `valuation` | GREEN | Historical valuation by year | Percentile vs peer/history | 1–2 sections | Apply only meaningful bank ratios. |
| Stock performance | daily OHLC, volume, market cap | `/v2/daily/{symbol}/` | GREEN | Rolling 90 days max | Returns, volume z-score, drawdown | 1/company | Label short-window limitation. |
| Price/fundamental divergence | price series + latest fundamentals | daily + quarterly/report | YELLOW | Price 90d; fundamentals vary | Directional divergence score | 2–6/company | Never make causal claim. |
| Discovery scanning | bounded company universe | Structured Screener | GREEN | Annual/forecast fields documented | Local Pandas anomaly ranking | 1 + cache | Preferred bulk-first architecture. |
| Market-wide price scan | all-company close data | `/v2/close/` | YELLOW | One day per pull | Cross-sectional price filter | ~32/day | Exclude base MVP. |
| Movers-led discovery | ranked price change | `/v2/companies/top-changes/` | GREEN | 1d–365d windows | Optional seed/ranking merge | 1/combo | Request one combo only. |
| Evidence generation | timestamped source values | All selected calls | GREEN | Source-specific | Evidence ledger records | No extra call | Required before LLM synthesis. |
| News/filing validation | dated events or filings | news, filings, actions, suspensions | YELLOW | Endpoint-specific | Contextual link matching | 1/call | Stretch; not in base score. |
| Broker/foreign-flow signal | per-symbol or universe flow | foreign-flow endpoints | YELLOW | Per-symbol max 90d | Flow anomaly | 1/company; 20–25 pages universe | Optional single-company evidence. |
| Fraud/manipulation detection | labels and causal evidence | Not established | RED | N/A | N/A | N/A | Explicitly out of scope. |
| Long-horizon technical anomaly | >90-day daily price history | Not established | RED | Daily cap 90d | N/A | N/A | Do not claim 1-year technical history. |
| Whole-IDX quarterly scan | recent fundamentals for ~950 firms | Technically callable but per-quarter priced | RED for MVP | Company-specific | N/A | Thousands | Constrain discovery universe. |

## Product-feasibility decision

1. **Discovery Mode:** Yes, for a selected subsector or bounded universe; no, not as an always-current full-IDX fundamental scan.
2. **Historical anomaly detection:** Yes, conditionally. Use a company only when the returned quarters meet a documented minimum history threshold.
3. **Peer comparison:** Yes. Same-subsector peers are directly exposed; add deterministic filtering and transparent peer sample sizes.
4. **Valuation analysis:** Yes, using company-report valuation and peer/subsector references; measure availability per company.
5. **Market/price anomaly:** Yes, as a 90-day short-window signal; not as long-horizon technical analysis.
6. **Must derive ourselves:** YoY/QoQ changes, robust deviations/percentiles, score components, metric eligibility, evidence ledger, report narrative, plan/router/memory.
7. **Remove from base scope:** full-market historical-fundamental scan, long-period price claims, generic ML/Isolation Forest, any fraud/manipulation framing, automated orders.
8. **Add:** report-date freshness, sector-aware bank metrics, data-availability abstention, and an evidence provenance panel.
9. **Smallest strong MVP:** `Banks Discovery → one flagged company → four-quarter investigation → bank-peer comparison → evidence-grounded report → contextual follow-up`.
10. **Track:** Track 01 remains appropriate if orchestration is first-class and visible; otherwise the product would fit Track 03.
