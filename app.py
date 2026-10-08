"""NUSA Intelligence — compact Streamlit research workspace."""

from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path
import re
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from nusa.agent.orchestration import (
    DeepInvestigationOrchestrator,
    DeepInvestigationResult,
    ResearchOrchestrator,
)
from nusa.agent.session_memory import ResearchSessionMemory
from nusa.agent.synthesis import LLMResearchSynthesizer, create_llm_provider_from_env
from nusa.discovery.anomaly import REAL_SCORING_METRICS
from nusa.discovery.workflow import discover_banks
from nusa.providers import BankDataProvider, create_bank_data_provider
from nusa.providers.sectors_snapshot import DEFAULT_SECTORS_SNAPSHOT_PATH
from nusa.ui import charts as chart_ui
from nusa.ui import deep_panel as deep_ui
from nusa.ui import insights as ins
from nusa.ui.presentation import (
    bank_header_html,
    bank_logo_html,
    comparison_table_rows,
    format_change,
    format_evidence_value,
    format_idr_value,
    format_retrieved_date,
    unit_label,
)
from nusa.ui.source_modes import (
    format_excluded_metric_flags,
    format_source_status,
    source_mode_options,
)
from nusa.ui.chart_styles import get_enhanced_chart_css


load_dotenv()
st.set_page_config(
    page_title="NUSA Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      /* ── Design tokens ────────────────────────────── */
      :root {
        color-scheme: dark;
        --bg:          #06101E;
        --surface0:    #0B1828;
        --surface1:    #0F1E33;
        --surface2:    #162540;
        --surface3:    #1C2D4E;
        --primary:     #3B82F6;
        --primary-d:   #2563EB;
        --accent:      #60A5FA;
        --success:     #22C55E;
        --warning:     #F59E0B;
        --error:       #EF4444;
        --text:        #EFF6FF;
        --text-2:      #94A3B8;
        --text-3:      #64748B;
        --border:      rgba(255,255,255,.07);
        --border-hi:   rgba(255,255,255,.13);
        --r:           10px;
        --r-lg:        14px;
        font-family: Inter, ui-sans-serif, system-ui, -apple-system,
                     BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      /* ── Shell ────────────────────────────────────── */
      .stApp, [data-testid="stAppViewContainer"] { background: var(--bg); color: var(--text); }
      [data-testid="stHeader"] { background: rgba(6,16,30,.97); backdrop-filter: blur(12px); }
      .block-container { max-width: 1440px; padding: 1.2rem clamp(.75rem,2.5vw,2rem) 4rem; }

      /* ── Sidebar ──────────────────────────────────── */
      [data-testid="stSidebar"] {
        background: var(--surface0);
        border-right: 1px solid var(--border-hi);
      }
      [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
      [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--text-2); }

      /* ── Typography ───────────────────────────────── */
      h1,h2,h3,h4 { color: var(--text); letter-spacing: -.025em; font-weight: 700; }
      h1 { font-size: clamp(1.7rem,3vw,2rem); }
      h2 { font-size: clamp(1.2rem,2vw,1.4rem); }
      h3 { font-size: 1.05rem; }
      p,li,label { color: var(--text); line-height: 1.6; }
      small, [data-testid="stCaptionContainer"] { color: var(--text-2); font-size: .82rem; line-height: 1.5; }

      /* ── Tabs ─────────────────────────────────────── */
      [data-testid="stTabs"] [data-baseweb="tab-list"]         { border-bottom: 1px solid var(--border-hi); gap: .2rem; }
      [data-testid="stTabs"] [role="tab"]                      { color: var(--text-2); font-weight: 600; padding: .6rem 1rem; }
      [data-testid="stTabs"] [role="tab"][aria-selected="true"]{ color: var(--text); font-weight: 700; }
      [data-testid="stTabs"] [data-baseweb="tab-highlight"]    { background: var(--primary); height: 2px; border-radius: 1px; }

      /* ── Enhanced Metric tiles ─────────────────────── */
      [data-testid="stMetric"] {
        background: linear-gradient(135deg, var(--surface1) 0%, var(--surface2) 100%);
        border: 1px solid var(--border-hi);
        border-radius: var(--r-lg);
        padding: 1.2rem 1.5rem;
        min-width: 0;
        box-shadow: 0 2px 4px rgba(0,0,0,.1);
        transition: all 0.3s ease;
      }
      
      [data-testid="stMetric"]:hover {
        border-color: var(--accent);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
        transform: translateY(-2px);
      }
      
      [data-testid="stMetricLabel"] {
        color: var(--accent);
        font-size: .7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin-bottom: .5rem;
      }
      [data-testid="stMetricValue"] {
        color: var(--text);
        font-size: clamp(1.2rem,2.5vw,1.8rem);
        font-weight: 800;
        letter-spacing: -.03em;
        line-height: 1.1;
      }

      /* ── Enhanced Cards / Containers ─────────────────── */
      [data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(135deg, var(--surface1) 0%, var(--surface2) 100%);
        border: 1px solid var(--border-hi);
        border-radius: var(--r-lg);
        box-shadow: 0 4px 6px rgba(0,0,0,.08);
        transition: all 0.3s ease;
      }
      
      [data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: rgba(96, 165, 250, 0.3);
        box-shadow: 0 8px 25px rgba(0,0,0,.15);
      }
      
      [data-testid="stExpander"] {
        background: var(--surface1);
        border: 1px solid var(--border);
        border-radius: var(--r-lg);
        margin: 0.5rem 0;
      }
      
      [data-testid="stExpander"]:hover {
        border-color: var(--border-hi);
      }
      
      [data-testid="stAlert"]    { 
        border-radius: var(--r-lg); 
        border-left: 4px solid var(--accent);
        background: rgba(59, 130, 246, 0.05);
      }
      
      [data-testid="stDataFrame"]{ 
        border: 1px solid var(--border-hi); 
        border-radius: var(--r-lg);
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,.05);
      }

      /* ── Enhanced Inputs ─────────────────────────────── */
      [data-testid="stTextInput"] input,
      [data-testid="stTextArea"] textarea,
      [data-baseweb="select"] > div {
        background: var(--surface2) !important;
        color: var(--text) !important;
        border-color: var(--border-hi) !important;
        border-radius: var(--r-lg) !important;
        transition: all 0.2s ease !important;
      }
      
      [data-testid="stTextInput"] input:focus,
      [data-testid="stTextArea"] textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1) !important;
      }

      /* ── Enhanced Buttons ────────────────────────────── */
      [data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-d) 100%);
        border: none;
        color: #fff;
        border-radius: var(--r-lg);
        font-weight: 650;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
      }
      
      [data-testid="stBaseButton-primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
      }
      
      [data-testid="stBaseButton-secondary"] {
        background: var(--surface2);
        border: 1px solid var(--border-hi);
        color: var(--text);
        border-radius: var(--r-lg);
        font-weight: 600;
        padding: 0.75rem 1.5rem;
        transition: all 0.3s ease;
      }
      
      [data-testid="stBaseButton-secondary"]:hover {
        background: var(--surface3);
        border-color: var(--accent);
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(96, 165, 250, 0.15);
      }

      /* ── Enhanced Status badges ──────────────────────── */
      .nusa-badge {
        display: inline-flex; 
        align-items: center; 
        gap: .4rem;
        border-radius: 8px; 
        padding: .4rem .8rem;
        font-size: .72rem; 
        font-weight: 700; 
        letter-spacing: .04em;
        border: 1px solid transparent;
        box-shadow: 0 1px 3px rgba(0,0,0,.1);
        transition: all 0.2s ease;
      }
      
      .nusa-badge:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 6px rgba(0,0,0,.15);
      }
      
      .nusa-badge-live   { 
        color: #86efac; 
        background: linear-gradient(135deg, #0b2218 0%, #064e3b 100%); 
        border-color: #15532e; 
      }
      .nusa-badge-demo   { 
        color: #fcd34d; 
        background: linear-gradient(135deg, #271c04 0%, #451a03 100%); 
        border-color: #854d0e; 
      }
      .nusa-badge-cached { 
        color: #93c5fd; 
        background: linear-gradient(135deg, #0c1e3e 0%, #1e3a8a 100%); 
        border-color: #1e40af; 
      }

      /* ── Enhanced Kicker / subtitle ──────────────────── */
      .nusa-kicker {
        color: var(--accent); 
        font-size: .7rem; 
        font-weight: 700;
        letter-spacing: .16em; 
        text-transform: uppercase; 
        margin-bottom: .25rem;
        display: flex;
        align-items: center;
        gap: .5rem;
      }
      
      .nusa-subtitle { 
        color: var(--text-2); 
        font-size: .95rem; 
        margin-top: -.35rem; 
        line-height: 1.5;
      }

      /* ── Enhanced Hero ticker display ────────────────── */
      .nusa-rank-label  { 
        color: var(--accent); 
        font-size: .7rem; 
        font-weight: 700; 
        letter-spacing: .14em; 
        text-transform: uppercase; 
      }
      .nusa-rank-ticker { 
        color: var(--text); 
        font-size: 2.2rem; 
        font-weight: 800; 
        letter-spacing: -.04em; 
        line-height: 1.1;
        background: linear-gradient(135deg, var(--text) 0%, var(--accent) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .nusa-rank-company{ 
        color: var(--text-2); 
        font-size: .88rem; 
        margin-top: .1rem; 
      }

      /* ── Enhanced Priority / evidence labels ─────────── */
      .nusa-priority-title  { 
        color: var(--text-2); 
        text-transform: uppercase; 
        letter-spacing: .09em; 
        font-size: .75rem; 
        font-weight: 700; 
      }
      .nusa-priority-ticker { 
        color: var(--text); 
        font-size: 1.8rem; 
        font-weight: 750; 
        margin: .2rem 0;
        background: linear-gradient(135deg, var(--text) 0%, var(--primary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .nusa-priority-company{ 
        color: var(--text-2); 
        font-size: .92rem; 
      }
      .nusa-evidence-title  { 
        color: var(--text); 
        font-size: .83rem; 
        font-weight: 700; 
        text-transform: uppercase; 
        letter-spacing: .06em; 
      }
      .nusa-insight-num     { 
        color: var(--accent); 
        font-size: .68rem; 
        font-weight: 700; 
        letter-spacing: .1em; 
        text-transform: uppercase; 
      }

      /* ── Chart enhancements ──────────────────────────── */
      .stPlotlyChart > div {
        border-radius: var(--r-lg);
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0,0,0,.1);
      }
      
      /* Enhanced responsiveness */
      @media (max-width: 760px) {
        .block-container { padding: .75rem .75rem 3rem; }
        [data-testid="stMetric"] { padding: 1rem; }
        .nusa-priority-ticker { font-size: 1.4rem; }
        .nusa-rank-ticker { font-size: 1.8rem; }
      }
      
      /* Loading states */
      .chart-loading {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 300px;
        color: var(--text-2);
        font-style: italic;
      }
      
      /* Accessibility enhancements */
      @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
          animation-duration: 0.01ms !important;
          animation-iteration-count: 1 !important;
          transition-duration: 0.01ms !important;
        }
      }
    </style>
    """ + get_enhanced_chart_css(),
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


def _active_status(mode: str) -> dict[str, Any]:
    status = st.session_state.get("nusa_data_status", {})
    if not status:
        try:
            status = asdict(_provider(mode).status)
        except (OSError, ValueError, RuntimeError):
            status = {}
    return status


def _show_data_status(mode: str) -> None:
    status = _active_status(mode)
    retrieved = status.get("retrieved_at")
    display = format_source_status(mode, retrieved)
    badge_class = {
        "live": "nusa-badge-live",
        "cached_sectors": "nusa-badge-cached",
        "demo": "nusa-badge-demo",
        "fixture": "nusa-badge-demo",
    }[mode]
    st.markdown(
        f'<span class="nusa-badge {badge_class}">{display["badge"]}</span>',
        unsafe_allow_html=True,
    )
    if mode == "cached_sectors":
        st.caption(
            f"Sectors-origin data · Retrieved {format_retrieved_date(retrieved)} · "
            "Not a live refresh"
        )
    elif mode in {"demo", "fixture"}:
        st.warning(display["message"], icon="⚠️")
    else:
        warning = status.get("warning")
        st.caption(warning or display["message"])


def _summary_metrics(mode: str) -> tuple[str, str, str, str]:
    """Summarize local source coverage without initiating a live request."""
    if mode == "live":
        return "On run", "On run", "On run", "Evidence-led"
    try:
        frame = _provider(mode).get_bank_universe().universe.frame
    except (OSError, ValueError, RuntimeError, KeyError):
        return "Unavailable", "—", "—", "Evidence-led"

    annual_fields: dict[str, set[str]] = {}
    for column in frame.columns:
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)\[(\d{4})\]", str(column))
        if match:
            annual_fields.setdefault(match.group(1), set()).add(match.group(2))
    paired_metrics = {
        metric for metric, years in annual_fields.items() if len(years) >= 2
    }
    years = sorted({year for values in annual_fields.values() for year in values})
    if mode == "cached_sectors":
        metric_count = len(paired_metrics.intersection(REAL_SCORING_METRICS))
    else:
        metric_count = len(paired_metrics)
    period = f"{years[0]}–{years[-1]}" if len(years) >= 2 else "—"
    return str(len(frame)), period, str(metric_count), "Evidence-led"


def _company_label(row: dict[str, Any]) -> str:
    name = row.get("company_name") or row.get("ticker", "Unknown company")
    return f"{name} · {row.get('ticker', '')}"


def _show_action_error(summary: str, error: BaseException) -> None:
    st.error(summary)
    detail = str(error).strip()
    if detail:
        with st.expander("Technical detail"):
            st.code(detail)


with st.sidebar:
    st.markdown("## NUSA")
    st.caption("Banking research workspace")
    st.markdown("### DATA SOURCE")
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
    if snapshot_available:
        sidebar_status = _active_status(source_mode)
        st.caption(sidebar_status.get("source", source_labels[source_mode]))
        if sidebar_status.get("retrieved_at"):
            st.caption(f"Retrieved {format_retrieved_date(sidebar_status['retrieved_at'])}")
    if not snapshot_available:
        st.info(
            "No local Sectors snapshot is available. Select LIVE SECTORS or DEMO/SAMPLE; "
            "no cached real data is being substituted."
        )
    st.caption(
        "Live API access requires `SECTORS_API_KEY` in the environment or ignored .env file."
    )
    st.markdown("### STATUS")
    source_summary = _summary_metrics(source_mode)
    st.caption(f"Companies available · {source_summary[0]}")
    st.caption(f"Annual coverage · {source_summary[1]}")
    st.caption(f"Scoring metrics · {source_summary[2]}")
    st.markdown("### ABOUT")
    st.caption("Evidence-grounded research on unusual changes among Indonesian listed banks.")
    if st.button("Clear Streamlit cache", width="stretch"):
        st.session_state["nusa_cache_version"] = st.session_state.get("nusa_cache_version", 0) + 1
        _cached_discovery.clear()
        _cached_universe.clear()
        _provider.clear()
        st.rerun()

if st.session_state.get("nusa_source_mode") != source_mode:
    st.session_state["nusa_source_mode"] = source_mode
    for key in (
        "nusa_data_status",
        "nusa_discovery_rows",
        "nusa_company_rows",
        "nusa_investigation_result",
        "nusa_investigation_report",
        "nusa_followup_result",
        "nusa_deep_result",
        "nusa_structured_followup_answer",
        "nusa_selected_ticker",
        "nusa_company_selector",
        "nusa_priority_ticker",
        "nusa_research_question",
        ResearchSessionMemory.SESSION_KEY,
    ):
        st.session_state.pop(key, None)
    st.session_state["nusa_cache_version"] = st.session_state.get("nusa_cache_version", 0)

header_left, header_right = st.columns([2.8, 1], vertical_alignment="center")
with header_left:
    st.markdown(
        '<div class="nusa-kicker">Indonesian banking research</div>',
        unsafe_allow_html=True,
    )
    st.title("NUSA Intelligence")
    st.markdown(
        '<div class="nusa-subtitle">Evidence-grounded AI research for Indonesian banking.</div>',
        unsafe_allow_html=True,
    )
with header_right:
    _show_data_status(source_mode)

summary = _summary_metrics(source_mode)
summary_columns = st.columns(4)
summary_values = [
    ("Banks in source", summary[0]),
    ("Financial periods", summary[1]),
    ("Scoring metrics", summary[2]),
    ("Research workflow", summary[3]),
]
for column, (label, value) in zip(summary_columns, summary_values):
    with column:
        st.metric(label, value)

# ── Judge Mode Quick Launch Banner ──────────────────────────────────────────
with st.container(border=True):
    jm_cols = st.columns([3.5, 1], vertical_alignment="center")
    with jm_cols[0]:
        st.markdown(
            f"**⚖️ NUSA for judges:** **{summary[0]}** IDX banks · "
            f"**{summary[2]}** metrics · **{summary[1]}** coverage · "
            "Autonomous investigation · Deterministic scoring · Evidence-grounded"
        )
        st.caption(
            "A normal chatbot answers questions you bring it. "
            "NUSA **discovers anomalies → plans → investigates → compares peers → validates evidence**."
        )
    with jm_cols[1]:
        if st.button("⚡ Run Judge Demo", key="judge_demo_header_btn", type="primary", use_container_width=True):
            st.session_state["nusa_trigger_judge_demo"] = True
            st.rerun()

discover_tab, investigate_tab, banks_tab, methodology_tab = st.tabs(
    ["DISCOVER", "INVESTIGATE", "BANKS", "METHODOLOGY"]
)


with discover_tab:
    st.subheader("Discover unusual financial changes")
    st.write("Rank IDX banks by transparent peer-relative financial change.")
    st.text_input(
        "Research question",
        value="Find unusual financial changes among Indonesian banks",
        key="nusa_discovery_question",
    )
    col_btn1, col_btn2 = st.columns([1, 1.3])
    with col_btn1:
        analyze = st.button("Run Discovery", type="primary", key="analyze_banks")
    with col_btn2:
        run_judge_demo = st.button(
            "⚡ Run Judge Demo (1-Click)",
            key="run_judge_demo",
            help="One-click full path: Loads cached/demo data, discovers anomalies, selects #1 priority, runs autonomous deep investigation, and shows validated findings.",
        )
    demo_discover = False
    if source_mode == "demo":
        demo_discover = st.button(
            "Example: Find unusual financial changes among Indonesian banks",
            key="demo_discover_example",
        )

    if run_judge_demo or st.session_state.pop("nusa_trigger_judge_demo", False):
        try:
            with st.spinner("Executing Judge Demo: Discovery → Priority Selection → Autonomous Deep Investigation…"):
                ranked_rows, company_rows, status = _cached_discovery(
                    source_mode, st.session_state.get("nusa_cache_version", 0)
                )
                st.session_state["nusa_discovery_rows"] = ranked_rows
                st.session_state["nusa_company_rows"] = company_rows
                _set_status(status)
                if ranked_rows:
                    top_bank = ranked_rows[0]
                    top_ticker = str(top_bank["ticker"])
                    st.session_state["nusa_selected_ticker"] = top_ticker
                    st.session_state["nusa_company_selector"] = top_ticker
                    
                    synthesizer = LLMResearchSynthesizer(create_llm_provider_from_env())
                    deep_orchestrator = DeepInvestigationOrchestrator(
                        _provider(source_mode),
                        synthesizer=synthesizer,
                    )
                    deep_result = deep_orchestrator.run_deep(top_ticker, ranked_rows)
                    st.session_state["nusa_deep_result"] = deep_result
                    st.session_state["nusa_investigation_result"] = None
                    st.session_state.pop("nusa_followup_result", None)
                    st.success(f"Judge Demo completed for {top_ticker}! Review findings below and in INVESTIGATE.")
        except Exception as error:
            _show_action_error(
                f"Judge demo failed ({type(error).__name__}). No fallback data was used.",
                error,
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
            _show_action_error(
                f"Could not analyze the selected source ({type(error).__name__}). "
                "No alternative data source was substituted.",
                error,
            )
            if failed_status.get("warning"):
                st.caption(f"Source status: {failed_status['warning']}")

    ranked_rows = st.session_state.get("nusa_discovery_rows")
    if ranked_rows is None:
        st.info("Run Discovery to view source-backed research priorities.")
    elif not ranked_rows:
        st.info(
            "No scoreable anomalies were returned. Metric or peer coverage may be insufficient."
        )
    else:
        ranked_frame = pd.DataFrame(ranked_rows)
        selector_rows = ranked_frame.to_dict(orient="records")
        st.markdown("#### Ranked research priorities")
        top_row = selector_rows[0]
        with st.container(border=True):
            top_header_col1, top_header_col2 = st.columns([3, 1])
            with top_header_col1:
                st.markdown('<div class="nusa-priority-title">#1 Research Priority</div>', unsafe_allow_html=True)
            with top_header_col2:
                st.markdown(
                    f'<span class="nusa-badge nusa-badge-live">✓ {len(ranked_rows)} Banks Screened</span>',
                    unsafe_allow_html=True,
                )
            hero_left, hero_score, hero_driver = st.columns([2.2, 1, 1.5])
            with hero_left:
                st.markdown(
                    bank_header_html(
                        str(top_row["ticker"]),
                        str(top_row.get("company_name") or "Company name unavailable"),
                        size_px=48,
                    ),
                    unsafe_allow_html=True,
                )
            with hero_score:
                st.metric("Research priority", f'{top_row["score"]} / 100')
            with hero_driver:
                st.metric("Primary driver", str(top_row["primary_driver"]).replace("_", " ").title())

            change_columns = st.columns(3)
            change_columns[0].metric(
                "Change",
                format_change(top_row.get("primary_change"), top_row.get("primary_change_unit", "")),
            )
            change_columns[1].metric(
                "Peer median",
                format_change(top_row.get("primary_peer_median"), top_row.get("primary_change_unit", "")),
            )
            change_columns[2].metric(
                "Peer deviation",
                format_change(top_row.get("primary_deviation"), top_row.get("primary_change_unit", "")),
            )

            # ── "Why this bank?" Explanation Card ──────────────────────────
            why_bullets = ins.why_this_bank(top_row, universe_size=len(ranked_rows))
            if why_bullets:
                st.markdown(f"**Why NUSA selected {top_row['ticker']}:**")
                for bullet in why_bullets:
                    st.markdown(f"- {bullet}")

            # ── Anomaly Decomposition Section ──────────────────────────────
            decomp = ins.anomaly_decomposition(top_row)
            with st.expander("Anomaly score decomposition (defensible 0–100 calculation)", expanded=False):
                st.caption(decomp.formula)
                decomp_df = pd.DataFrame(decomp.rows)[["Metric", "Change", "Peer median", "Peers", "Level", "Status"]]
                st.dataframe(decomp_df, hide_index=True, width="stretch")

            # ── Peer Context Distribution Chart ────────────────────────────
            with st.expander(f"Peer context distribution ({ins.metric_label(top_row['primary_driver'])})", expanded=False):
                dist = ins.peer_distribution(
                    selector_rows,
                    str(top_row["primary_driver"]),
                    str(top_row["ticker"]),
                )
                # Use enhanced chart visualization
                chart_ui.create_enhanced_peer_distribution_chart(dist)

            if st.button(
                f'Investigate {top_row["ticker"]}',
                key="investigate_top_result",
                type="primary",
            ):
                st.session_state["nusa_selected_ticker"] = str(top_row["ticker"])
                st.session_state["nusa_company_selector"] = str(top_row["ticker"])
                st.success("Company selected. Continue in the INVESTIGATE section.")
            excluded_flags = top_row.get("excluded_metric_flags", [])
            if excluded_flags:
                st.caption(
                    "Excluded from percentage scoring: "
                    + "; ".join(format_excluded_metric_flags([flag]) for flag in excluded_flags)
                )

        st.caption(
            "Research-priority scores identify unusual peer-relative financial changes. "
            "They are not buy/sell signals and do not imply misconduct."
        )
        deep_preview: DeepInvestigationResult | None = st.session_state.get("nusa_deep_result")
        if deep_preview and str(deep_preview.ticker) == str(top_row["ticker"]):
            deep_ui.render_deep_investigation_compact(
                deep_preview,
                selected_discovery=top_row,
                discovery_all_rows=selector_rows,
            )
        if len(selector_rows) > 1:
            # Enhanced visual hierarchy for investigation section
            st.markdown("""
                <div style="background: linear-gradient(135deg, #0F1E33 0%, #1C2D4E 100%); 
                           border: 1px solid rgba(96, 165, 250, 0.2); 
                           border-radius: 12px; 
                           padding: 20px; 
                           margin: 16px 0;">
                    <h4 style="color: #EFF6FF; margin-bottom: 8px; font-weight: 700;">
                        🎯 Where should I investigate first?
                    </h4>
                    <p style="color: #94A3B8; font-size: 14px; margin-bottom: 0;">
                        Top ranked banks with significant peer-relative deviation
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            # Add portfolio overview for better context
            chart_ui.create_portfolio_overview_chart(selector_rows)
            
            top_ranked_subset = selector_rows[:5]
            for rank_idx, r in enumerate(top_ranked_subset, start=1):
                unit_r = str(r.get("primary_change_unit", ""))
                
                # Enhanced rank card styling
                priority_level = "high" if r.get("score", 0) >= 80 else "medium" if r.get("score", 0) >= 60 else "low"
                priority_colors = {
                    "high": ("rgba(16, 185, 129, 0.15)", "#10B981", "🔥"),
                    "medium": ("rgba(245, 158, 11, 0.15)", "#F59E0B", "⚡"),
                    "low": ("rgba(107, 114, 128, 0.15)", "#6B7280", "📊")
                }
                bg_color, border_color, icon = priority_colors[priority_level]
                
                st.markdown(f"""
                    <div style="background: {bg_color}; 
                               border: 1px solid {border_color}; 
                               border-radius: 12px; 
                               padding: 20px; 
                               margin: 12px 0;
                               transition: all 0.3s ease;">
                """, unsafe_allow_html=True)
                
                with st.container():
                    r_c1, r_c2, r_c3, r_c4 = st.columns([2.5, 1, 1.2, 1])
                    with r_c1:
                        rank_logo = bank_logo_html(str(r.get("ticker", "")), size_px=36)
                        st.markdown(f"""
                            <div style="display: flex; align-items: center; gap: 12px;">
                                {rank_logo}
                                <div>
                                    <div style="font-weight: 700; font-size: 16px; color: #EFF6FF;">
                                        #{rank_idx} · {r.get('ticker')}
                                    </div>
                                    <div style="color: #94A3B8; font-size: 13px; margin-top: 2px;">
                                        {r.get('company_name') or 'Bank'}
                                    </div>
                                    <div style="color: {border_color}; font-size: 11px; font-weight: 600; 
                                               text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px;">
                                        Primary: {str(r.get('primary_driver', '')).replace('_', ' ').title()}
                                    </div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
                    
                    with r_c2:
                        st.metric("Priority", f"{r.get('score')} / 100", help=f"{priority_level.title()} priority bank")
                    with r_c3:
                        st.metric("Change", format_change(r.get("primary_change"), unit_r), help="Primary metric change")
                    with r_c4:
                        if st.button("🔍 Investigate", 
                                   key=f"investigate_rank_{r.get('ticker')}_{rank_idx}",
                                   type="primary" if priority_level == "high" else "secondary"):
                            st.session_state["nusa_selected_ticker"] = str(r.get("ticker"))
                            st.session_state["nusa_company_selector"] = str(r.get("ticker"))
                            st.success(f"🎯 {r.get('ticker')} selected for investigation!")
                            st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

            with st.expander(f"📊 View all {len(selector_rows)} banks across universe", expanded=False):
                # Enhanced table with better formatting and visual indicators
                all_rows = []
                for rank, row in enumerate(selector_rows, start=1):
                    unit = str(row.get("primary_change_unit", ""))
                    score = row.get("score", 0)
                    
                    # Priority indicators
                    if score >= 80:
                        priority_icon = "🔥"
                        priority_label = "High"
                    elif score >= 60:
                        priority_icon = "⚡"
                        priority_label = "Medium"
                    else:
                        priority_icon = "📊"
                        priority_label = "Low"
                    
                    all_rows.append(
                        {
                            "Rank": f"#{rank}",
                            "Priority": f"{priority_icon} {priority_label}",
                            "Ticker": row.get("ticker"),
                            "Company": row.get("company_name"),
                            "Score": f"{score}/100",
                            "Primary Driver": str(row.get("primary_driver", "")).replace("_", " ").title(),
                            "Change": format_change(row.get("primary_change"), unit),
                            "Peer Reference": format_change(row.get("primary_peer_median"), unit),
                        }
                    )
                
                # Display enhanced dataframe
                df_all = pd.DataFrame(all_rows)
                
                # Add custom styling
                def style_priority(s):
                    styles = []
                    for priority in s:
                        if "High" in str(priority):
                            styles.append('background-color: rgba(16, 185, 129, 0.1); color: #10B981; font-weight: 600;')
                        elif "Medium" in str(priority):
                            styles.append('background-color: rgba(245, 158, 11, 0.1); color: #F59E0B; font-weight: 600;')
                        else:
                            styles.append('background-color: rgba(107, 114, 128, 0.1); color: #6B7280; font-weight: 600;')
                    return styles
                
                styled_df = df_all.style.apply(style_priority, subset=['Priority'])
                st.dataframe(styled_df, hide_index=True, use_container_width=True, height=400)
                
                # Summary statistics
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    high_priority = sum(1 for row in selector_rows if row.get("score", 0) >= 80)
                    st.metric("High Priority", high_priority, help="Banks with score ≥ 80")
                
                with col2:
                    avg_score = sum(row.get("score", 0) for row in selector_rows) / len(selector_rows)
                    st.metric("Avg Score", f"{avg_score:.1f}", help="Average research priority score")
                
                with col3:
                    score_range = max(row.get("score", 0) for row in selector_rows) - min(row.get("score", 0) for row in selector_rows)
                    st.metric("Score Range", f"{score_range:.1f}", help="Range between highest and lowest scores")
                
                with col4:
                    eligible_banks = sum(1 for row in selector_rows if row.get("eligible_metric_count", 0) >= 3)
                    st.metric("Well Covered", eligible_banks, help="Banks with ≥3 scoreable metrics")

        chosen_ticker = st.selectbox(
            "Select any company for investigation",
            options=[str(row["ticker"]) for row in selector_rows],
            format_func=lambda ticker: next(
                _company_label(row) for row in selector_rows if row["ticker"] == ticker
            ),
            key="nusa_priority_ticker",
        )
        if st.button("Investigate selected bank", key="investigate_priority"):
            st.session_state["nusa_selected_ticker"] = chosen_ticker
            st.session_state["nusa_company_selector"] = chosen_ticker
            st.success("Company selected. Continue in the INVESTIGATE section.")


with investigate_tab:
    st.subheader("Investigate a bank")
    selected_discovery: dict[str, Any] | None = None
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
        selected_discovery = next(
            (
                row
                for row in st.session_state.get("nusa_discovery_rows", [])
                if row.get("ticker") == ticker
            ),
            None,
        )
        company = by_ticker[ticker]
        primary_component: dict[str, Any] = next(
            (
                component
                for component in (selected_discovery or {}).get("components", [])
                if component.get("metric") == (selected_discovery or {}).get("primary_driver")
            ),
            {},
        )
        primary_period = str(primary_component.get("period", "Annual period")).replace(
            " to ", " → "
        )
        with st.container(border=True):
            # Use enhanced investigation overview
            chart_ui.create_enhanced_investigation_overview(ticker, selected_discovery, company)
            
            if selected_discovery:
                kpi_columns = st.columns(5)
                kpi_columns[0].metric(
                    "Research priority",
                    f'{selected_discovery.get("score", "—")} / 100',
                )
                kpi_columns[1].metric(
                    "Primary driver",
                    str(selected_discovery.get("primary_driver", "—")).replace("_", " ").title(),
                )
                kpi_columns[2].metric(
                    primary_period,
                    format_change(
                        selected_discovery.get("primary_change"),
                        selected_discovery.get("primary_change_unit", ""),
                    ),
                )
                kpi_columns[3].metric(
                    "Peer median",
                    format_change(
                        selected_discovery.get("primary_peer_median"),
                        selected_discovery.get("primary_change_unit", ""),
                    ),
                )
                deep_for_ticker = st.session_state.get("nusa_deep_result")
                inv_for_ticker = st.session_state.get("nusa_investigation_result")
                if deep_for_ticker and deep_for_ticker.ticker == ticker:
                    val_stats = chart_ui.validation_from_trace(deep_for_ticker.trace.events)
                    evidence_label = (
                        f"{val_stats['validated_count']}/{val_stats['evidence_count']} validated"
                        if val_stats["evidence_count"]
                        else "—"
                    )
                elif inv_for_ticker:
                    val_stats = chart_ui.validation_from_trace(inv_for_ticker.trace.events)
                    evidence_label = (
                        f"{val_stats['validated_count']}/{val_stats['evidence_count']} validated"
                        if val_stats["evidence_count"]
                        else "—"
                    )
                else:
                    evidence_label = "Run investigation"
                kpi_columns[4].metric("Evidence verified", evidence_label)
            
            # Enhanced "Why flagged" section
            if selected_discovery:
                why_p = ins.why_flagged_paragraph(selected_discovery)
                if why_p:
                    st.markdown("""
                        <div style="background: rgba(245, 158, 11, 0.08); 
                                   border-left: 4px solid #F59E0B; 
                                   border-radius: 8px; 
                                   padding: 16px; 
                                   margin: 16px 0;">
                            <h4 style="color: #F59E0B; margin: 0 0 8px 0; font-size: 14px; 
                                      font-weight: 700; text-transform: uppercase;">
                                🚨 Why NUSA Flagged This Bank
                            </h4>
                    """, unsafe_allow_html=True)
                    st.write(why_p)
                    st.markdown('</div>', unsafe_allow_html=True)

        if source_mode == "demo" and st.button(
            "Example comparison: this change with DEMOBANK2 and DEMOBANK3",
            key="demo_comparison_example",
        ):
            st.session_state["nusa_research_question"] = (
                "Compare this change with DEMOBANK2 and DEMOBANK3."
            )
        # ── 2. Investigation Questions Engine ──────────────────────────
        if selected_discovery:
            auto_questions = ins.investigation_questions(selected_discovery)
            if auto_questions:
                with st.expander("💡 Bounded research questions & deterministic findings", expanded=False):
                    st.caption("Engineered from observed anomaly components — no external LLM required.")
                    for q in auto_questions:
                        st.markdown(f"**Q: {q.question}**")
                        st.write(q.answer)

        question = st.text_input(
            "Research question",
            placeholder=f"e.g. Investigate {ticker} · or select a suggested question above",
            key="nusa_research_question",
        )
        run_research = st.button("Run investigation", type="primary", key="run_investigation")
        run_deep = st.button(
            "🤖 Run autonomous deep investigation",
            key="run_deep_investigation",
            help=(
                "The agent selects size-matched peers automatically, "
                "decides which metrics to compare and why, "
                "and stops when evidence is sufficient — no LLM required."
            ),
        )
        run_followup = st.button(
            "Run follow-up peer comparison",
            key="run_followup_comparison",
            disabled=(
                (
                    st.session_state.get("nusa_investigation_result") is None
                    and st.session_state.get("nusa_deep_result") is None
                )
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
                research_request = question.strip() or f"Investigate {ticker}"
                with st.spinner("Running the evidence-led research workflow…"):
                    result = orchestrator.run(research_request)
                st.session_state["nusa_investigation_result"] = result
                st.session_state["nusa_investigation_report"] = result.synthesis
                st.session_state.pop("nusa_followup_result", None)
                st.session_state.pop("nusa_deep_result", None)
                _set_status(asdict(_provider(source_mode).status))
            except Exception as error:
                failed_status = asdict(_provider(source_mode).status)
                _set_status(failed_status)
                _show_action_error(
                    f"The investigation could not be completed ({type(error).__name__}). "
                    "Review the data-source status; no fabricated fallback data was used.",
                    error,
                )
                if failed_status.get("warning"):
                    st.caption(f"Source status: {failed_status['warning']}")

        if run_deep:
            try:
                discovery_rows = st.session_state.get("nusa_discovery_rows") or []
                synthesizer = LLMResearchSynthesizer(create_llm_provider_from_env())
                deep_orchestrator = DeepInvestigationOrchestrator(
                    _provider(source_mode),
                    synthesizer=synthesizer,
                )
                with st.spinner(
                    "🤖 Autonomous agent: observe → decide → act… "
                    "selecting peers, comparing metrics, validating evidence…"
                ):
                    deep_result = deep_orchestrator.run_deep(ticker, discovery_rows)
                st.session_state["nusa_deep_result"] = deep_result
                st.session_state["nusa_investigation_result"] = None
                st.session_state.pop("nusa_followup_result", None)
                _set_status(asdict(_provider(source_mode).status))
            except Exception as error:
                failed_status = asdict(_provider(source_mode).status)
                _set_status(failed_status)
                _show_action_error(
                    f"Deep investigation could not be completed ({type(error).__name__}). "
                    "No fabricated fallback data was used.",
                    error,
                )
                if failed_status.get("warning"):
                    st.caption(f"Source status: {failed_status['warning']}")


        if run_followup:
            try:
                # ── Try deterministic structured answer first ──────────────
                discovery_rows_list = st.session_state.get("nusa_discovery_rows") or []
                active_evidence = (
                    list(st.session_state.get("nusa_deep_result").evidence_ledger)
                    if st.session_state.get("nusa_deep_result")
                    else list(st.session_state.get("nusa_investigation_result").evidence_ledger)
                    if st.session_state.get("nusa_investigation_result")
                    else []
                )
                selected_peers = (
                    st.session_state.get("nusa_deep_result").peer_tickers_selected
                    if st.session_state.get("nusa_deep_result")
                    else []
                )
                struct_ans = ins.answer_structured_followup(
                    question,
                    selected_discovery,
                    ranked_rows=discovery_rows_list,
                    evidence_items=active_evidence,
                    peers=selected_peers,
                )
                if struct_ans is not None:
                    st.session_state["nusa_structured_followup_answer"] = struct_ans
                    st.session_state.pop("nusa_followup_result", None)
                else:
                    memory = ResearchSessionMemory.from_session_state(st.session_state)
                    orchestrator = ResearchOrchestrator(
                        _provider(source_mode),
                        synthesizer=LLMResearchSynthesizer(create_llm_provider_from_env()),
                        session_memory=memory,
                    )
                    with st.spinner("Resolving the follow-up from session memory…"):
                        followup_result = orchestrator.run(question)
                    st.session_state["nusa_followup_result"] = followup_result
                    st.session_state.pop("nusa_structured_followup_answer", None)
                _set_status(asdict(_provider(source_mode).status))
            except Exception as error:
                _show_action_error(
                    f"The follow-up could not be completed ({type(error).__name__}). "
                    "It requires an existing investigation with validated metric evidence.",
                    error,
                )

    # ── Enhanced Deep investigation result (autonomous agent) ─────────────────
    deep_result: DeepInvestigationResult | None = st.session_state.get("nusa_deep_result")
    if deep_result is not None:
        if selected_discovery is None and deep_result.ticker:
            selected_discovery = next(
                (
                    row
                    for row in st.session_state.get("nusa_discovery_rows", [])
                    if row.get("ticker") == deep_result.ticker
                ),
                None,
            )
        
        # Add enhanced research summary for deep investigation
        chart_ui.create_enhanced_research_summary_table(
            deep_result=deep_result,
            selected_discovery=selected_discovery
        )
        
        # Enhanced evidence visualization for deep investigation
        if hasattr(deep_result, 'evidence_ledger') and deep_result.evidence_ledger:
            chart_ui.create_enhanced_evidence_visualization(
                deep_result.evidence_ledger, 
                deep_result.ticker
            )
        
        # Original detailed deep investigation results
        with st.expander("🤖 Detailed Autonomous Investigation Results", expanded=False):
            deep_ui.render_deep_investigation_results(
                deep_result,
                selected_discovery=selected_discovery,
                discovery_all_rows=st.session_state.get("nusa_discovery_rows") or [],
                widget_key_prefix="investigate_",
            )

    # ── Standard investigation result ─────────────────────────────────────────
    result = st.session_state.get("nusa_investigation_result")
    if result is not None:
        events = {event.event for event in result.trace.events}
        validation_event = next(
            (event for event in result.trace.events if event.event == "EVIDENCE_VALIDATED"),
            None,
        )
        evidence_validated = bool(
            validation_event and validation_event.details.get("valid", False)
        )
        plan_event = next(
            (e for e in result.trace.events if e.event == "PLAN_CREATED"), None
        )
        used_llm_planner = bool(plan_event and plan_event.details.get("planner") == "llm")
        synth_event = next(
            (e for e in result.trace.events if e.event == "SYNTHESIS_COMPLETED"), None
        )
        used_llm_synth = bool(
            synth_event and synth_event.details.get("generation_mode") == "llm"
        )
        stages = [
            ("Understanding request", "INTENT_RESOLVED" in events),
            (
                "Research plan created"
                + (" · LLM planner (validated)" if used_llm_planner else " · deterministic"),
                "PLAN_VALIDATED" in events,
            ),
            ("Retrieving evidence", "TOOL_COMPLETED" in events),
            ("Running quantitative analysis", "ANALYSIS_COMPLETED" in events),
            ("Comparing peers", "compare_peer_metrics" in result.outputs),
            ("Validating evidence", "EVIDENCE_VALIDATED" in events),
            (
                "Generating research report"
                + (" · LLM synthesis" if used_llm_synth else " · deterministic template"),
                "SYNTHESIS_COMPLETED" in events,
            ),
        ]
        st.markdown("#### 📊 Enhanced Investigation Analysis")
        evidence_items = list(result.evidence_ledger)
        if not evidence_items:
            st.info("No validated anomaly evidence was available for this company.")
        else:
            # Enhanced evidence visualization with tabs
            chart_ui.create_enhanced_evidence_visualization(evidence_items, ticker)
            
            # Enhanced research summary table
            chart_ui.create_enhanced_research_summary_table(
                investigation_result=result,
                selected_discovery=selected_discovery
            )
            
            # Traditional evidence ledger (enhanced)
            st.markdown("#### Evidence ledger")
            metrics = list(dict.fromkeys(item.metric for item in evidence_items))
            metric = st.selectbox("Metric", metrics, key="nusa_metric_chart")
            selected_evidence = [item for item in evidence_items if item.metric == metric]
            with st.expander(f"📈 Metric charts ({metric})", expanded=False):
                for item in selected_evidence:
                    st.markdown(f"**{item.ticker} · {item.metric} · {item.period}**")
                    # Use enhanced metric history chart
                    chart_ui.create_enhanced_metric_history_chart(
                        previous_value=item.previous_value,
                        current_value=item.current_value,
                        period=item.period,
                        metric=item.metric,
                        data_mode=item.data_mode,
                        ticker=item.ticker
                    )
                    if item.scoring_eligible:
                        # Enhanced peer comparison visualization
                        st.markdown("##### Peer Comparison")
                        comparison_data = [{
                            "ticker": item.ticker,
                            "change": item.change,
                            "change_unit": item.change_unit,
                            "peer_median": item.peer_median,
                            "deviation": item.deviation
                        }]
                        chart_ui.create_enhanced_comparison_chart(
                            comparison_data, 
                            item.metric,
                            f"{item.ticker} vs Peers"
                        )
                    else:
                        st.caption(
                            f"Not scored: {item.exclusion_reason}. Percentage change excluded from scoring."
                        )

                for item in evidence_items:
                    metric_label = item.metric.replace("_", " ").title()
                    with st.container(border=True):
                        heading_left, heading_right = st.columns([3, 1])
                        with heading_left:
                            st.markdown(
                                f'<div class="nusa-evidence-title">{escape(metric_label)}</div>',
                                unsafe_allow_html=True,
                            )
                            st.caption(f"{item.ticker} · {item.period}")
                        with heading_right:
                            if evidence_validated:
                                st.success("Evidence verified", icon="✅")
                            else:
                                st.warning("Validation status unavailable", icon="⚠️")
                        value_columns = st.columns(4)
                        start_period, end_period = item.period.split(" to ")
                        value_columns[0].metric(
                            start_period,
                            format_evidence_value(
                                item.previous_value, item.metric, data_mode=item.data_mode
                            ),
                        )
                        value_columns[1].metric(
                            end_period,
                            format_evidence_value(
                                item.current_value, item.metric, data_mode=item.data_mode
                            ),
                        )
                        value_columns[2].metric(
                            "Change",
                            format_change(item.change, item.change_unit),
                        )
                        value_columns[3].metric(
                            "Peer median",
                            format_change(item.peer_median, item.change_unit),
                        )
                        deviation_label = format_change(item.deviation, item.change_unit)
                        source_label = str(item.source)
                        if item.data_mode == "cached":
                            source_label = "SECTORS CACHED SNAPSHOT"
                        elif item.data_mode == "demo":
                            source_label = "DEMO/SAMPLE DATA"
                        st.caption(
                            f"Deviation {deviation_label} · {item.peer_count} peers · "
                            f"{source_label} · {format_retrieved_date(item.retrieved_at)}"
                        )
                components = [
                    {
                        "Ticker": item.ticker,
                        "Metric": item.metric,
                        "Period": item.period,
                        f"Change ({unit_label(item.change_unit)})": item.change,
                        f"Peer median ({unit_label(item.change_unit)})": item.peer_median,
                        "Peers": item.peer_count,
                        f"Deviation ({unit_label(item.change_unit)})": item.deviation,
                        "Scoring eligible": item.scoring_eligible,
                        "Exclusion reason": item.exclusion_reason,
                        "Evidence ID": item.evidence_id,
                    }
                    for item in evidence_items
                ]
                with st.expander("📊 Anomaly components breakdown", expanded=False):
                    df_components = pd.DataFrame(components)
                    
                    # Enhanced styling for components table
                    def style_eligibility(s):
                        styles = []
                        for eligible in s:
                            if eligible:
                                styles.append('background-color: rgba(16, 185, 129, 0.1); color: #10B981;')
                            else:
                                styles.append('background-color: rgba(245, 158, 11, 0.1); color: #F59E0B;')
                        return styles
                    
                    styled_components = df_components.style.apply(style_eligibility, subset=['Scoring eligible'])
                    st.dataframe(styled_components, hide_index=True, use_container_width=True)

        # Enhanced peer comparison section
        comparison = result.outputs.get("compare_peer_metrics")
        st.markdown("#### 🎯 Enhanced Peer Comparison")
        if comparison and comparison.value.get("comparisons"):
            # Use enhanced comparison visualization
            chart_ui.create_enhanced_comparison_chart(
                comparison.value["comparisons"],
                "peer_comparison",
                "Comprehensive Peer Analysis"
            )
        else:
            st.info(
                "Peer comparison is limited to the peer baseline recorded in the evidence ledger."
            )

        # Enhanced research summary section
        report = st.session_state.get("nusa_investigation_report", result.synthesis)
        st.markdown("#### 📝 Research Summary & Insights")
        
        # Create enhanced summary container
        st.markdown("""
            <div style="background: linear-gradient(135deg, #0F1E33 0%, #1C2D4E 100%); 
                       border: 1px solid rgba(96, 165, 250, 0.2); 
                       border-radius: 12px; 
                       padding: 24px; 
                       margin: 20px 0;">
        """, unsafe_allow_html=True)
        
        with st.container():
            st.markdown("""
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                    <div style="background: #3B82F6; width: 40px; height: 40px; border-radius: 8px; 
                               display: flex; align-items: center; justify-content: center; color: white; 
                               font-size: 18px;">📋</div>
                    <div>
                        <h4 style="color: #EFF6FF; margin: 0; font-weight: 700;">Executive Summary</h4>
                        <p style="color: #94A3B8; margin: 4px 0 0 0; font-size: 12px; text-transform: uppercase; 
                                  letter-spacing: 0.05em;">Evidence-grounded • Validated financial claims</p>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.write(report.executive_summary)
            
            # Enhanced report sections with tabs
            tab_findings, tab_context, tab_limitations = st.tabs([
                "🔍 Key Findings", 
                "📊 Analysis Context", 
                "⚠️ Limitations"
            ])
            
            with tab_findings:
                if report.key_findings:
                    for i, finding in enumerate(report.key_findings, 1):
                        st.markdown(f"""
                            <div style="background: rgba(16, 185, 129, 0.05); 
                                       border-left: 3px solid #10B981; 
                                       padding: 12px; margin: 8px 0; border-radius: 6px;">
                                <strong style="color: #10B981;">Finding #{i}:</strong> {finding}
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No specific findings highlighted in the analysis.")
            
            with tab_context:
                context_sections = [
                    ("📈 Historical Context", report.historical_context),
                    ("🏦 Peer Comparison", report.peer_comparison),
                    ("🚨 Why Flagged", report.why_flagged),
                ]
                
                for heading, lines in context_sections:
                    if lines:
                        st.markdown(f"**{heading}**")
                        for line in lines:
                            st.markdown(f"- {line}")
                        st.markdown("")
            
            with tab_limitations:
                if report.limitations:
                    for limitation in report.limitations:
                        st.markdown(f"""
                            <div style="background: rgba(245, 158, 11, 0.05); 
                                       border-left: 3px solid #F59E0B; 
                                       padding: 12px; margin: 8px 0; border-radius: 6px;">
                                <strong style="color: #F59E0B;">⚠️</strong> {limitation}
                            </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("No specific limitations noted in this analysis.")
        
        st.markdown('</div>', unsafe_allow_html=True)
        if report.evidence_references:
            st.caption("Evidence references: " + ", ".join(report.evidence_references))
        st.caption("Research context only — not investment advice.")

        import datetime as _dt2
        std_brief = [
            "# NUSA Intelligence — Research Brief",
            f"**Ticker:** {result.resolved_intent.tickers[0] if result.resolved_intent.tickers else '—'}",
            f"**Generated:** {_dt2.datetime.now().strftime('%Y-%m-%d %H:%M')} WIB",
            "**Mode:** Standard bounded-autonomy investigation",
            f"**Synthesis:** {report.generation_mode}",
            "",
            "## Executive Summary",
            report.executive_summary or "—",
        ]
        for heading, lines in [
            ("Key findings", report.key_findings),
            ("Historical context", report.historical_context),
            ("Peer comparison", report.peer_comparison),
            ("Why flagged", report.why_flagged),
            ("Limitations", report.limitations),
        ]:
            std_brief.append(f"\n## {heading}")
            std_brief += [f"- {line}" for line in lines] if lines else ["—"]
        std_brief += [
            "\n## Evidence References",
            ", ".join(report.evidence_references) if report.evidence_references else "—",
            "\n---",
            "*Research context only — not investment advice.*",
            "*NUSA Intelligence · Sectors Hackathon 2026, Track 01 — AI Agents & Assistants*",
        ]
        brief_ticker = (
            result.resolved_intent.tickers[0].replace(".", "_")
            if result.resolved_intent.tickers
            else "research"
        )
        st.markdown("#### Research workflow")
        with st.expander("Agent execution stages & research plan", expanded=False):
            for label, complete in stages:
                marker = "✓" if complete else "○"
                marker_label = "Complete" if complete else "Pending"
                st.markdown(f"**{marker}** &nbsp; {label} &nbsp; · &nbsp; {marker_label}")
            st.divider()
            st.caption("Full research plan (JSON):")
            st.json(result.plan.to_dict())

        st.download_button(
            label="⬇ Download research brief (Markdown)",
            data="\n".join(std_brief),
            file_name=f"nusa_brief_{brief_ticker}.md",
            mime="text/markdown",
            key="download_std_brief",
        )

        # Enhanced structured followup answers
        struct_followup_ans = st.session_state.get("nusa_structured_followup_answer")
        if struct_followup_ans is not None:
            st.markdown(f"""
                <div style="background: linear-gradient(135deg, #8B5CF6 0%, #A78BFA 100%); 
                           border-radius: 12px; padding: 20px; margin: 16px 0; color: white;">
                    <h4 style="color: white; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
                        💬 Follow-up Insight: {struct_followup_ans.title}
                    </h4>
                    <p style="color: rgba(255,255,255,0.8); font-size: 12px; margin-bottom: 16px;">
                        Resolved deterministically from structured state • Intent: {struct_followup_ans.intent}
                    </p>
                </div>
            """, unsafe_allow_html=True)
            
            with st.container(border=True):
                for ln in struct_followup_ans.lines:
                    st.markdown(f"- {ln}")

        # Enhanced followup comparison results
        followup_result = st.session_state.get("nusa_followup_result")
        if followup_result is not None:
            comparison_output = followup_result.outputs.get("compare_peer_metrics")
            st.markdown("#### Follow-up peer comparison")
            
            st.markdown(f"""
                <div style="background: rgba(6, 182, 212, 0.1); border-left: 4px solid #06B6D4; 
                           padding: 16px; margin: 12px 0; border-radius: 8px;">
                    <strong style="color: #06B6D4;">Session Context:</strong> 
                    {', '.join(followup_result.plan.tickers)} • 
                    Metric: {followup_result.plan.tasks[0].arguments.get('metric', 'not specified')}
                </div>
            """, unsafe_allow_html=True)
            
            if comparison_output and comparison_output.value.get("comparisons"):
                # Enhanced comparison visualization
                chart_ui.create_enhanced_comparison_chart(
                    comparison_output.value["comparisons"],
                    followup_result.plan.tasks[0].arguments.get('metric', 'comparison'),
                    "Follow-up Peer Comparison Analysis"
                )
                
                # Enhanced summary
                st.markdown(f"""
                    <div style="background: rgba(16, 185, 129, 0.1); border-left: 4px solid #10B981; 
                               padding: 16px; margin: 12px 0; border-radius: 8px;">
                        <strong style="color: #10B981;">Analysis Summary:</strong><br>
                        {followup_result.synthesis.executive_summary}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("No validated comparison evidence was available for the requested peers.")


with banks_tab:
    st.subheader("🏛️ Indonesian Banking Universe")
    st.caption(
        "Complete coverage of 48 commercial banks on the Indonesia Stock Exchange (IDX) with vector brand identities."
    )

    all_banks: list[dict[str, Any]] = []
    try:
        universe_rows, _ = _cached_universe(
            source_mode, st.session_state.get("nusa_cache_version", 0)
        )
        all_banks = universe_rows
    except Exception as exc:
        _show_action_error("Could not load bank universe", exc)
        all_banks = []

    if not all_banks:
        st.info("No bank records available in the current data source mode.")
    else:
        # Summary KPI cards
        b_c1, b_c2, b_c3, b_c4 = st.columns(4)
        with b_c1:
            st.metric("Total Banks", len(all_banks), help="All banks currently covered in this data source")
        with b_c2:
            st.metric("Vector Brand Logos", f"{len(all_banks)} / {len(all_banks)}", help="Handcrafted SVG vector logos loaded")
        with b_c3:
            st.metric("Stock Exchange", "IDX (Indonesia)", help="Listed on Indonesia Stock Exchange")
        with b_c4:
            st.metric("Grid Layout", f"{min(len(all_banks), 48)} Banks (12 × 4)", help="12 rows × 4 columns responsive layout")

        # Search filter
        search_filter = st.text_input(
            "Filter banks",
            placeholder="Search by ticker or company name (e.g. BBCA, Superbank, BMRI, Krom)...",
            key="banks_tab_search_filter",
        )

        filtered_banks = all_banks
        if search_filter.strip():
            query_lower = search_filter.strip().lower()
            filtered_banks = [
                b for b in all_banks
                if query_lower in str(b.get("ticker", "")).lower()
                or query_lower in str(b.get("company_name", "")).lower()
            ]
            st.caption(f"Showing **{len(filtered_banks)}** of **{len(all_banks)}** banks matching '{search_filter.strip()}'")

        # Grid of 4 columns across rows (12 rows for 48 banks)
        for row_start in range(0, len(filtered_banks), 4):
            row_items = filtered_banks[row_start : row_start + 4]
            cols = st.columns(4)
            for c_idx, bank_data in enumerate(row_items):
                with cols[c_idx]:
                    with st.container(border=True):
                        ticker = str(bank_data.get("ticker", "—"))
                        name = str(bank_data.get("company_name", "—"))
                        mkt_cap = bank_data.get("market_cap")

                        logo_markup = bank_logo_html(ticker, size_px=48)
                        mkt_cap_text = f"Mkt Cap: {format_idr_value(mkt_cap)}" if mkt_cap else "Commercial Bank"

                        st.markdown(
                            f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
                            f'{logo_markup}'
                            f'<div style="overflow:hidden;">'
                            f'<div style="font-weight:800;font-size:15px;color:#EFF6FF;letter-spacing:-0.02em;">{escape(ticker)}</div>'
                            f'<div style="font-size:11px;color:#94A3B8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:180px;" title="{escape(name)}">{escape(name)}</div>'
                            f'</div>'
                            f'</div>'
                            f'<div style="font-size:11px;color:#60A5FA;font-weight:600;margin-bottom:10px;">{escape(mkt_cap_text)}</div>',
                            unsafe_allow_html=True,
                        )

                        if st.button("Investigate →", key=f"inv_btn_grid_{ticker}_{row_start}_{c_idx}", use_container_width=True):
                            st.session_state["nusa_selected_ticker"] = ticker
                            st.session_state["nusa_company_selector"] = ticker
                            st.success(f"Selected **{ticker}**! Open the **INVESTIGATE** tab above to view deep findings.")


with methodology_tab:
    st.subheader("Methodology and evidence standards")
    st.write("Transparent calculations, explicit provenance, and clear data limitations.")
    method_cards = [
        (
            "Data source",
            "LIVE SECTORS reads the authenticated API; SECTORS CACHED SNAPSHOT is local Sectors-origin data and is not a live refresh; DEMO/SAMPLE is synthetic and not current market data. Modes never substitute for one another.",
        ),
        (
            "Metrics and changes",
            "The real-data score covers annual earnings, net interest income, total assets, total equity, and ROA. Monetary changes use (current − previous) / abs(previous) × 100; ROA uses percentage-point change.",
        ),
        (
            "Eligibility and peer reference",
            "Sign transitions, zero prior values, and small prior bases are flagged and excluded from conventional percentage scoring. Eligible metrics use leave-one-out peer medians and percentile deviation contributions.",
        ),
        (
            "Research-priority score",
            "A transparent 0–100 composite summarizes peer-relative deviation and eligible-metric coverage. It is deterministic Python analysis; no black-box anomaly ML model is used.",
        ),
        (
            "Evidence validation",
            "The ledger retains the metric, values, period, calculation, source endpoint, retrieval time, and data mode. Synthesis receives validated evidence; missing values remain missing.",
        ),
        (
            "Data Lineage & Provenance",
            "Sectors API → Raw Response Cache → Normalization → Peer Percentile Scoring → Evidence Ledger → Evidence Validator → Research Brief. Original timestamps and endpoints are strictly recorded.",
        ),
        (
            "Error-State & Reliability Guarantee",
            "NUSA never falls back to synthetic data. If a detailed Sectors company-report request is unavailable, it may continue using already-retrieved Sectors Screener evidence and explicitly marks the degraded source path.",
        ),
        (
            "Interpretation",
            "A research-priority anomaly is not proof of misconduct or fraud, and it is not a buy/sell signal. NUSA does not provide personalized investment advice.",
        ),
    ]
    for index in range(0, len(method_cards), 2):
        card_columns = st.columns(2)
        for column, (title, body) in zip(card_columns, method_cards[index : index + 2]):
            with column:
                with st.container(border=True):
                    st.markdown(f"#### {title}")
                    st.write(body)
