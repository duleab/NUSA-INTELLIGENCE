# NUSA Intelligence — Submission Copy

## A. One-sentence problem statement

Analysts have access to large amounts of financial data, but finding which Indonesian listed companies deserve investigation and why requires repetitive screening, historical analysis, and peer comparison.

## B. One-sentence solution statement

NUSA Intelligence combines a Sectors data-provider integration, deterministic quantitative analytics, and custom AI-agent orchestration to discover unusual financial changes and investigate them with validated evidence.

## C. Short project description (~100 words)

NUSA Intelligence is an autonomous AI research agent for unusual financial changes in Indonesian listed banks. The Sectors Companies Screener works in the authenticated client and returned 48 IDX Banks with annual 2024/2025 earnings, net interest income, total assets, total equity, and ROA. The judging workflow uses a local Sectors-origin cached snapshot for reproducibility; its badge says it is not a live refresh. Deterministic Python calculates and ranks eligible changes, and an Evidence Ledger validates their source and peer context before the report. Optional LLM synthesis explains validated evidence, while a deterministic template works without model credentials. A separate DEMO/SAMPLE fixture remains available and is explicitly synthetic.

## D. Full project description (~250 words)

NUSA Intelligence is an autonomous AI research agent that helps analysts identify unusual financial changes among Indonesian listed companies. Its current MVP focuses on Indonesian-listed banks, using peer context and period-to-period changes to help prioritize further research.

Bounded Discovery ranks annual metric changes when the selected source has enough comparable historical and peer data. A structured plan runs through an explicit allowlist of tools. Deterministic Python normalizes data and calculates trends, anomaly scores, and peer comparisons. The Evidence Ledger records tickers, values, periods, sources, calculations, and peer baselines; an Evidence Validator checks records before synthesis. Optional LLM synthesis explains evidence but cannot calculate or originate financial numbers, and cannot run model-generated code. Structured session memory resolves follow-ups such as “this change.” Without a configured model provider, NUSA returns a deterministic evidence-based template.

The `BankDataProvider` separates three explicit source modes: direct **LIVE SECTORS DATA**, **SECTORS CACHED SNAPSHOT**, and fictional **DEMO/SAMPLE**. Direct authenticated `GET /v2/companies/` is working and returned 48 Banks with 2024/2025 annual fields. For a stable judging run, NUSA reads a Sectors-origin cached snapshot and shows its original retrieval time plus “Not a live refresh.” The raw snapshot is ignored by Git and intentionally excluded from the public repository; clones do not include the real financial dataset. Authorized users can populate a local copy using the documented response importer in [`sectors_snapshot_ingestion.md`](sectors_snapshot_ingestion.md). Earlier 403 attempts are historical and do not describe current integration status.

The plan, tool trace, calculations, evidence references, peer context, and limitations are inspectable. NUSA is a research tool—not a trading system, fraud detector, or source of personalized investment advice.

## E. Track

**Track 01 — AI Agents & Assistants**

## F. Why it qualifies for Track 01

NUSA is not simply an LLM connected to Sectors. The implemented custom agent includes intent resolution, structured research planning, plan validation, a registered tool registry/router, deterministic tool execution, anomaly scoring, an Evidence Ledger, evidence validation, optional LLM synthesis, and structured session-level research memory. The model is restricted to bounded interpretation and explanation. It does not calculate financial metrics, invent missing values, or execute generated code. Operational events are visible without exposing hidden chain-of-thought.

## G. Sectors usage explanation

The authenticated Sectors client successfully retrieves the Companies Screener. A Banks query returned 48 IDX companies and annual 2024/2025 values for earnings, net interest income, total assets, total equity, and ROA. The judging demo reads a validated Sectors-origin snapshot locally for stability; the snapshot is not a live refresh and is deliberately excluded from the public repository. The client also supports explicit live retrieval when a user configures authorized credentials. Any live failure is surfaced, never replaced silently with DEMO/SAMPLE. See [`sectors_api_analysis.md`](sectors_api_analysis.md) and [`sectors_snapshot_ingestion.md`](sectors_snapshot_ingestion.md) for integration and local import details.

## H. Technical innovation summary

NUSA combines a bounded bank-data provider interface with custom agent orchestration and deterministic, explainable financial analysis. It routes requests only through registered tools, keeps calculations outside the LLM, validates metric evidence before synthesis, and retains compact structured memory for contextual comparisons. The real-data judging journey is repeatable because it uses a labeled Sectors cached snapshot; no black-box ML anomaly model is used.

## Data and methodology

For earnings, net interest income, total assets, and total equity, the ordinary
change is `(current - previous) / abs(previous) × 100`. ROA is stored as a
decimal fraction and changes in percentage points: `(current - previous) × 100`.
Sign transitions, zero prior values, and sufficiently small prior values
(below 1% of the median absolute prior-year value) are excluded from percentage
scoring and explicitly flagged; absolute monetary changes remain in evidence.
Eligible metrics use leave-one-out peer medians and percentile deviation
contributions. The 0–100 score is a research-priority ranking, not investment
advice, a BUY/SELL signal, or a misconduct/fraud assessment.

## I. Current limitations

- The judging snapshot is cached rather than live. It is not included in public repository clones; obtain authorized Sectors data locally to reproduce the real-data journey.
- The five-company DEMOBANK fixture is fictional and synthetic. Its values are not current market data or Sectors observations.
- Available metrics and periods depend on provider coverage; the app abstains when required comparisons are unsupported.
- Without an optional compatible LLM provider, report synthesis uses a deterministic template.
- Research memory is limited to the active session.

## J. Research disclaimer

Anomaly scores indicate research priority only. They are not BUY/SELL signals, do not imply fraud or misconduct, and do not establish causality. NUSA is a research/information tool, not personalized financial advice. Verify source, period, coverage, and context independently.
