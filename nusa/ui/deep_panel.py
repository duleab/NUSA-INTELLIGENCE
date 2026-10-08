"""Streamlit rendering for autonomous deep-investigation results."""

from __future__ import annotations

import datetime as dt
from typing import Any

import pandas as pd
import streamlit as st

from nusa.agent.orchestration import DeepInvestigationResult
from nusa.ui import charts as chart_ui
from nusa.ui import insights as ins
from nusa.ui.presentation import format_change, format_evidence_value


def render_peer_comparison_block(
    *,
    discovery_all_rows: list[dict[str, Any]],
    primary_drv: str,
    ticker: str,
    peer_tickers: list[str],
    heading: str | None = None,
) -> None:
    """Enhanced peer bar chart + readable comparison table with professional styling."""
    if not discovery_all_rows:
        return
    title = heading or f"How unusual is this change? ({ins.metric_label(primary_drv)})"
    st.markdown(f"#### {title}")
    peer_dist = ins.peer_distribution(
        discovery_all_rows,
        primary_drv,
        ticker,
        peers=peer_tickers,
    )
    
    # Use enhanced chart visualization
    chart_ui.create_enhanced_peer_distribution_chart(peer_dist)
    
    if peer_tickers:
        st.caption(f"Size-matched peers: {', '.join(peer_tickers)}")


def render_deep_investigation_compact(
    deep_result: DeepInvestigationResult,
    *,
    selected_discovery: dict[str, Any] | None,
    discovery_all_rows: list[dict[str, Any]],
) -> None:
    """Summary on DISCOVER after judge demo — no duplicate download/history widgets."""
    validation = chart_ui.validation_from_trace(deep_result.trace.events)
    with st.container(border=True):
        st.markdown("#### Autonomous investigation complete")
        st.caption(
            f"**{deep_result.ticker}** · {len(deep_result.decisions)} agent steps · "
            f"{validation['validated_count']}/{validation['evidence_count']} evidence records validated"
        )
        if selected_discovery:
            st.markdown(f"**Key takeaway:** *{ins.generate_hero_sentence(selected_discovery)}*")
        primary_drv = str(
            (selected_discovery or {}).get("primary_driver")
            or (deep_result.evidence_ledger[0].metric if deep_result.evidence_ledger else "net_interest_income")
        )
        render_peer_comparison_block(
            discovery_all_rows=discovery_all_rows,
            primary_drv=primary_drv,
            ticker=deep_result.ticker,
            peer_tickers=list(deep_result.peer_tickers_selected),
            heading=f"Peer context ({ins.metric_label(primary_drv)})",
        )
        bullets = ins.research_summary_bullets(selected_discovery)
        if bullets:
            for line in bullets[:3]:
                st.markdown(f"- {line}")
        st.info(
            "Open the **INVESTIGATE** tab for evidence cards, agent decision log, "
            "and the downloadable research brief."
        )


