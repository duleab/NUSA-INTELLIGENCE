# NUSA Intelligence — Judging Video Script

Maximum duration: 3:00. Target about 2:55 to leave a safe edit margin. Keep the
source badge and full **DEMO/SAMPLE DATA — Synthetic demonstration values. Not
current market data.** warning visible whenever sample financial results are
shown. All DEMOBANK tickers and numeric values are fictional.

| Time | Screen direction | Narration |
| --- | --- | --- |
| **0:00–0:20 — Problem** | Open on NUSA title; show Discover with source warning visible. | “Financial analysts have access to large amounts of company data, but finding which changes deserve a closer look takes repetitive screening, historical analysis, and peer comparison. An AI summary is not enough: the reasoning should be traceable to evidence.” |
| **0:20–0:35 — Solution** | Show three app sections, then display the Core Workflow line. | “NUSA Intelligence is an autonomous AI research agent for unusual financial changes in Indonesian listed companies. Its current MVP focuses on banks. The workflow is Discover, Plan, Retrieve, Analyze, Compare, Verify, Explain—and remember useful session context.” |
| **0:35–1:00 — Discovery** | Keep DEMO warning in frame. Click **Example: Find unusual financial changes among Indonesian banks**. Show all five results, then DEMOBANK5 at the top and its score/driver. | “This is the explicitly labeled DEMO/SAMPLE fixture: five fictional DEMOBANK companies with synthetic annual metrics. DEMOBANK5 ranks first in this configured sample because its asset change is most unusual relative to the other sample rows. This is a demonstration of the method, not a real market finding or current Sectors data.” |
| **1:00–1:50 — Autonomous investigation** | Click **Investigate highest-ranked demo bank**, open INVESTIGATE, click **Run investigation**. Show progress; open Research plan and Evidence Ledger. | “Now I’ll investigate DEMOBANK5. NUSA resolves the request, creates and validates a structured plan, then calls only registered tools. Deterministic Python calculates the year-over-year metrics and peer baselines. The Evidence Ledger records periods, values, calculations, source, and IDs. Validation checks that evidence before synthesis. The optional language model receives validated evidence; it is not asked to invent or calculate financial numbers. With no model configured, NUSA uses its deterministic report template.” |
| **1:50–2:20 — Report** | Show report summary, quantitative evidence, why-flagged section, references and limitations. | “The report explains the sample flag using the validated evidence: the primary driver, change period, peer comparison, and evidence references. Its limitations remain visible. A research-priority score is not a buy or sell recommendation, proof of misconduct, or a causal explanation.” |
| **2:20–2:40 — Memory / peer comparison** | Click the comparison example, then **Run follow-up peer comparison**. Show resolved tickers, reused metric, and table. | “I’ll ask, ‘Compare this change with DEMOBANK2 and DEMOBANK3.’ Session memory resolves ‘this change’ to DEMOBANK5’s investigated assets metric. The registered comparison tool returns same-period evidence for the three fictional banks. These remain synthetic fixture values.” |
| **2:40–2:55 — Architecture / Sectors** | Show README Mermaid diagram or repository architecture. | “The app keeps source selection, planning, tool routing, analytics, evidence validation, synthesis, and session memory as separate parts. Authenticated Sectors taxonomy access was confirmed, and the official Playground was reported to return Banks rows. Direct application access to the Companies Screener still returns HTTP 403, so this recording uses the disclosed fixture rather than claiming a live result.” |
| **2:55–3:00 — Close** | NUSA logo/title and closing line. | “NUSA Intelligence turns financial screening into autonomous, evidence-grounded research.” |

## Recording checks

- Use DEMO/SAMPLE mode; do not switch to LIVE for the judging recording.
- Keep the synthetic-data warning visible on Discovery, investigation, report,
  and comparison shots.
- Show only fictional DEMOBANK tickers in the synthetic journey.
- Do not expose `.env`, API keys, credentials, or hidden reasoning.
- Do not claim a live Sectors Screener response, current market data, fraud
  detection, investment recommendations, or personalized advice.
