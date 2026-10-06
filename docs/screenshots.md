# Manual Screenshot Plan

Use the local Streamlit app with **SECTORS CACHED SNAPSHOT** selected for the
real-data judging journey. Keep **SECTORS CACHED SNAPSHOT — Sectors-origin data
— Not a live refresh** visible on every financial-results capture. The snapshot
is local and ignored by Git; never add it to screenshots, attachments, or the
public repository. Hide `.env`, API keys, Authorization headers, cookies,
account details, terminal output, and personal information.

| # | Capture | What must be visible | Hide / avoid | Suggested caption |
| --- | --- | --- | --- | --- |
| 1 | Landing / source status | NUSA title, three sections, source selector, **SECTORS CACHED SNAPSHOT**, original retrieval time, “Not a live refresh” | `.env`, credentials, browser profile, unrelated window chrome | “NUSA uses an explicitly labeled Sectors-origin cached snapshot for this reproducible demonstration.” |
| 2 | Discovery results | 48-bank universe, top-ranked SUPA.JK, net-interest-income driver, +159.75% change, peer median near +1.69%, score and excluded-metric flags | Any wording that implies a live refresh, BUY/SELL advice, or a fraud conclusion | “Discovery ranks SUPA.JK highest for research priority in the 48-bank cached snapshot.” |
| 3 | Research plan / workflow | SUPA.JK investigation stages, validated plan, registered tool names and execution progress | Hidden reasoning, secrets, oversized irrelevant JSON | “A structured plan routes the SUPA investigation through registered deterministic tools.” |
| 4 | Evidence Ledger | Ticker, metric, 2024/2025 values, unit, peer baseline/count, eligibility/reason, source and retrieval time | Unreadable full-screen dumps; crop must not remove cached-data status | “The ledger preserves source, period, calculation, peer context, and scoring eligibility.” |
| 5 | Research report | Executive summary, key finding, evidence references, why flagged, limitations | Cropping that removes the source label or disclaimer | “The deterministic report explains a peer-relative change using validated evidence.” |
| 6 | Memory-driven peer comparison | Prompt **Compare this change with BBSI.JK and BBHI.JK**, resolved metric **net_interest_income**, values +159.75% / +91.97% / +28.93% | Any indication that compared values come from a live refresh | “Session memory resolves ‘this change’ to net interest income for SUPA and two peers.” |
| 7 | Methodology / architecture | Explicit source modes, deterministic formulas, evidence grounding, no-ML note, disclaimer | Unrelated project files or hidden configuration | “NUSA separates source retrieval, deterministic analysis, evidence validation, and synthesis.” |
| 8 | Source-mode choices (optional) | LIVE SECTORS, SECTORS CACHED SNAPSHOT, and DEMO/SAMPLE as distinct options | Selecting a mode in a way that mislabels its financial values | “Three explicit source modes; no silent transition between cached, live, and synthetic data.” |

Capture screenshots manually after launching `streamlit run app.py`. Before
recording, verify the status reports 48 banks and SUPA.JK at the top. Do not
alter real values, fixture values, company names, or source labels. If the local
Sectors snapshot is unavailable, use DEMO/SAMPLE only with its full synthetic
warning visible; never describe that fixture as Sectors data. Add only verified
images and captions to the repository.