def render_deep_investigation_results(
    deep_result: DeepInvestigationResult,
    *,
    selected_discovery: dict[str, Any] | None,
    discovery_all_rows: list[dict[str, Any]],
    widget_key_prefix: str = "",
) -> None:
    """Full deep-investigation panel (INVESTIGATE tab)."""
    deep_evidence = list(deep_result.evidence_ledger)
    validation = chart_ui.validation_from_trace(deep_result.trace.events)
    deep_validated = bool(validation["valid"])

    if selected_discovery:
        three_panel = ins.what_changed_panel(selected_discovery)
        if three_panel:
            st.markdown("#### Key Investigation Insights")
            p_c1, p_c2, p_c3 = st.columns(3)
            validated_line = (
                f"{validation['validated_count']}/{validation['evidence_count']} evidence records validated"
                if validation["evidence_count"]
                else "No evidence records collected"
            )
            with p_c1:
                with st.container(border=True):
                    st.markdown("**1. What Changed**")
                    st.markdown(f"### {three_panel['what_changed']}")
                    st.caption(f"Period: {three_panel['period']}")
                    for supp in three_panel["supporting"][:3]:
                        st.caption(f"• {supp}")
            with p_c2:
                with st.container(border=True):
                    st.markdown("**2. Why It Is Unusual**")
                    st.markdown(f"### {three_panel['why_unusual']}")
                    st.caption("Leave-one-out peer reference")
                    st.caption("Peer-relative divergence across the bank universe")
            with p_c3:
                with st.container(border=True):
                    st.markdown("**3. What NUSA Did**")
                    st.markdown(f"### {len(deep_result.decisions)} Autonomous Steps")
                    st.caption(
                        f"Peers evaluated: {', '.join(deep_result.peer_tickers_selected) or 'Size-matched'}"
                    )
                    st.caption(validated_line)

    primary_drv = str(
        (selected_discovery or {}).get("primary_driver")
        or (deep_result.evidence_ledger[0].metric if deep_result.evidence_ledger else "net_interest_income")
    )
    render_peer_comparison_block(
        discovery_all_rows=discovery_all_rows,
        primary_drv=primary_drv,
        ticker=deep_result.ticker,
        peer_tickers=list(deep_result.peer_tickers_selected),
    )

    st.markdown("#### Research Summary")
    sum_bullets = ins.research_summary_bullets(selected_discovery)
    if sum_bullets:
        with st.container(border=True):
            for b_text in sum_bullets:
                st.markdown(f"- {b_text}")
    else:
        deep_report = deep_result.synthesis
        with st.container(border=True):
            st.write(deep_report.executive_summary)
            for line in deep_report.key_findings or []:
                st.markdown(f"- {line}")

    if deep_evidence:
        st.markdown("#### Validated Evidence Records")
        subject_evidence = [item for item in deep_evidence if item.ticker == deep_result.ticker]
        if not subject_evidence:
            subject_evidence = deep_evidence
        peer_evidence = [item for item in deep_evidence if item.ticker != deep_result.ticker]

        for i in range(0, len(subject_evidence), 2):
            grid_cols = st.columns(2)
            for col_idx, item in enumerate(subject_evidence[i : i + 2]):
                with grid_cols[col_idx]:
                    m_label = item.metric.replace("_", " ").title()
                    with st.container(border=True):
                        card_hdr_left, card_hdr_right = st.columns([3, 1])
                        with card_hdr_left:
                            st.markdown(f"**{m_label}** · {item.ticker}")
                            st.caption(item.period)
                        with card_hdr_right:
                            if deep_validated and validation["invalid_count"] == 0:
                                st.success("Verified", icon="✅")
                            elif deep_validated:
                                st.warning("Partial", icon="⚠️")
                            else:
                                st.info("Reported", icon="ℹ️")
                        card_cols = st.columns(4)
                        p_start, p_end = item.period.split(" to ")
                        card_cols[0].metric(
                            p_start,
                            format_evidence_value(item.previous_value, item.metric, data_mode=item.data_mode),
                        )
                        card_cols[1].metric(
                            p_end,
                            format_evidence_value(item.current_value, item.metric, data_mode=item.data_mode),
                        )
                        card_cols[2].metric("Change", format_change(item.change, item.change_unit))
                        card_cols[3].metric("Peer median", format_change(item.peer_median, item.change_unit))
                        st.caption(
                            f"Peer deviation: {format_change(item.deviation, item.change_unit)} · "
                            f"{item.peer_count} peers · Source: {item.source}"
                        )

        if peer_evidence:
            with st.expander(f"📋 Peer benchmark evidence records ({len(peer_evidence)} records)", expanded=False):
                peer_table = [
                    {
                        "Peer Ticker": item.ticker,
                        "Metric": item.metric.replace("_", " ").title(),
                        "Period": item.period,
                        "Prior Value": format_evidence_value(item.previous_value, item.metric, data_mode=item.data_mode),
                        "Current Value": format_evidence_value(item.current_value, item.metric, data_mode=item.data_mode),
                        "Change": format_change(item.change, item.change_unit),
                        "Status": "Verified ✅" if deep_validated else "Reported",
                    }
                    for item in peer_evidence
                ]
                st.dataframe(pd.DataFrame(peer_table), hide_index=True, width="stretch")

    if deep_evidence:
        st.markdown("#### Historical Context")
        d_metrics = list(dict.fromkeys(item.metric for item in deep_evidence))
        d_metric = st.selectbox(
            "Inspect metric history",
            d_metrics,
            key=f"{widget_key_prefix}nusa_deep_metric_chart",
        )
        for item in [e for e in deep_evidence if e.metric == d_metric]:
            # Use enhanced metric history chart
            chart_ui.create_enhanced_metric_history_chart(
                previous_value=item.previous_value,
                current_value=item.current_value,
                period=item.period,
                metric=item.metric,
                data_mode=item.data_mode,
                ticker=item.ticker
            )

    next_qs = ins.investigate_next_questions(selected_discovery)
    if next_qs:
        st.markdown("#### What to Investigate Next")
        with st.container(border=True):
            for q_num, q_txt in enumerate(next_qs, 1):
                st.markdown(f"**{q_num}.** {q_txt}")

    cov = ins.evidence_coverage(
        deep_evidence,
        ticker=deep_result.ticker,
        validated=deep_validated,
        invalid_count=int(validation["invalid_count"]),
        universe_size=len(discovery_all_rows),
        source_label=str(deep_evidence[0].source) if deep_evidence else None,
    )
    st.markdown("#### Evidence Strength & Verification")
    ec_cols = st.columns(4)
    ec_cols[0].metric(
        "Evidence records",
        f"{cov['records_validated']} / {cov['records_total']} validated",
    )
    ec_cols[1].metric("Peer universe", f"{cov['universe_size'] or '—'} banks")
    ec_cols[2].metric("Coverage period", cov["period_label"])
    ec_cols[3].metric("Failed checks", str(int(validation["invalid_count"])))
    if cov["all_validated"]:
        st.caption(
            "All collected evidence passed deterministic validation — "
            "reproducible math, not arbitrary AI confidence scores."
        )
    else:
        st.caption(
            "Validation counts reflect the evidence validator; "
            "review the agent log if any checks failed."
        )

    with st.expander("🤖 How NUSA investigated (Autonomous Agent Log)", expanded=False):
        st.markdown(
            f"**Agent policy:** Observe → Compare → Corroborate → Validate → Stop<br>"
            f"Ticker: **{deep_result.ticker}** · {len(deep_result.decisions)} decisions · "
            f"Peers auto-selected: {', '.join(deep_result.peer_tickers_selected) or 'none'}",
            unsafe_allow_html=True,
        )
        for dec in deep_result.decisions:
            icon = {"RUN_TOOL": "⚡", "STOP": "🛑", "ABSTAIN": "⚠️"}.get(dec.decision, "•")
            st.markdown(
                f"**Step {dec.step} &nbsp;{icon} {dec.decision}**"
                f"{'&nbsp; `' + dec.tool + '`' if dec.tool else ''}"
            )
            st.caption(f"Observed: {dec.observation}")
            st.markdown(f"*Reason: {dec.reason}*")
        st.divider()
        st.markdown("**Verifiable Audit Trail:**")
        audit_steps = ins.audit_trail(
            universe_size=cov["universe_size"],
            metric_count=5,
            ranked_rows=discovery_all_rows,
            ticker=deep_result.ticker,
            trace_events=deep_result.trace.events,
        )
        for step_title, step_desc in audit_steps:
            st.markdown(f"✓ **{step_title}:** {step_desc}")

    with st.container(border=True):
        st.markdown("##### Research Limitations")
        st.caption("• Analysis is based on annual financial figures from the Sectors Screener snapshot.")
        st.caption("• Intra-year, quarterly, and qualitative factors are not reflected in this view.")
        st.caption("• Peer medians reflect reporting banks in the bounded 48-bank IDX universe.")
        st.caption("• Findings highlight unusual changes for research prioritization; not investment advice.")

    deep_report = deep_result.synthesis
    brief_lines = [
        "# NUSA Intelligence — Deep Research Brief",
        f"**Ticker:** {deep_result.ticker}",
        f"**Generated:** {dt.datetime.now().strftime('%Y-%m-%d %H:%M')} WIB",
        "**Agent mode:** Autonomous bounded-autonomy (deterministic policy)",
        f"**Synthesis:** {deep_report.generation_mode}",
        "",
        "## Executive Summary",
        deep_report.executive_summary or "—",
        "",
        "## Agent Decision Log",
    ]
    for dec in deep_result.decisions:
        icon = {"RUN_TOOL": "⚡", "STOP": "🛑", "ABSTAIN": "⚠️"}.get(dec.decision, "•")
        brief_lines.append(
            f"### Step {dec.step} {icon} {dec.decision}"
            + (f" · `{dec.tool}`" if dec.tool else "")
        )
        brief_lines.append(f"- **Observed:** {dec.observation}")
        brief_lines.append(f"- **Reason:** {dec.reason}")
        if dec.limitation:
            brief_lines.append(f"- ⚠️ **Limitation:** {dec.limitation}")
    brief_lines += [
        "",
        "## Key Findings",
        *[f"- {line}" for line in (deep_report.key_findings or ["—"])],
        "",
        "## Peer Comparison",
        *[f"- {line}" for line in (deep_report.peer_comparison or ["—"])],
        "",
        "## Limitations",
        *[f"- {line}" for line in (deep_report.limitations or ["—"])],
        "",
        "---",
        "*Research context only — not investment advice.*",
        "*NUSA Intelligence · Sectors Hackathon 2026, Track 01 — AI Agents & Assistants*",
    ]
    st.download_button(
        label="⬇ Download research brief (Markdown)",
        data="\n".join(brief_lines),
        file_name=f"nusa_brief_{deep_result.ticker.replace('.', '_')}.md",
        mime="text/markdown",
        key=f"{widget_key_prefix}download_deep_brief",
    )

    with st.expander("🛠️ Advanced technical details", expanded=False):
        st.markdown("**Evidence Ledger Identifiers:**")
        for item in deep_evidence:
            st.caption(f"`{item.evidence_id}` · {item.metric} · {item.source}")
        st.markdown("**Trace Event Log:**")
        st.json(
            [
                {"event": event.event, "timestamp": event.timestamp, "details": event.details}
                for event in deep_result.trace.events
            ]
        )
