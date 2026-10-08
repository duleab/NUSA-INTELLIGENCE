"""Enhanced chart-ready frames and tables for professional Streamlit visualizations.

This module provides sophisticated data visualization utilities with improved:
- Color schemes and styling
- Interactive elements
- Accessibility features
- Professional formatting
- Statistical context
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
import streamlit as st

from nusa.ui import insights as ins
from nusa.ui.presentation import (
    bank_logo_html,
    chart_numeric_value,
    format_change,
    unit_label,
)

# Professional color palette for data visualization
CHART_COLORS = {
    "primary": "#3B82F6",      # Blue - for selected bank
    "secondary": "#60A5FA",    # Light blue - for peers
    "accent": "#06B6D4",       # Cyan - for peer median
    "success": "#10B981",      # Green - for positive values
    "warning": "#F59E0B",      # Amber - for moderate values
    "error": "#EF4444",        # Red - for negative values
    "neutral": "#6B7280",      # Gray - for neutral data
    "background": "#0F1E33",   # Dark background
    "surface": "#1C2D4E",      # Surface color
    "text": "#EFF6FF",         # Text color
    "muted": "#94A3B8"         # Muted text
}

# Chart styling configuration
CHART_CONFIG = {
    "font_family": "Inter, ui-sans-serif, system-ui, sans-serif",
    "font_size": 12,
    "grid_color": "rgba(255,255,255,0.1)",
    "axis_color": "#94A3B8",
    "title_size": 16,
    "subtitle_size": 12,
    "border_radius": 8,
    "padding": 20,
    "animation_duration": 300
}


def validation_from_trace(trace_events: Any) -> dict[str, int | bool]:
    """Extract evidence validation counts from orchestrator trace events."""
    events = list(trace_events)
    validation = next((event for event in events if event.event == "EVIDENCE_VALIDATED"), None)
    if not validation:
        return {
            "valid": False,
            "evidence_count": 0,
            "invalid_count": 0,
            "validated_count": 0,
        }
    total = int(validation.details.get("evidence_count", 0))
    invalid = int(validation.details.get("invalid_count", 0))
    validated = max(total - invalid, 0)
    return {
        "valid": bool(validation.details.get("valid", False)),
        "evidence_count": total,
        "invalid_count": invalid,
        "validated_count": validated,
    }


def create_enhanced_bar_chart(
    data: pd.DataFrame,
    title: str,
    subtitle: str = "",
    color_column: str = None,
    highlight_value: str = None,
    show_values: bool = True,
    height: int = 400
) -> None:
    """Create an enhanced bar chart with professional styling and interactivity."""
    
    # Custom CSS for enhanced charts
    st.markdown(
        f"""
        <style>
        .enhanced-chart-container {{
            background: {CHART_COLORS["surface"]};
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: {CHART_CONFIG["border_radius"]}px;
            padding: {CHART_CONFIG["padding"]}px;
            margin: 10px 0;
        }}
        
        .chart-title {{
            font-family: {CHART_CONFIG["font_family"]};
            font-size: {CHART_CONFIG["title_size"]}px;
            font-weight: 700;
            color: {CHART_COLORS["text"]};
            margin-bottom: 8px;
        }}
        
        .chart-subtitle {{
            font-family: {CHART_CONFIG["font_family"]};
            font-size: {CHART_CONFIG["subtitle_size"]}px;
            color: {CHART_COLORS["muted"]};
            margin-bottom: 16px;
        }}
        
        .chart-legend {{
            display: flex;
            gap: 16px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: {CHART_COLORS["muted"]};
        }}
        
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Create chart container
    with st.container():
        st.markdown('<div class="enhanced-chart-container">', unsafe_allow_html=True)
        
        # Chart title and subtitle
        st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
        if subtitle:
            st.markdown(f'<div class="chart-subtitle">{subtitle}</div>', unsafe_allow_html=True)
        
        # Add legend for different data types
        _render_chart_legend(data, highlight_value)
        
        # Enhanced chart display
        st.bar_chart(data, height=height, use_container_width=True)
        
        # Add statistical summary below chart
        _render_chart_stats(data)
        
        st.markdown('</div>', unsafe_allow_html=True)


def _render_chart_legend(data: pd.DataFrame, highlight_value: str = None) -> None:
    """Render professional chart legend with color coding."""
    legend_html = '<div class="chart-legend">'
    
    if highlight_value:
        legend_html += f'''
        <div class="legend-item">
            <div class="legend-color" style="background-color: {CHART_COLORS["primary"]}"></div>
            <span>Selected Bank</span>
        </div>
        '''
    
    legend_html += f'''
    <div class="legend-item">
        <div class="legend-color" style="background-color: {CHART_COLORS["secondary"]}"></div>
        <span>Peer Banks</span>
    </div>
    <div class="legend-item">
        <div class="legend-color" style="background-color: {CHART_COLORS["accent"]}"></div>
        <span>Peer Median</span>
    </div>
    '''
    
    legend_html += '</div>'
    st.markdown(legend_html, unsafe_allow_html=True)


