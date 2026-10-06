# NUSA Intelligence — Judging Video Script

Maximum duration: 3:00. Target exactly the timed sections below. Keep the
source label **SECTORS CACHED SNAPSHOT — Sectors-origin data — Not a live
refresh** visibly in frame whenever real financial results are shown. The
snapshot was retrieved from Sectors; this recording is not a live refresh.

| Time | Screen direction | Narration |
| --- | --- | --- |
| **0:00–0:20 — Problem** | Open on NUSA and Discover. Keep the cached-source badge and not-live-refresh notice visible. | “Analysts have access to large volumes of financial data, but finding which changes deserve attention takes repeated screening, historical analysis, and peer comparison. Research also needs to show where its numbers came from.” |
| **0:20–0:40 — NUSA solution** | Show the three sections and the Discover → Plan → Retrieve → Analyze → Compare → Verify → Explain workflow. | “NUSA Intelligence is an autonomous AI research agent for unusual changes among Indonesian listed banks. It combines the Sectors Financial API, deterministic analysis, custom tool orchestration, and an evidence ledger. The data shown here is a Sectors-origin cached snapshot—not a live refresh.” |
| **0:40–1:10 — Discovery** | Click **Analyze Banks**. Show the 48-bank universe and ranked table. Highlight SUPA.JK, score, NII driver, change, and peer median. | “Sectors returned a universe of 48 IDX Banks with annual 2024 and 2025 values. SUPA.JK is the highest research priority in this snapshot. Its net interest income changed by 159.75%, compared with an eligible-peer median of approximately 1.69%. This ranking prioritizes research; it is not an investment recommendation or a misconduct finding.” |
| **1:10–2:10 — Autonomous investigation** | Select SUPA.JK and run investigation. Show progress, expand the research plan, show registered tools, quantitative evidence, Evidence Ledger, validation result, and report. Keep source badge visible. | “Now I’ll investigate SUPA. NUSA resolves the request and validates a structured research plan. The router calls only registered tools. Deterministic Python calculates the annual changes and peer baselines. The Evidence Ledger records the values, periods, source, calculations, peer context, and eligibility flags. Evidence validation runs before the report is generated. The optional language model explains validated evidence; it is not asked to calculate or invent financial numbers. This report uses the deterministic template.” |
| **2:10–2:35 — Peer comparison / memory** | Enter **Compare this change with BBSI.JK and BBHI.JK**; run follow-up. Show the resolved metric and three comparison rows. | “I’ll ask, ‘Compare this change with BBSI.JK and BBHI.JK.’ Structured session memory resolves ‘this change’ to net interest income. The snapshot shows SUPA at plus 159.75%, BBSI at plus 91.97%, and BBHI at plus 28.93%. All three values are from the same Sectors-origin cached snapshot, not a live refresh.” |
| **2:35–2:50 — Architecture / Sectors** | Show the architecture diagram or Methodology section, then the cached-source status. | “NUSA separates provider selection, planning, tool execution, deterministic analytics, evidence validation, synthesis, and memory. The raw cached financial snapshot stays local and is intentionally excluded from the public repository.” |
| **2:50–3:00 — Close** | Return to NUSA title and keep the source label visible. | “NUSA turns unusual financial changes into evidence-grounded research priorities—discover what changed, verify the evidence, and investigate what matters.” |

## Recording checks

- Use **SECTORS CACHED SNAPSHOT** mode and keep **Sectors-origin data — Not a
  live refresh** visible beside financial results.
- Verify the displayed universe count is 48 and the top row is SUPA.JK before
  recording; do not edit or stage the snapshot into Git.
- Use the follow-up prompt exactly as written so memory resolves the NII metric.
- Keep `.env`, API keys, credentials, account details, and hidden reasoning out
  of frame.
- Describe the score as research priority only. Do not imply fraud detection,
  causality, a BUY/SELL recommendation, or personalized advice.
- If the snapshot is unavailable in the recording environment, stop and obtain
  an authorized local Sectors snapshot or explicitly switch to DEMO/SAMPLE and
  disclose that it is synthetic; never conflate the two.
