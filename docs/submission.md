# NUSA Intelligence — Submission Copy

## A. One-sentence problem statement

Analysts have access to large amounts of financial data, but finding which Indonesian listed companies deserve investigation and why requires repetitive screening, historical analysis, and peer comparison.

## B. One-sentence solution statement

NUSA Intelligence combines a Sectors data-provider integration, deterministic quantitative analytics, and custom AI-agent orchestration to discover unusual financial changes and investigate them with validated evidence.

## C. Short project description (~100 words)

NUSA Intelligence is an autonomous AI research agent for unusual financial changes in Indonesian listed companies, with an MVP focused on banks. It ranks eligible annual changes in a bounded universe, investigates a selected company through a structured plan and registered tools, and compares validated metrics with available peers. Deterministic Python calculates the financial values; an Evidence Ledger preserves periods, sources, calculations, and peer context before report generation. Optional LLM synthesis explains validated evidence, while a deterministic template keeps the application useful without an LLM credential. The demo uses five fictional DEMOBANK symbols and synthetic values, clearly labeled as not current market data. Live Sectors Screener access remains unresolved.

## D. Full project description (~250 words)

NUSA Intelligence is an autonomous AI research agent that helps analysts identify unusual financial changes among Indonesian listed companies. Its current MVP focuses on Indonesian-listed banks, using peer context and period-to-period changes to help prioritize further research.

Bounded Discovery ranks annual metric changes when the selected source has enough comparable historical and peer data. A structured plan runs through an explicit allowlist of tools. Deterministic Python normalizes data and calculates trends, anomaly scores, and peer comparisons. The Evidence Ledger records tickers, values, periods, sources, calculations, and peer baselines; an Evidence Validator checks records before synthesis. Optional LLM synthesis explains evidence but cannot calculate or originate financial numbers, and cannot run model-generated code. Structured session memory resolves follow-ups such as “this change.” Without a configured model provider, NUSA returns a deterministic evidence-based template.

The `BankDataProvider` separates authenticated Sectors access from explicitly selected fixture data. Access to `/v2/subsectors/` was confirmed, and the official Companies Screener Playground was reported to return IDX Banks. Direct app access to `GET /v2/companies/` returns HTTP 403; its cause is unresolved, so the judging journey uses the bundled fixture. Its five DEMOBANK symbols and values are synthetic, not current market data or Sectors observations.

The plan, tool trace, calculations, evidence references, peer context, and limitations are inspectable. NUSA is a research tool—not a trading system, fraud detector, or source of personalized investment advice.

## E. Track

**Track 01 — AI Agents & Assistants**

## F. Why it qualifies for Track 01

NUSA is not simply an LLM connected to Sectors. The implemented custom agent includes intent resolution, structured research planning, plan validation, a registered tool registry/router, deterministic tool execution, anomaly scoring, an Evidence Ledger, evidence validation, optional LLM synthesis, and structured session-level research memory. The model is restricted to bounded interpretation and explanation. It does not calculate financial metrics, invent missing values, or execute generated code. Operational events are visible without exposing hidden chain-of-thought.

## G. Sectors usage explanation

The live provider uses the existing authenticated Sectors client and remains available as an explicit LIVE mode. Authenticated `/v2/subsectors/` access was confirmed. A successful Banks Companies Screener Playground result was reported separately; it is not an application result. Direct Python `GET /v2/companies/` returned HTTP 403 in the controlled attempts, and the cause has not been established. Live API failures are surfaced without silently switching to fixture data. The submission demo therefore uses the explicitly labeled synthetic fixture. See [`sectors_api_analysis.md`](sectors_api_analysis.md) for details.

## H. Technical innovation summary

NUSA combines a bounded bank-data provider interface with custom agent orchestration and deterministic, explainable financial analysis. It routes requests only through registered tools, keeps calculations outside the LLM, validates metric evidence before synthesis, and retains compact structured memory for contextual comparisons. When the Screener is unavailable, the demo fixture enables repeatable judging without representing synthetic data as live data.

## I. Current limitations

- Direct application `GET /v2/companies/` currently returns HTTP 403; live discovery and the end-to-end live workflow are not verified.
- The five-company DEMOBANK fixture is fictional and synthetic. Its values are not current market data or Sectors observations.
- Available metrics and periods depend on provider coverage; the app abstains when required comparisons are unsupported.
- Without an optional compatible LLM provider, report synthesis uses a deterministic template.
- Research memory is limited to the active session.

## J. Research disclaimer

Anomaly scores indicate research priority only. They are not BUY/SELL signals, do not imply fraud or misconduct, and do not establish causality. NUSA is a research/information tool, not personalized financial advice. Verify source, period, coverage, and context independently.
