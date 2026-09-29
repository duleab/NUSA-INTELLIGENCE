"""NUSA Intelligence — compact Streamlit research workspace."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from nusa.agent.orchestration import ResearchOrchestrator
from nusa.agent.session_memory import ResearchSessionMemory
from nusa.agent.synthesis import LLMResearchSynthesizer, create_llm_provider_from_env
from nusa.discovery.workflow import discover_banks
from nusa.providers import BankDataProvider, create_bank_data_provider


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
      div[data-testid="stTabs"] button {{ font-weight: 700; }}
      .stButton button[kind="primary"] {{ background: {_TEAL}; border-color: {_TEAL}; }}
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def _provider(mode: str) -> BankDataProvider:
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
    configured_live = mode == "live"
    is_live = bool(status.get("is_live", configured_live))
    label = "LIVE" if is_live else "DEMO/SAMPLE"
    badge_class = "nusa-badge-live" if is_live else "nusa-badge-demo"
    source = status.get("source", "Sectors Financial API" if is_live else "Bundled sample fixture")
    warning = status.get("warning")
    retrieved = status.get("retrieved_at")
    status_text = f"{source} · {status.get('mode', mode)}"
    if retrieved:
        status_text += f" · Retrieved {retrieved}"
    st.markdown(
        f'<span class="{badge_class}">{label}</span> &nbsp; '
        f'<span style="color:{_MUTED}">{status_text}</span>',
        unsafe_allow_html=True,
    )
    if not is_live:
        st.warning("DEMO/SAMPLE DATA — not current live market data", icon="⚠️")
    elif warning:
        st.caption(f"Source note: {warning}")


def _company_label(row: dict[str, Any]) -> str:
    name = row.get("company_name") or row.get("ticker", "Unknown company")
    return f"{name} · {row.get('ticker', '')}"


st.markdown('<div class="nusa-kicker">Indonesian banking research</div>', unsafe_allow_html=True)
st.title("NUSA Intelligence")
st.markdown(
    "<div class=\"nusa-subtitle\">AI research agent for unusual financial changes "
    "in Indonesian listed banks</div>",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Research settings")
    source_choice = st.selectbox(
        "Data source",
        ["DEMO/SAMPLE", "LIVE — Sectors"],
        index=0,
        help="Live requests use the authenticated Sectors API. Demo is the safe default.",
    )
    source_mode = "live" if source_choice.startswith("LIVE") else "demo"
    st.caption(
        "Live API access requires `SECTORS_API_KEY` in the environment or ignored .env file."
    )
    if st.button("Clear Streamlit cache", width="stretch"):
        st.session_state["nusa_cache_version"] = st.session_state.get("nusa_cache_version", 0) + 1
        _cached_discovery.clear()
        _cached_universe.clear()
        st.rerun()

if st.session_state.get("nusa_source_mode") != source_mode:
    st.session_state["nusa_source_mode"] = source_mode
    st.session_state.pop("nusa_data_status", None)
    st.session_state.pop("nusa_discovery_rows", None)
    st.session_state.pop("nusa_company_rows", None)
    st.session_state.pop("nusa_investigation_result", None)
    st.session_state.pop("nusa_investigation_report", None)
    st.session_state.pop("nusa_selected_ticker", None)
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
    if analyze:
        try:
            with st.spinner("Analyzing the selected data source…"):
                ranked_rows, company_rows, status = _cached_discovery(
                    source_mode, st.session_state.get("nusa_cache_version", 0)
                )
            st.session_state["nusa_discovery_rows"] = ranked_rows
            st.session_state["nusa_company_rows"] = company_rows
            _set_status(status)
            if not status.get("is_live"):
                st.warning("DEMO/SAMPLE DATA — not current live market data", icon="⚠️")
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
            }
        )[["Ticker", "Company", "Primary driver", "Research priority score"]]
        st.dataframe(display, hide_index=True, width="stretch")
        st.caption(
            "Scores rank unusual peer-relative changes for research; they are not "
            "recommendations or misconduct assessments."
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
            st.success("Company selected. Continue in the INVESTIGATE section.")


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
        question = st.text_input(
            "Research question",
            placeholder="e.g. What drove the change, and how does it compare with peers?",
            key="nusa_research_question",
        )
        run_research = st.button("Run investigation", type="primary", key="run_investigation")
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
                    report = (
                        orchestrator.answer_followup(question, result)
                        if question.strip()
                        else result.synthesis
                    )
                st.session_state["nusa_investigation_result"] = result
                st.session_state["nusa_investigation_report"] = report
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
                peer_change = pd.DataFrame(
                    {"Year-over-year change (%)": [item.change, item.peer_median]},
                    index=[item.ticker, "Peer median"],
                )
                st.bar_chart(peer_change, width="stretch")

            evidence_frame = pd.DataFrame([item.to_dict() for item in evidence_items])
            with st.expander("Evidence ledger", expanded=False):
                st.dataframe(evidence_frame, hide_index=True, width="stretch")
            components = [
                {
                    "Ticker": item.ticker,
                    "Metric": item.metric,
                    "Period": item.period,
                    "Change (%)": item.change,
                    "Peer median (%)": item.peer_median,
                    "Peers": item.peer_count,
                    "Deviation (pp)": item.deviation,
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


with methodology_tab:
    st.subheader("How NUSA builds a research priority")
    st.markdown(
        """
        **Data source.** Live mode uses the authenticated Sectors Financial API. Demo mode uses
        the bundled fictional fixture and is never represented as current market data. API and
        coverage limitations are surfaced rather than silently substituted.

        **Deterministic analytics.** The existing Discovery pipeline uses only annual fields
        returned by the provider. It calculates year-over-year changes, compares each bank with
        the median of comparable peers, and ranks absolute deviations by cross-sectional
        percentile. Insufficient company or peer coverage yields no score.

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
