"""NUSA Intelligence — compact Streamlit research workspace."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from nusa.agent.orchestration import ResearchOrchestrator
from nusa.agent.session_memory import ResearchSessionMemory
from nusa.agent.synthesis import LLMResearchSynthesizer, create_llm_provider_from_env
from nusa.discovery.workflow import discover_banks
from nusa.providers import BankDataProvider, create_bank_data_provider
from nusa.providers.sectors_snapshot import DEFAULT_SECTORS_SNAPSHOT_PATH
from nusa.ui.source_modes import (
    format_excluded_metric_flags,
    format_source_status,
    source_mode_options,
)


load_dotenv()
st.set_page_config(page_title="NUSA Intelligence", page_icon="N", layout="wide")

_NAVY = "#102a43"
_TEAL = "#0f766e"
_MUTED = "#627d98"
_BORDER = "#d9e2ec"

st.markdown(
    f"""
    <style>
      .stApp {{ background: #f5f8fb; color: {_NAVY}; }}
      [data-testid="stHeader"] {{ background: rgba(245,248,251,.94); }}
      .block-container {{ max-width: 1420px; padding-top: 2rem; padding-bottom: 3rem; }}
      h1, h2, h3 {{ color: {_NAVY}; letter-spacing: -.025em; }}
      .nusa-kicker {{ color: {_TEAL}; font-size: .76rem; font-weight: 750;
        letter-spacing: .14em; text-transform: uppercase; margin-bottom: .35rem; }}
      .nusa-subtitle {{ color: {_MUTED}; font-size: 1.1rem; margin-top: -.5rem; }}
      .nusa-card {{ background: white; border: 1px solid {_BORDER}; border-radius: 14px;
        padding: 1rem 1.15rem; min-height: 84px; }}
      .nusa-label {{ color: {_MUTED}; font-size: .8rem; font-weight: 650; }}
      .nusa-value {{ color: {_NAVY}; font-size: 1.15rem; font-weight: 750; margin-top: .25rem; }}
      .nusa-badge-live {{ color: #086b4b; background: #dcfce7; border-radius: 999px;
        display: inline-block; padding: .36rem .7rem; font-size: .77rem; font-weight: 750; }}
      .nusa-badge-demo {{ color: #854d0e; background: #fef3c7; border-radius: 999px;
        display: inline-block; padding: .36rem .7rem; font-size: .77rem; font-weight: 800; }}
      .nusa-badge-cached {{ color: #1e3a8a; background: #dbeafe; border-radius: 999px;
        display: inline-block; padding: .36rem .7rem; font-size: .77rem; font-weight: 800; }}
      div[data-testid="stTabs"] button {{ font-weight: 700; }}
      .stButton button[kind="primary"] {{ background: {_TEAL}; border-color: {_TEAL}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def _provider(mode: str) -> BankDataProvider:
    if mode == "cached_sectors":
        return create_bank_data_provider(
            mode,
            snapshot_path=DEFAULT_SECTORS_SNAPSHOT_PATH,
        )
    return create_bank_data_provider(mode)


@st.cache_data(ttl=300, show_spinner=False)
def _cached_discovery(
    mode: str,
    cache_version: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    del cache_version  # Included in the cache key to support an explicit source refresh.
    result = discover_banks(_provider(mode))
    return (
        result.ranked.to_dict(orient="records"),
        result.universe.frame.to_dict(orient="records"),
        asdict(result.status),
    )


@st.cache_data(ttl=300, show_spinner=False)
def _cached_universe(mode: str, cache_version: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    del cache_version
    result = _provider(mode).get_bank_universe()
    return result.universe.frame.to_dict(orient="records"), asdict(result.status)


def _set_status(status: dict[str, Any]) -> None:
    st.session_state["nusa_data_status"] = status


def _show_data_status(mode: str) -> None:
    status = st.session_state.get("nusa_data_status", {})
    if mode == "cached_sectors" and not status:
        try:
            status = asdict(_provider(mode).status)
        except (OSError, ValueError):
            status = {}
    retrieved = status.get("retrieved_at")
    display = format_source_status(mode, retrieved)
    badge_class = {
        "live": "nusa-badge-live",
        "cached_sectors": "nusa-badge-cached",
        "demo": "nusa-badge-demo",
        "fixture": "nusa-badge-demo",
    }[mode]
    st.markdown(
        f'<span class="{badge_class}">{display["badge"]}</span> &nbsp; '
        f'<span style="color:{_MUTED}">{status.get("source", display["message"])}</span>',
        unsafe_allow_html=True,
    )
    if mode == "cached_sectors":
        st.info(display["message"])
    elif mode in {"demo", "fixture"}:
        st.warning(display["message"], icon="⚠️")
    else:
        warning = status.get("warning")
        st.caption(display["message"] if not warning else f"{display['message']} {warning}")


def _company_label(row: dict[str, Any]) -> str:
    name = row.get("company_name") or row.get("ticker", "Unknown company")
    return f"{name} · {row.get('ticker', '')}"


def _unit_label(unit: str) -> str:
    return "percentage points" if unit == "percentage_points" else unit


st.markdown('<div class="nusa-kicker">Indonesian banking research</div>', unsafe_allow_html=True)
st.title("NUSA Intelligence")
st.markdown(
    "<div class=\"nusa-subtitle\">AI research agent for unusual financial changes "
    "in Indonesian listed banks</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Research settings")
    snapshot_available = Path(DEFAULT_SECTORS_SNAPSHOT_PATH).is_file()
    source_options = source_mode_options(snapshot_available=snapshot_available)
    source_labels = dict(source_options)
    source_choice = st.selectbox(
        "Data source",
        [mode for mode, _ in source_options],
        format_func=lambda mode: source_labels[mode],
        index=0,
        help="Choose a cached Sectors snapshot, an explicit live API source, or DEMO/SAMPLE.",
    )
    source_mode = source_choice
    if not snapshot_available:
        st.info(
            "No local Sectors snapshot is available. Select LIVE SECTORS or DEMO/SAMPLE; "
            "no cached real data is being substituted."
        )
    st.caption(
        "Live API access requires `SECTORS_API_KEY` in the environment or ignored .env file."
    )
    if st.button("Clear Streamlit cache", width="stretch"):
        st.session_state["nusa_cache_version"] = st.session_state.get("nusa_cache_version", 0) + 1
        _cached_discovery.clear()
        _cached_universe.clear()
        _provider.clear()
        st.rerun()

if st.session_state.get("nusa_source_mode") != source_mode:
    st.session_state["nusa_source_mode"] = source_mode
    st.session_state.pop("nusa_data_status", None)
    st.session_state.pop("nusa_discovery_rows", None)
    st.session_state.pop("nusa_company_rows", None)
    st.session_state.pop("nusa_investigation_result", None)
    st.session_state.pop("nusa_investigation_report", None)
    st.session_state.pop("nusa_followup_result", None)
    st.session_state.pop("nusa_selected_ticker", None)
    st.session_state.pop("nusa_company_selector", None)
    st.session_state.pop("nusa_priority_ticker", None)
    st.session_state.pop("nusa_research_question", None)
    st.session_state.pop(ResearchSessionMemory.SESSION_KEY, None)
    st.session_state["nusa_cache_version"] = st.session_state.get("nusa_cache_version", 0)

_show_data_status(source_mode)
st.write("")

discover_tab, investigate_tab, methodology_tab = st.tabs(
    ["DISCOVER", "INVESTIGATE", "METHODOLOGY"]
)


with discover_tab:
    st.subheader("Banking sector monitor")
    st.write("Screen the available bank universe for unusual annual financial changes.")
    analyze = st.button("Analyze Banks", type="primary", key="analyze_banks")
    demo_discover = False
    if source_mode == "demo":
        demo_discover = st.button(
            "Example: Find unusual financial changes among Indonesian banks",
            key="demo_discover_example",
        )
    if analyze or demo_discover:
        try:
            with st.spinner("Analyzing the selected data source…"):
                ranked_rows, company_rows, status = _cached_discovery(
                    source_mode, st.session_state.get("nusa_cache_version", 0)
                )
            st.session_state["nusa_discovery_rows"] = ranked_rows
            st.session_state["nusa_company_rows"] = company_rows
            _set_status(status)
            if source_mode == "demo":
                st.warning(format_source_status("demo")["message"], icon="⚠️")
        except Exception as error:
            failed_status = asdict(_provider(source_mode).status)
            _set_status(failed_status)
            st.error(
                f"Could not analyze the selected source ({type(error).__name__}). "
                "No alternative data source was substituted."
            )
            if failed_status.get("warning"):
                st.caption(f"Source status: {failed_status['warning']}")

    ranked_rows = st.session_state.get("nusa_discovery_rows")
    if ranked_rows is None:
        st.info("Run Analyze Banks to view source-backed research priorities.")
    elif not ranked_rows:
        st.info(
            "No scoreable anomalies were returned. Metric or peer coverage may be insufficient."
        )
    else:
        ranked_frame = pd.DataFrame(ranked_rows)
        st.markdown("#### Research priorities")
        display = ranked_frame.rename(
            columns={
                "ticker": "Ticker",
                "company_name": "Company",
                "primary_driver": "Primary driver",
                "score": "Research priority score",
                "eligible_metric_count": "Eligible metrics",
                "primary_change": "Driver change",
                "primary_change_unit": "Change unit",
                "primary_peer_median": "Peer median",
                "primary_deviation": "Peer deviation",
            }
        )[[
            "Ticker", "Company", "Primary driver", "Driver change", "Change unit",
            "Peer median", "Peer deviation", "Research priority score", "Eligible metrics",
        ]]
        display["Change unit"] = display["Change unit"].replace(
            {"percentage_points": "percentage points"}
        )
        display["Excluded metric flags"] = ranked_frame["excluded_metric_flags"].map(
            format_excluded_metric_flags
        )
        st.dataframe(display, hide_index=True, width="stretch")
        st.caption(
            "Scores rank unusual peer-relative changes for research; they are not "
            "recommendations or misconduct assessments."
        )
        flagged = ranked_frame.loc[ranked_frame["excluded_metric_flags"].map(bool)]
        if not flagged.empty:
            st.caption(
                "Some metric changes are excluded from scoring due to sign transitions, "
                "zero denominators, or small bases; those changes remain flagged in the detail."
            )

        selector_rows = ranked_frame.to_dict(orient="records")
        chosen_ticker = st.selectbox(
            "Choose a company to investigate",
            options=[str(row["ticker"]) for row in selector_rows],
            format_func=lambda ticker: next(
                _company_label(row) for row in selector_rows if row["ticker"] == ticker
            ),
            key="nusa_priority_ticker",
        )
        selected_row = next(row for row in selector_rows if row["ticker"] == chosen_ticker)
        metric_a, metric_b, metric_c = st.columns(3)
        with metric_a:
            st.metric("Company", selected_row.get("company_name") or chosen_ticker)
        with metric_b:
            st.metric("Primary driver", selected_row.get("primary_driver") or "Not available")
        with metric_c:
            st.metric("Priority score", selected_row.get("score", "Not available"))
        if st.button("Investigate selected bank", key="investigate_priority"):
            st.session_state["nusa_selected_ticker"] = chosen_ticker
            st.session_state["nusa_company_selector"] = chosen_ticker
            st.success("Company selected. Continue in the INVESTIGATE section.")
        if source_mode == "demo" and st.button(
            "Investigate highest-ranked demo bank", key="demo_investigate_top"
        ):
            top_ticker = str(selector_rows[0]["ticker"])
            st.session_state["nusa_selected_ticker"] = top_ticker
            st.session_state["nusa_company_selector"] = top_ticker
            st.success(
                f"{_company_label(selector_rows[0])} selected. Open INVESTIGATE and run the workflow."
            )


with investigate_tab:
    st.subheader("Company research")
    company_rows = st.session_state.get("nusa_company_rows")
    if not company_rows:
        st.write("Load the selected source's company list to begin a focused investigation.")
        if st.button("Load companies", key="load_companies"):
            try:
                with st.spinner("Loading the bounded bank universe…"):
                    company_rows, status = _cached_universe(
                        source_mode, st.session_state.get("nusa_cache_version", 0)
                    )
                st.session_state["nusa_company_rows"] = company_rows
                _set_status(status)
                st.rerun()
            except Exception as error:
                failed_status = asdict(_provider(source_mode).status)
                _set_status(failed_status)
                st.error(
                    f"Could not load companies ({type(error).__name__}). "
                    "No alternative data source was substituted."
                )
                if failed_status.get("warning"):
                    st.caption(f"Source status: {failed_status['warning']}")
    else:
        by_ticker = {str(row["ticker"]): row for row in company_rows}
        tickers = list(by_ticker)
        default_ticker = st.session_state.get("nusa_selected_ticker")
        default_index = tickers.index(default_ticker) if default_ticker in tickers else 0
        ticker = st.selectbox(
            "Company",
            options=tickers,
            index=default_index,
            format_func=lambda value: _company_label(by_ticker[value]),
            key="nusa_company_selector",
        )
        if source_mode == "demo" and st.button(
            "Example comparison: this change with DEMOBANK2 and DEMOBANK3",
            key="demo_comparison_example",
        ):
            st.session_state["nusa_research_question"] = (
                "Compare this change with DEMOBANK2 and DEMOBANK3."
            )
        question = st.text_input(
            "Research question",
            placeholder="Run an investigation, then ask a follow-up about its validated evidence.",
            key="nusa_research_question",
        )
        run_research = st.button("Run investigation", type="primary", key="run_investigation")
        run_followup = st.button(
            "Run follow-up peer comparison",
            key="run_followup_comparison",
            disabled=(
                st.session_state.get("nusa_investigation_result") is None
                or not question.strip()
            ),
        )
        if run_research:
            try:
                memory = ResearchSessionMemory.from_session_state(st.session_state)
                synthesizer = LLMResearchSynthesizer(create_llm_provider_from_env())
                orchestrator = ResearchOrchestrator(
                    _provider(source_mode),
                    synthesizer=synthesizer,
                    session_memory=memory,
                )
                with st.spinner("Running the evidence-led research workflow…"):
                    result = orchestrator.run(f"Investigate {ticker}")
                st.session_state["nusa_investigation_result"] = result
                st.session_state["nusa_investigation_report"] = result.synthesis
                st.session_state.pop("nusa_followup_result", None)
                _set_status(asdict(_provider(source_mode).status))
            except Exception as error:
                failed_status = asdict(_provider(source_mode).status)
                _set_status(failed_status)
                st.error(
                    f"The investigation could not be completed ({type(error).__name__}). "
                    "Review the data-source status; no fabricated fallback data was used."
                )
                if failed_status.get("warning"):
                    st.caption(f"Source status: {failed_status['warning']}")

        if run_followup:
            try:
                memory = ResearchSessionMemory.from_session_state(st.session_state)
                orchestrator = ResearchOrchestrator(
                    _provider(source_mode),
                    synthesizer=LLMResearchSynthesizer(create_llm_provider_from_env()),
                    session_memory=memory,
                )
                with st.spinner("Resolving the follow-up from session memory…"):
                    followup_result = orchestrator.run(question)
                st.session_state["nusa_followup_result"] = followup_result
                _set_status(asdict(_provider(source_mode).status))
            except Exception as error:
                st.error(
                    f"The follow-up comparison could not be completed ({type(error).__name__}). "
                    "It requires an existing investigation with validated metric evidence."
                )

    result = st.session_state.get("nusa_investigation_result")
    if result is not None:
        events = {event.event for event in result.trace.events}
        stages = [
            ("Understanding request", "INTENT_RESOLVED" in events),
            ("Research plan created", "PLAN_VALIDATED" in events),
            ("Retrieving evidence", "TOOL_COMPLETED" in events),
            ("Running quantitative analysis", "ANALYSIS_COMPLETED" in events),
            ("Comparing peers", "compare_peer_metrics" in result.outputs),
            ("Validating evidence", "EVIDENCE_VALIDATED" in events),
            ("Generating research report", "SYNTHESIS_COMPLETED" in events),
        ]
        st.markdown("#### Research workflow")
        for label, complete in stages:
            st.markdown(f"{'✓' if complete else '○'} &nbsp; {label}")

        with st.expander("Research plan", expanded=False):
            st.json(result.plan.to_dict())

        st.markdown("#### Quantitative evidence")
        evidence_items = list(result.evidence_ledger)
        if not evidence_items:
            st.info("No validated anomaly evidence was available for this company.")
        else:
            metrics = list(dict.fromkeys(item.metric for item in evidence_items))
            metric = st.selectbox("Metric", metrics, key="nusa_metric_chart")
            selected_evidence = [item for item in evidence_items if item.metric == metric]
            for item in selected_evidence:
                st.markdown(f"**{item.ticker} · {item.metric} · {item.period}**")
                history = pd.DataFrame(
                    {"Reported value": [item.previous_value, item.current_value]},
                    index=[item.period.split(" to ")[0], item.period.split(" to ")[1]],
                )
                st.line_chart(history, width="stretch")
                if item.scoring_eligible:
                    peer_change = pd.DataFrame(
                        {f"Change ({_unit_label(item.change_unit)})": [item.change, item.peer_median]},
                        index=[item.ticker, "Peer median"],
                    )
                    st.bar_chart(peer_change, width="stretch")
                else:
                    st.caption(
                        f"Not scored: {item.exclusion_reason}. Absolute monetary change is "
                        "retained; percentage change is not used for scoring."
                    )

            evidence_frame = pd.DataFrame([item.to_dict() for item in evidence_items])
            with st.expander("Evidence ledger", expanded=False):
                st.dataframe(evidence_frame, hide_index=True, width="stretch")
            components = [
                {
                    "Ticker": item.ticker,
                    "Metric": item.metric,
                    "Period": item.period,
                    f"Change ({_unit_label(item.change_unit)})": item.change,
                    f"Peer median ({_unit_label(item.change_unit)})": item.peer_median,
                    "Peers": item.peer_count,
                    f"Deviation ({_unit_label(item.change_unit)})": item.deviation,
                    "Scoring eligible": item.scoring_eligible,
                    "Exclusion reason": item.exclusion_reason,
                    "Evidence ID": item.evidence_id,
                }
                for item in evidence_items
            ]
            with st.expander("Anomaly components", expanded=False):
                st.dataframe(pd.DataFrame(components), hide_index=True, width="stretch")

        comparison = result.outputs.get("compare_peer_metrics")
        st.markdown("#### Peer comparison")
        if comparison and comparison.value.get("comparisons"):
            st.dataframe(
                pd.DataFrame(comparison.value["comparisons"]),
                hide_index=True,
                width="stretch",
            )
        else:
            st.info(
                "Peer comparison is limited to the peer baseline recorded in the evidence ledger."
            )

        report = st.session_state.get("nusa_investigation_report", result.synthesis)
        st.markdown("#### Research report")
        st.write(report.executive_summary)
        report_sections = [
            ("Key findings", report.key_findings),
            ("Historical context", report.historical_context),
            ("Peer comparison", report.peer_comparison),
            ("Why flagged", report.why_flagged),
            ("Limitations", report.limitations),
        ]
        for heading, lines in report_sections:
            st.markdown(f"**{heading}**")
            if lines:
                for line in lines:
                    st.markdown(f"- {line}")
            else:
                st.caption("No additional validated detail available.")
        if report.evidence_references:
            st.caption("Evidence references: " + ", ".join(report.evidence_references))

        followup_result = st.session_state.get("nusa_followup_result")
        if followup_result is not None:
            comparison_output = followup_result.outputs.get("compare_peer_metrics")
            st.markdown("#### Follow-up peer comparison")
            st.caption(
                "Resolved from session memory: "
                f"{', '.join(followup_result.plan.tickers)} · "
                f"metric: {followup_result.plan.tasks[0].arguments.get('metric', 'not specified')}"
            )
            if comparison_output and comparison_output.value.get("comparisons"):
                comparison_frame = pd.DataFrame(comparison_output.value["comparisons"])
                display_columns = [
                    column
                    for column in (
                        "ticker", "metric", "period", "change", "peer_median",
                        "peer_count", "deviation", "evidence_id",
                    )
                    if column in comparison_frame.columns
                ]
                st.dataframe(
                    comparison_frame[display_columns],
                    hide_index=True,
                    width="stretch",
                )
                st.caption(followup_result.synthesis.executive_summary)
            else:
                st.info("No validated comparison evidence was available for the requested peers.")


with methodology_tab:
    st.subheader("How NUSA builds a research priority")
    st.markdown(
        """
        **Data source.** LIVE SECTORS uses the authenticated Sectors Financial API. SECTORS
        CACHED SNAPSHOT uses a local Sectors-origin response with its original retrieval time;
        it is not a live refresh. DEMO/SAMPLE uses the bundled fictional fixture and is never
        represented as current market data. Source modes never substitute for one another.

        **Deterministic analytics.** Real Sectors ranking initially uses annual earnings,
        net interest income, assets, equity, and ROA; NIM is excluded. Monetary changes use
        `(current - previous) / abs(previous) × 100`. A sign transition, zero prior value, or
        prior value below 1% of the median absolute prior-year value is retained as an absolute
        change but excluded from percentage scoring. ROA is reported in percentage points.
        Eligible changes use leave-one-out peer medians and percentile deviation contributions.
        The 0–100 composite is adjusted by eligible-metric coverage, so missing metrics are not
        treated as zero evidence and partial coverage is visible.

        **Evidence grounding.** Every supported quantitative finding is carried in the Evidence
        Ledger with its source, endpoint, period, calculation, values, and data mode. The report
        layer receives validated evidence and must cite its evidence IDs. Missing numbers remain
        missing; they are not inferred or filled.

        **AI-agent architecture.** A bounded intent resolver and validated research plan route
        through explicit safe tools. Quantitative analysis stays deterministic. The optional
        language model interprets unresolved wording and writes a readable synthesis; it does
        not execute code or originate financial facts. Operational progress is shown without
        exposing hidden reasoning.

        **Disclaimer.** A research-priority anomaly is not proof of misconduct or fraud and is
        not a buy/sell recommendation. NUSA does not provide personalized investment advice.
        Verify source coverage, periods, and context before making decisions.
        """
    )
