# Manual Screenshot Plan

Use the local Streamlit application in **DEMO/SAMPLE** mode for all research
screenshots. The visible warning must read **DEMO/SAMPLE DATA — Synthetic
demonstration values. Not current market data.** Do not include `.env`, API
keys, credentials, terminal output containing secrets, browser account details,
or personal information.

| # | Capture | What must be visible | Hide / avoid | Recommended crop | Suggested README caption |
| --- | --- | --- | --- | --- | --- |
| 1 | NUSA landing page | NUSA title, Indonesian listed banks subtitle, source selector, DEMO/SAMPLE badge and full warning, three sections | Browser profile, credentials, unrelated desktop/window chrome | App content from title through source warning and tabs | “NUSA Intelligence — research workflow using explicitly labeled synthetic demo data.” |
| 2 | Discovery results | Discovery table, all five fictional bank rows, primary driver and score, source warning | Any implication that these are current market results | Include table and warning in the same frame; keep labels legible | “Bounded sample Discovery ranks synthetic changes for research follow-up.” |
| 3 | Highest-ranked DEMOBANK5 | DEMOBANK5 row/company, score, primary driver, **Investigate highest-ranked demo bank** action | Any real company ticker or real-world company label | Crop around top result and action while retaining the DEMO warning | “DEMOBANK5 is the highest-priority fictional sample in this fixture.” |
| 4 | Research plan / operational trace | Workflow stages and expanded Research plan with intent, ticker, task/tool names | Hidden reasoning, secrets, oversized JSON irrelevant to judging | Show progress and plan side by side if the window allows; otherwise separate captures | “A validated structured plan routes only through registered tools.” |
| 5 | Evidence Ledger | Evidence IDs, ticker, metric, current/previous values, period, peer baseline/count, source, calculation or data mode where visible | Full-screen dumps with unreadable text; never crop away source/data-mode labels | Open Evidence Ledger expander and crop to useful columns plus warning | “Validated synthetic fixture evidence includes provenance and peer context.” |
| 6 | Investigation report | Executive summary, why flagged/key finding, evidence references and limitations | Any wording cropped so it implies a live finding | Report text with DEMO warning or source badge visible nearby | “The deterministic report explains a fictional sample anomaly and its limits.” |
| 7 | Peer comparison | Resolved tickers DEMOBANK5/2/3, reused metric, comparison rows, periods, changes and evidence IDs | Real tickers; any interpretation as current Indonesian bank performance | Show resolved-memory caption and comparison table together | “Session memory resolves ‘this change’ to assets and compares three fictional banks.” |
| 8 | Methodology / architecture | Methodology text, disclaimer, Mermaid architecture rendered from README or docs if captured separately | Unrelated project files or secret/config content | Capture the complete diagram or a readable section; avoid truncating endpoints/components | “NUSA separates the provider, deterministic analytics, evidence validation and optional synthesis.” |

Capture screenshots manually after a fresh launch with `streamlit run app.py`.
Do not alter fixture values, company names, source labels, or screenshots to
make the sample appear live. Add only verified images and captions to the
repository.