def _render_chart_stats(data: pd.DataFrame) -> None:
    """Render statistical summary below charts."""
    if data.empty:
        return
    
    col_name = data.columns[0]
    values = data[col_name].dropna()
    
    if len(values) > 1:
        stats_cols = st.columns(4)
        
        with stats_cols[0]:
            st.metric(
                "Min", 
                f"{values.min():.2f}",
                help="Minimum value in dataset"
            )
        
        with stats_cols[1]:
            st.metric(
                "Max", 
                f"{values.max():.2f}",
                help="Maximum value in dataset"
            )
        
        with stats_cols[2]:
            st.metric(
                "Median", 
                f"{values.median():.2f}",
                help="Middle value of the dataset"
            )
        
        with stats_cols[3]:
            st.metric(
                "Range", 
                f"{values.max() - values.min():.2f}",
                help="Difference between max and min values"
            )


def peer_distribution_chart_frame(peer_dist: dict[str, Any]) -> pd.DataFrame | None:
    """Build an enhanced sorted bar-chart frame with professional styling and color coding."""
    bars = peer_dist.get("bars")
    if not bars:
        return None
    
    unit = str(peer_dist.get("unit", "percent"))
    column = f"Change ({unit_label(unit)})"
    
    # Enhanced sorting with role-based ordering
    ordered = sorted(
        bars,
        key=lambda bar: (
            0 if bar.get("role") == "Selected bank" else 
            1 if bar.get("role") == "Size-matched peer" else 
            2 if bar.get("role") == "Peer median" else 3,
            -float(bar.get("change", 0))  # Sort by value within role
        ),
    )
    
    # Create enhanced DataFrame with color information
    chart_data = pd.DataFrame(
        {column: [float(bar["change"]) for bar in ordered]},
        index=[str(bar["label"]) for bar in ordered],
    )
    
    return chart_data


def create_enhanced_peer_distribution_chart(peer_dist: dict[str, Any]) -> None:
    """Create an enhanced peer distribution chart with professional styling."""
    chart_frame = peer_distribution_chart_frame(peer_dist)
    if chart_frame is None:
        st.info("No peer comparison data available for visualization.")
        return
    
    metric_name = peer_dist.get("metric", "").replace("_", " ").title()
    unit = str(peer_dist.get("unit", "percent"))
    count = peer_dist.get("count", 0)
    
    # Find the selected bank for highlighting
    bars = peer_dist.get("bars", [])
    selected_bank = next((bar["label"] for bar in bars if bar.get("role") == "Selected bank"), None)
    
    title = f"Peer Context Distribution: {metric_name}"
    subtitle = f"Comparing {count} banks • Unit: {unit_label(unit)}"
    
    # Create enhanced chart
    create_enhanced_bar_chart(
        data=chart_frame,
        title=title,
        subtitle=subtitle,
        highlight_value=selected_bank,
        height=350
    )
    
    # Enhanced table with better formatting
    _render_enhanced_peer_table(peer_dist)


def _render_enhanced_peer_table(peer_dist: dict[str, Any]) -> None:
    """Render an enhanced peer comparison table with role-based styling."""
    table_rows = peer_distribution_table_rows(peer_dist)
    if not table_rows:
        return
    
    # Convert to DataFrame for better display
    df = pd.DataFrame(table_rows)
    
    # Add styling based on role
    def highlight_selected(s):
        return ['background-color: rgba(59, 130, 246, 0.1)' if role == 'Selected bank' 
                else 'background-color: rgba(96, 165, 250, 0.05)' if role == 'Size-matched peer'
                else '' for role in s]
    
    # Display with custom styling
    st.markdown("##### Detailed Comparison")
    styled_df = df.style.apply(highlight_selected, subset=['Role'])
    st.dataframe(styled_df, hide_index=True, use_container_width=True)
    
    # Add insights
    _render_peer_insights(peer_dist)


def _render_peer_insights(peer_dist: dict[str, Any]) -> None:
    """Render intelligent insights about peer comparison data."""
    bars = peer_dist.get("bars", [])
    stats = peer_dist.get("stats", {})
    
    if not bars or not stats:
        return
    
    selected_bar = next((bar for bar in bars if bar.get("role") == "Selected bank"), None)
    if not selected_bar:
        return
    
    selected_value = selected_bar["change"]
    median_value = stats.get("median", 0)
    
    # Generate contextual insights
    insights = []
    
    if abs(selected_value) > abs(median_value) * 1.5:
        direction = "significantly higher" if selected_value > median_value else "significantly lower"
        insights.append(f"📈 **Outlier Alert**: Selected bank shows {direction} performance than peer median")
    
    if len(bars) >= 4:  # Enough data for percentile analysis
        values = [bar["change"] for bar in bars if bar.get("role") != "Peer median"]
        values.sort()
        percentile = (sum(1 for v in values if v < selected_value) / len(values)) * 100
        insights.append(f"📊 **Percentile Rank**: {percentile:.0f}th percentile among peers")
    
    range_val = stats.get("max", 0) - stats.get("min", 0)
    if range_val > 0:
        volatility = "high" if range_val > abs(median_value) * 2 else "moderate" if range_val > abs(median_value) else "low"
        insights.append(f"📉 **Market Volatility**: {volatility.title()} dispersion across peer group")
    
    if insights:
        st.markdown("##### 💡 Key Insights")
        for insight in insights:
            st.markdown(f"- {insight}")


