# Proposed final MVP specification

## Product

**NUSA Intelligence** is an Indonesian equities research agent that finds unusual, evidence-backed changes in a bounded peer universe and autonomously investigates a selected company. It is research information, not investment advice.

## The demoable core workflow

1. The analyst selects **Banks** and runs Discovery.
2. NUSA loads/caches the bounded universe, calculates transparent latest-quarter and short-window market signals, then ranks candidates with score components.
3. The analyst clicks **Investigate** for one candidate.
4. The agent visibly creates a structured plan, retrieves only required Sectors sections/quarters, runs deterministic analytics, validates evidence, and returns a report.
5. The analyst asks a contextual follow-up such as “Compare the profitability change with BBCA and BMRI.” Structured memory resolves `profitability change`, the active company, period, and peers.

## Agent contract

The LLM may classify the user request and produce a schema-validated plan from an allowlist. Python controls execution, credits, calculations, citations, and memory.

Allowed tools:

- `resolve_company_or_universe`
- `get_company_sections`
- `get_quarterly_dates`
- `get_quarterly_financials`
- `get_daily_market_data`
- `get_subsector_report`
- `calculate_fundamental_signals`
- `calculate_market_signals`
- `compare_peer_metrics`
- `validate_evidence`
- `update_research_memory`

## Anomaly methodology

The base score is a 0--100 research-priority indicator, not a prediction or risk rating. Score only components with sufficient non-null data; redistribute weights over eligible components and state omissions.

| Component | Indicative weight | Deterministic method |
| --- | ---: | --- |
| Fundamental change | 40 | Absolute robust standardized YoY/QoQ change in earnings/revenue; for banks, NII/ROA/ROE/loan/deposit measures where returned. |
| Peer deviation | 30 | Absolute percentile distance or robust z-score within the same-subsector peer set; show peer count. |
| Trend acceleration | 15 | Difference between current and prior growth/change; require enough sequential quarters. |
| Market confirmation | 15 | 20/60-day return, volume z-score, or drawdown using the 90-day series. |

Use median/MAD scaling when peer/history sample sizes permit, otherwise percentile distance. Require a documented minimum (recommended: four valid quarters for YoY and at least three comparable peers); otherwise show **Insufficient data**, not a numeric flag. Keep valuation outside the first score or render it as a separately labelled evidence component until data coverage is tested.

## Report sections

Company; research question; executive summary; detected changes; historical context; peer comparison; quantitative evidence; why NUSA flagged it; limitations; sources; non-advice disclaimer.

## Explicit exclusions

- Full-IDX quarterly fundamental scanning.
- Long-horizon price claims beyond the documented 90-day window.
- Fraud, manipulation, or causality assertions.
- Automated order execution, buy/sell recommendations, and personalized investment advice.
- An LLM that invents numbers, endpoint fields, or citations.

## Recommended architecture (approval checkpoint)

```text
Streamlit UI
  -> Request interpreter / structured planner (LLM)
  -> Orchestrator: allowlist, credit budget, execution events
      -> Sectors REST client + disk/TTL cache
      -> deterministic analytics + metric registry
      -> evidence ledger + validator
  -> Synthesizer (LLM receives only validated evidence)
  -> Structured session memory
```

Suggested repository layout after approval:

```text
nusa-intelligence/
  app.py
  agent/{schemas,planner,orchestrator,memory,synthesizer}.py
  sectors/{client,cache,models}.py
  analytics/{registry,signals,peers,scoring}.py
  evidence/{ledger,validator}.py
  ui/{discovery,investigation,components}.py
  tests/{test_client,test_analytics,test_orchestrator}.py
  docs/
```

This makes the custom orchestration inspectable and ensures Sectors remains indispensable.