def peer_distribution_table_rows(peer_dist: dict[str, Any]) -> list[dict[str, str]]:
    """Human-readable peer comparison rows for enhanced dataframe display."""
    bars = peer_dist.get("bars")
    if not bars:
        return []
    unit = str(peer_dist.get("unit", "percent"))
    
    rows: list[dict[str, str]] = []
    for bar in bars:
        # Add visual indicators
        role = str(bar.get("role", "—"))
        icon = "🎯" if role == "Selected bank" else "👥" if role == "Size-matched peer" else "📊"
        
        rows.append(
            {
                "Bank": f"{icon} {str(bar.get('label', '—'))}",
                "Role": role,
                "Change": format_change(bar.get("change"), unit),
            }
        )
    return rows


def create_enhanced_metric_history_chart(
    previous_value: object,
    current_value: object,
    period: str,
    metric: str,
    data_mode: str,
    ticker: str = "Bank"
) -> None:
    """Create an enhanced metric history chart with trend analysis."""
    
    hist_frame, y_label = metric_history_chart_frame(
        previous_value=previous_value,
        current_value=current_value,
        period=period,
        metric=metric,
        data_mode=data_mode,
    )
    
    if hist_frame.empty:
        st.warning("No historical data available for visualization.")
        return
    
    # Calculate trend information
    prev_val = chart_numeric_value(previous_value, metric, data_mode=data_mode) or 0
    curr_val = chart_numeric_value(current_value, metric, data_mode=data_mode) or 0
    change_pct = ((curr_val - prev_val) / abs(prev_val) * 100) if prev_val != 0 else 0
    
    # Enhanced styling for line charts
    st.markdown(
        f"""
        <style>
        .metric-history-container {{
            background: {CHART_COLORS["surface"]};
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: {CHART_CONFIG["border_radius"]}px;
            padding: {CHART_CONFIG["padding"]}px;
            margin: 10px 0;
        }}
        
        .trend-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            margin: 8px 0;
        }}
        
        .trend-up {{
            background-color: rgba(16, 185, 129, 0.1);
            color: {CHART_COLORS["success"]};
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        
        .trend-down {{
            background-color: rgba(239, 68, 68, 0.1);
            color: {CHART_COLORS["error"]};
            border: 1px solid rgba(239, 68, 68, 0.2);
        }}
        
        .trend-flat {{
            background-color: rgba(107, 114, 128, 0.1);
            color: {CHART_COLORS["neutral"]};
            border: 1px solid rgba(107, 114, 128, 0.2);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    with st.container():
        st.markdown('<div class="metric-history-container">', unsafe_allow_html=True)
        
        # Title with trend indicator
        metric_label = metric.replace("_", " ").title()
        st.markdown(f"##### 📈 {ticker} - {metric_label} Trend")
        
        # Trend indicator
        if abs(change_pct) < 1:
            trend_class = "trend-flat"
            trend_icon = "➡️"
            trend_text = "Stable"
        elif change_pct > 0:
            trend_class = "trend-up"
            trend_icon = "📈"
            trend_text = f"Growing (+{change_pct:.1f}%)"
        else:
            trend_class = "trend-down"
            trend_icon = "📉"
            trend_text = f"Declining ({change_pct:.1f}%)"
        
        st.markdown(
            f'<div class="trend-indicator {trend_class}">{trend_icon} {trend_text}</div>',
            unsafe_allow_html=True
        )
        
        # Enhanced line chart
        st.line_chart(hist_frame, height=300, use_container_width=True)
        
        # Period summary
        start, end = period.split(" to ", 1) if " to " in period else ("Prior", "Current")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                f"{start} Value",
                f"{prev_val:,.2f}",
                help=f"Value at the beginning of {period}"
            )
        
        with col2:
            st.metric(
                f"{end} Value",
                f"{curr_val:,.2f}",
                delta=f"{curr_val - prev_val:,.2f}",
                help=f"Value at the end of {period}"
            )
        
        with col3:
            st.metric(
                "Change %",
                f"{change_pct:+.2f}%",
                help="Percentage change over the period"
            )
        
        st.markdown('</div>', unsafe_allow_html=True)


def metric_history_chart_frame(
    *,
    previous_value: object,
    current_value: object,
    period: str,
    metric: str,
    data_mode: str,
) -> tuple[pd.DataFrame, str]:
    """Enhanced two-point history frame with better formatting and validation."""
    start, end = period.split(" to ", 1) if " to " in period else ("Prior", "Current")
    prev = chart_numeric_value(previous_value, metric, data_mode=data_mode)
    curr = chart_numeric_value(current_value, metric, data_mode=data_mode)
    
    # Enhanced labeling based on metric type and data mode
    metric_key = metric.lower()
    if data_mode in {"fixture", "synthetic", "demo"}:
        y_label = f"{metric.replace('_', ' ').title()} (Sample Units)"
    elif metric_key == "roa":
        y_label = "ROA (%)"
    elif metric_key in {"earnings", "net_interest_income", "total_assets", "total_equity"}:
        y_label = f"{metric.replace('_', ' ').title()} (IDR Billions)"
    else:
        y_label = f"{metric.replace('_', ' ').title()}"
    
    # Handle missing values gracefully
    prev_display = prev if prev is not None else 0.0
    curr_display = curr if curr is not None else 0.0
    
    frame = pd.DataFrame(
        {y_label: [prev_display, curr_display]},
        index=[start, end],
    )
    
    return frame, y_label


def create_enhanced_comparison_chart(
    comparison_data: list[dict[str, Any]],
    metric: str,
    title: str = "Peer Comparison"
) -> None:
    """Create enhanced comparison charts for multiple banks."""
    
    if not comparison_data:
        st.info("No comparison data available.")
        return
    
    # Prepare data for visualization
    banks = []
    values = []
    colors = []
    
    for item in comparison_data:
        banks.append(item.get("ticker", "Unknown"))
        change_val = item.get("change", 0)
        values.append(float(change_val))
        
        # Color coding based on value
        if change_val > 0:
            colors.append(CHART_COLORS["success"])
        elif change_val < 0:
            colors.append(CHART_COLORS["error"])
        else:
            colors.append(CHART_COLORS["neutral"])
    
    # Create comparison DataFrame
    unit = comparison_data[0].get("change_unit", "percent") if comparison_data else "percent"
    column_name = f"{metric.replace('_', ' ').title()} Change ({unit_label(unit)})"
    
    chart_data = pd.DataFrame(
        {column_name: values},
        index=banks
    )
    
    # Enhanced chart with professional styling
    create_enhanced_bar_chart(
        data=chart_data,
        title=title,
        subtitle=f"Comparing {len(banks)} banks on {metric.replace('_', ' ').title()}",
        height=400
    )
    
    # Enhanced comparison table
    _render_enhanced_comparison_table(comparison_data, metric)


def _render_enhanced_comparison_table(comparison_data: list[dict[str, Any]], metric: str) -> None:
    """Render enhanced comparison table with statistical context."""
    
    if not comparison_data:
        return
    
    # Prepare table data
    table_data = []
    for item in comparison_data:
        ticker = item.get("ticker", "—")
        change = item.get("change", 0)
        unit = item.get("change_unit", "percent")
        peer_median = item.get("peer_median", 0)
        deviation = item.get("deviation", 0)
        
        # Add performance indicators
        if abs(deviation) > abs(peer_median) * 0.5:  # Significant deviation
            indicator = "🔥" if deviation > 0 else "❄️"
        else:
            indicator = "📊"
        
        table_data.append({
            "Bank": f"{indicator} {ticker}",
            "Change": format_change(change, unit),
            "Peer Median": format_change(peer_median, unit),
            "Deviation": format_change(deviation, unit),
            "Status": "Outperforming" if deviation > 0 else "Underperforming" if deviation < 0 else "In-line"
        })
    
    # Display enhanced table
    st.markdown("##### 📊 Detailed Performance Analysis")
    df = pd.DataFrame(table_data)
    
    # Style the dataframe
    def highlight_performance(s):
        styles = []
        for status in s:
            if status == "Outperforming":
                styles.append('background-color: rgba(16, 185, 129, 0.1)')
            elif status == "Underperforming":
                styles.append('background-color: rgba(239, 68, 68, 0.1)')
            else:
                styles.append('')
        return styles
    
    styled_df = df.style.apply(highlight_performance, subset=['Status'])
    st.dataframe(styled_df, hide_index=True, use_container_width=True)


def create_enhanced_investigation_overview(
    ticker: str, 
    selected_discovery: dict[str, Any] | None, 
    company: dict[str, Any]
) -> None:
    """Create an enhanced investigation overview with professional styling."""
    logo_badge = bank_logo_html(ticker, size_px=54)
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0F1E33 0%, #1C2D4E 100%); 
                   border: 1px solid rgba(96, 165, 250, 0.3); 
                   border-radius: 16px; 
                   padding: 24px; 
                   margin: 20px 0;
                   box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);">
            <div style="display: flex; align-items: center; gap: 16px; margin-bottom: 20px;">
                {logo_badge}
                <div>
                    <h2 style="color: #EFF6FF; margin: 0; font-size: 28px; font-weight: 800;">
                        {ticker}
                    </h2>
                    <p style="color: #94A3B8; margin: 4px 0 0 0; font-size: 16px;">
                        {company.get('company_name', 'Banking Institution')}
                    </p>
                </div>
            </div>
    """, unsafe_allow_html=True)
    
    if selected_discovery:
        # Enhanced KPI metrics display
        score = selected_discovery.get("score", 0)
        
        # Determine status color based on score
        if score >= 80:
            status_color = "#10B981"
            status_bg = "rgba(16, 185, 129, 0.1)"
            status_icon = "🔥"
            status_text = "HIGH PRIORITY"
        elif score >= 60:
            status_color = "#F59E0B"
            status_bg = "rgba(245, 158, 11, 0.1)"
            status_icon = "⚡"
            status_text = "MEDIUM PRIORITY"
        else:
            status_color = "#6B7280"
            status_bg = "rgba(107, 114, 128, 0.1)"
            status_icon = "📊"
            status_text = "LOW PRIORITY"
        
        st.markdown(f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                       gap: 16px; margin: 20px 0;">
                <div style="background: {status_bg}; border: 1px solid {status_color}; 
                           border-radius: 12px; padding: 16px; text-align: center;">
                    <div style="color: {status_color}; font-size: 24px; margin-bottom: 8px;">
                        {status_icon}
                    </div>
                    <div style="color: {status_color}; font-size: 28px; font-weight: 800; 
                               margin-bottom: 4px;">
                        {score}/100
                    </div>
                    <div style="color: {status_color}; font-size: 11px; font-weight: 600; 
                               letter-spacing: 0.05em;">
                        {status_text}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Key takeaway with enhanced styling
        hero_sentence = ins.generate_hero_sentence(selected_discovery)
        st.markdown(f"""
            <div style="background: rgba(96, 165, 250, 0.08); 
                       border-left: 4px solid #60A5FA; 
                       border-radius: 8px; 
                       padding: 20px; 
                       margin: 20px 0;">
                <h4 style="color: #60A5FA; margin: 0 0 12px 0; font-size: 14px; 
                          font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">
                    🎯 Key Investigation Insight
                </h4>
                <p style="color: #E2E8F0; margin: 0; font-size: 16px; line-height: 1.6; 
                         font-style: italic;">
                    {hero_sentence}
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)


def create_enhanced_research_summary_table(
    investigation_result=None, 
    deep_result=None, 
    selected_discovery: dict[str, Any] | None = None
) -> None:
    """Create a comprehensive research summary table with all key findings."""
    
    st.markdown("""
        <div style="background: linear-gradient(135deg, #0F1E33 0%, #1C2D4E 100%); 
                   border: 1px solid rgba(96, 165, 250, 0.2); 
                   border-radius: 12px; 
                   padding: 24px; 
                   margin: 20px 0;">
            <h4 style="color: #EFF6FF; margin-bottom: 20px; font-weight: 700; 
                      display: flex; align-items: center; gap: 8px;">
                📋 Comprehensive Research Summary
            </h4>
    """, unsafe_allow_html=True)
    
    # Determine data source
    result = deep_result or investigation_result
    
    if not result:
        st.info("🔍 Run an investigation to see comprehensive research summary")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    # Prepare summary data
    summary_data = []
    
    # Basic information
    ticker = getattr(result, 'ticker', 'Unknown')
    
    # Add investigation metadata
    summary_data.extend([
        {"Category": "🏦 Basic Information", "Metric": "Bank Ticker", "Value": ticker, "Context": "Primary identifier"},
        {"Category": "🏦 Basic Information", "Metric": "Investigation Type", 
         "Value": "Autonomous Deep Investigation" if deep_result else "Standard Investigation", 
         "Context": "Analysis method used"},
    ])
    
    # Add discovery insights if available
    if selected_discovery:
        score = selected_discovery.get("score", 0)
        primary_driver = selected_discovery.get("primary_driver", "").replace("_", " ").title()
        primary_change = format_change(
            selected_discovery.get("primary_change"), 
            selected_discovery.get("primary_change_unit", "")
        )
        peer_median = format_change(
            selected_discovery.get("primary_peer_median"), 
            selected_discovery.get("primary_change_unit", "")
        )
        
        summary_data.extend([
            {"Category": "📊 Discovery Analysis", "Metric": "Research Priority Score", 
             "Value": f"{score}/100", "Context": "Peer-relative anomaly ranking"},
            {"Category": "📊 Discovery Analysis", "Metric": "Primary Driver", 
             "Value": primary_driver, "Context": "Most significant metric change"},
            {"Category": "📊 Discovery Analysis", "Metric": "Primary Change", 
             "Value": primary_change, "Context": "Observed metric change"},
            {"Category": "📊 Discovery Analysis", "Metric": "Peer Median", 
             "Value": peer_median, "Context": "Leave-one-out peer reference"},
        ])
    
    # Add evidence information
    if hasattr(result, 'evidence_ledger') and result.evidence_ledger:
        evidence = result.evidence_ledger
        validation = validation_from_trace(result.trace.events)
        
        summary_data.extend([
            {"Category": "🔍 Evidence Analysis", "Metric": "Evidence Records", 
             "Value": f"{len(evidence)}", "Context": "Total evidence items collected"},
            {"Category": "🔍 Evidence Analysis", "Metric": "Validated Records", 
             "Value": f"{validation['validated_count']}/{validation['evidence_count']}", 
             "Context": "Passed deterministic validation"},
            {"Category": "🔍 Evidence Analysis", "Metric": "Failed Checks", 
             "Value": f"{validation['invalid_count']}", "Context": "Evidence validation failures"},
        ])
        
        # Add evidence details
        for i, item in enumerate(list(evidence)[:5]):  # Show first 5 evidence items
            metric_name = item.metric.replace("_", " ").title()
            change_val = format_change(item.change, item.change_unit)
            
            summary_data.append({
                "Category": f"📈 Evidence #{i+1}", 
                "Metric": f"{metric_name} Change", 
                "Value": change_val, 
                "Context": f"Period: {item.period}"
            })
    
    # Add agent decisions if available (for deep investigation)
    if deep_result and hasattr(deep_result, 'decisions'):
        decisions = deep_result.decisions
        peer_count = len(getattr(deep_result, 'peer_tickers_selected', []))
        
        summary_data.extend([
            {"Category": "🤖 Agent Analysis", "Metric": "Autonomous Steps", 
             "Value": f"{len(decisions)}", "Context": "Agent decision sequence"},
            {"Category": "🤖 Agent Analysis", "Metric": "Peers Selected", 
             "Value": f"{peer_count}", "Context": "Size-matched peer banks"},
            {"Category": "🤖 Agent Analysis", "Metric": "Final Decision", 
             "Value": decisions[-1].decision if decisions else "Unknown", 
             "Context": "Agent stopping condition"},
        ])
    
    # Add synthesis information
    if hasattr(result, 'synthesis') and result.synthesis:
        synthesis = result.synthesis
        
        summary_data.extend([
            {"Category": "📝 Report Generation", "Metric": "Generation Mode", 
             "Value": synthesis.generation_mode, "Context": "Report creation method"},
            {"Category": "📝 Report Generation", "Metric": "Key Findings", 
             "Value": f"{len(synthesis.key_findings or [])}", "Context": "Number of key insights"},
            {"Category": "📝 Report Generation", "Metric": "Limitations", 
             "Value": f"{len(synthesis.limitations or [])}", "Context": "Analysis constraints noted"},
        ])
    
    # Create and display the enhanced table
    if summary_data:
        df_summary = pd.DataFrame(summary_data)
        
        # Custom styling function
        def style_summary_table(s):
            styles = []
            for cat in s:
                if "Basic Information" in str(cat):
                    styles.append('background-color: rgba(59, 130, 246, 0.1); color: #3B82F6; font-weight: 600;')
                elif "Discovery Analysis" in str(cat):
                    styles.append('background-color: rgba(16, 185, 129, 0.1); color: #10B981; font-weight: 600;')
                elif "Evidence Analysis" in str(cat):
                    styles.append('background-color: rgba(245, 158, 11, 0.1); color: #F59E0B; font-weight: 600;')
                elif "Evidence #" in str(cat):
                    styles.append('background-color: rgba(139, 92, 246, 0.1); color: #8B5CF6; font-weight: 500;')
                elif "Agent Analysis" in str(cat):
                    styles.append('background-color: rgba(6, 182, 212, 0.1); color: #06B6D4; font-weight: 600;')
                elif "Report Generation" in str(cat):
                    styles.append('background-color: rgba(107, 114, 128, 0.1); color: #6B7280; font-weight: 600;')
                else:
                    styles.append('')
            return styles
        
        # Apply styling and display
        styled_summary = df_summary.style.apply(style_summary_table, subset=['Category'])
        st.dataframe(styled_summary, hide_index=True, use_container_width=True, height=400)
        
        # Summary statistics
        col1, col2, col3, col4 = st.columns(4)
        
        evidence_count = len([item for item in summary_data if "Evidence #" in item["Category"]])
        categories = len(set(item["Category"] for item in summary_data))
        
        with col1:
            st.metric("📊 Total Metrics", len(summary_data), help="Total analysis points")
        
        with col2:
            st.metric("🔍 Evidence Items", evidence_count, help="Direct evidence records")
        
        with col3:
            st.metric("📋 Categories", categories, help="Analysis categories covered")
        
        with col4:
            if hasattr(result, 'synthesis') and result.synthesis:
                confidence = "High" if evidence_count >= 3 else "Medium" if evidence_count >= 2 else "Low"
                st.metric("✅ Confidence", confidence, help="Analysis confidence level")
            else:
                st.metric("⏱️ Status", "In Progress", help="Investigation status")
    
    st.markdown('</div>', unsafe_allow_html=True)


def create_portfolio_overview_chart(discovery_data: list[dict[str, Any]]) -> None:
    """Create enhanced portfolio overview visualization."""
    if not discovery_data or len(discovery_data) < 5:
        st.info("Insufficient data for portfolio overview.")
        return
    
    # Take top 10 banks for overview
    top_banks = discovery_data[:10]
    
    # Prepare data
    tickers = [bank.get("ticker", f"Bank {i}") for i, bank in enumerate(top_banks)]
    scores = [bank.get("score", 0) for bank in top_banks]
    
    # Create enhanced visualization
    st.markdown(
        f"""
        <div style="background: {CHART_COLORS['surface']}; 
                    border: 1px solid rgba(255,255,255,0.1); 
                    border-radius: {CHART_CONFIG['border_radius']}px; 
                    padding: {CHART_CONFIG['padding']}px; 
                    margin: 10px 0;">
            <h4 style="color: {CHART_COLORS['text']}; margin-bottom: 16px;">
                🏦 Research Priority Portfolio Overview
            </h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Create score distribution chart
    chart_data = pd.DataFrame(
        {"Research Priority Score": scores},
        index=tickers
    )
    
    st.bar_chart(chart_data, height=400, use_container_width=True)
    
    # Portfolio statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Avg Score",
            f"{sum(scores)/len(scores):.1f}",
            help="Average research priority score"
        )
    
    with col2:
        st.metric(
            "Top Score",
            f"{max(scores):.1f}",
            help="Highest research priority score"
        )
    
    with col3:
        high_priority = sum(1 for score in scores if score >= 70)
        st.metric(
            "High Priority",
            f"{high_priority}",
            help="Banks with score ≥ 70"
        )
    
    with col4:
        score_range = max(scores) - min(scores)
        st.metric(
            "Score Range",
            f"{score_range:.1f}",
            help="Difference between highest and lowest scores"
        )


def create_portfolio_overview_chart(discovery_data: list[dict[str, Any]]) -> None:
    """Create enhanced portfolio overview visualization."""
    
    if not discovery_data or len(discovery_data) < 5:
        st.info("Insufficient data for portfolio overview.")
        return
    
    # Take top 10 banks for overview
    top_banks = discovery_data[:10]
    
    # Prepare data
    tickers = [bank.get("ticker", f"Bank {i}") for i, bank in enumerate(top_banks)]
    scores = [bank.get("score", 0) for bank in top_banks]
    
    # Create enhanced visualization
    st.markdown(
        f"""
        <div style="background: {CHART_COLORS['surface']}; 
                    border: 1px solid rgba(255,255,255,0.1); 
                    border-radius: {CHART_CONFIG['border_radius']}px; 
                    padding: {CHART_CONFIG['padding']}px; 
                    margin: 10px 0;">
            <h4 style="color: {CHART_COLORS['text']}; margin-bottom: 16px;">
                🏦 Research Priority Portfolio Overview
            </h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Create score distribution chart
    chart_data = pd.DataFrame(
        {"Research Priority Score": scores},
        index=tickers
    )
    
    st.bar_chart(chart_data, height=400, use_container_width=True)
    
    # Portfolio statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Avg Score",
            f"{sum(scores)/len(scores):.1f}",
            help="Average research priority score"
        )
    
    with col2:
        st.metric(
            "Top Score",
            f"{max(scores):.1f}",
            help="Highest research priority score"
        )
    
    with col3:
        high_priority = sum(1 for score in scores if score >= 70)
        st.metric(
            "High Priority",
            f"{high_priority}",
            help="Banks with score ≥ 70"
        )
    
    with col4:
        score_range = max(scores) - min(scores)
        st.metric(
            "Score Range",
            f"{score_range:.1f}",
            help="Difference between highest and lowest scores"
        )


def create_enhanced_evidence_visualization(evidence_items, ticker: str = "Bank") -> None:
    """Create enhanced evidence visualization with multiple chart types."""
    
    if not evidence_items:
        st.info("No evidence data available for visualization.")
        return
    
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0F1E33 0%, #1C2D4E 100%); 
                   border: 1px solid rgba(96, 165, 250, 0.2); 
                   border-radius: 12px; 
                   padding: 24px; 
                   margin: 16px 0;">
            <h4 style="color: #EFF6FF; margin-bottom: 20px; font-weight: 700;">
                📊 {ticker} - Evidence Analysis Dashboard
            </h4>
        </div>
    """, unsafe_allow_html=True)
    
    # Create tabs for different visualizations
    tab1, tab2, tab3 = st.tabs(["📈 Metric Trends", "🎯 Peer Comparison", "📋 Evidence Summary"])
    
    with tab1:
        # Metric trends visualization
        metrics_data = {}
        for item in evidence_items:
            metric = item.metric.replace("_", " ").title()
            if metric not in metrics_data:
                metrics_data[metric] = []
            
            metrics_data[metric].append({
                "Period": item.period,
                "Current": chart_numeric_value(item.current_value, item.metric, data_mode=item.data_mode) or 0,
                "Previous": chart_numeric_value(item.previous_value, item.metric, data_mode=item.data_mode) or 0,
                "Change %": ((item.current_value or 0) - (item.previous_value or 0)) / abs(item.previous_value or 1) * 100 if item.previous_value else 0
            })
        
        for metric, data in metrics_data.items():
            st.markdown(f"##### 📈 {metric} Trend Analysis")
            
            if data:
                df_metric = pd.DataFrame(data)
                
                # Create multi-series chart
                chart_data = pd.DataFrame({
                    "Current Value": df_metric["Current"],
                    "Previous Value": df_metric["Previous"]
                }, index=df_metric["Period"])
                
                st.line_chart(chart_data, height=300, use_container_width=True)
                
                # Show change percentage
                avg_change = sum(item["Change %"] for item in data) / len(data)
                trend_direction = "📈 Growing" if avg_change > 0 else "📉 Declining" if avg_change < 0 else "➡️ Stable"
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Avg Change", f"{avg_change:+.1f}%")
                with col2:
                    st.metric("Trend", trend_direction.split(" ")[1])
                with col3:
                    volatility = max(item["Change %"] for item in data) - min(item["Change %"] for item in data)
                    st.metric("Volatility", f"{volatility:.1f}%")
    
    with tab2:
        # Peer comparison visualization
        st.markdown("##### 🎯 Peer Performance Analysis")
        
        for item in evidence_items:
            if hasattr(item, 'peer_median') and item.peer_median is not None:
                metric_name = item.metric.replace("_", " ").title()
                
                # Create comparison chart
                comparison_data = pd.DataFrame({
                    f"{metric_name} Change": [item.change or 0, item.peer_median or 0]
                }, index=[ticker, "Peer Median"])
                
                st.bar_chart(comparison_data, height=250)
                
                # Performance indicator
                if (item.change or 0) > (item.peer_median or 0):
                    performance = "🔥 Outperforming"
                    perf_color = "#10B981"
                elif (item.change or 0) < (item.peer_median or 0):
                    performance = "❄️ Underperforming"
                    perf_color = "#EF4444"
                else:
                    performance = "📊 In-line"
                    perf_color = "#6B7280"
                
                st.markdown(f"""
                    <div style="background: rgba(96, 165, 250, 0.05); 
                               border-left: 4px solid {perf_color}; 
                               padding: 12px; margin: 8px 0; border-radius: 6px;">
                        <strong style="color: {perf_color};">{performance}</strong> - 
                        {ticker}: {format_change(item.change, item.change_unit)} vs 
                        Peers: {format_change(item.peer_median, item.change_unit)}
                        ({item.peer_count} peers)
                    </div>
                """, unsafe_allow_html=True)
    
    with tab3:
        # Evidence summary table
        st.markdown("##### 📋 Detailed Evidence Records")
        
        evidence_summary = []
        for i, item in enumerate(evidence_items, 1):
            evidence_summary.append({
                "#": i,
                "Metric": item.metric.replace("_", " ").title(),
                "Period": item.period,
                "Change": format_change(item.change, item.change_unit),
                "Peer Median": format_change(item.peer_median, item.change_unit) if hasattr(item, 'peer_median') else "—",
                "Peers": getattr(item, 'peer_count', 0),
                "Status": "✅ Validated" if getattr(item, 'scoring_eligible', True) else "⚠️ Excluded",
                "Evidence ID": getattr(item, 'evidence_id', f"E{i:03d}")
            })
        
        df_evidence = pd.DataFrame(evidence_summary)
        
        # Style the evidence table
        def style_evidence_status(s):
            styles = []
            for status in s:
                if "Validated" in str(status):
                    styles.append('background-color: rgba(16, 185, 129, 0.1); color: #10B981; font-weight: 600;')
                elif "Excluded" in str(status):
                    styles.append('background-color: rgba(245, 158, 11, 0.1); color: #F59E0B; font-weight: 600;')
                else:
                    styles.append('')
            return styles
        
        styled_evidence = df_evidence.style.apply(style_evidence_status, subset=['Status'])
        st.dataframe(styled_evidence, hide_index=True, use_container_width=True)