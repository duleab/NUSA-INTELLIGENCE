"""Enhanced CSS styling for professional data visualization components."""

from __future__ import annotations


def get_enhanced_chart_css() -> str:
    """Return comprehensive CSS for enhanced chart styling."""
    return """
    <style>
    /* Enhanced Chart Styling */
    .enhanced-chart-container {
        background: linear-gradient(135deg, #0F1E33 0%, #1C2D4E 100%);
        border: 1px solid rgba(96, 165, 250, 0.2);
        border-radius: 12px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
                    0 2px 4px -1px rgba(0, 0, 0, 0.06);
        transition: all 0.3s ease;
    }
    
    .enhanced-chart-container:hover {
        border-color: rgba(96, 165, 250, 0.4);
        box-shadow: 0 8px 25px -5px rgba(0, 0, 0, 0.2);
    }
    
    /* Chart Titles and Labels */
    .chart-title {
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
        font-size: 18px;
        font-weight: 700;
        color: #EFF6FF;
        margin-bottom: 8px;
        letter-spacing: -0.025em;
    }
    
    .chart-subtitle {
        font-family: Inter, ui-sans-serif, system-ui, sans-serif;
        font-size: 14px;
        color: #94A3B8;
        margin-bottom: 20px;
        line-height: 1.5;
    }
    
    /* Enhanced Legend Styling */
    .chart-legend {
        display: flex;
        gap: 20px;
        margin-bottom: 16px;
        flex-wrap: wrap;
        align-items: center;
    }
    
    .legend-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 12px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 8px;
        font-size: 12px;
        color: #94A3B8;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    
    .legend-item:hover {
        background: rgba(255, 255, 255, 0.1);
        color: #EFF6FF;
    }
    
    .legend-color {
        width: 14px;
        height: 14px;
        border-radius: 3px;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
    }
    
    /* Trend Indicators */
    .trend-indicator {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        border-radius: 8px;
        font-size: 13px;
        font-weight: 600;
        margin: 12px 0;
        transition: all 0.2s ease;
    }
    
    .trend-up {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%);
        color: #10B981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    
    .trend-down {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    
    .trend-flat {
        background: linear-gradient(135deg, rgba(107, 114, 128, 0.15) 0%, rgba(75, 85, 99, 0.1) 100%);
        color: #6B7280;
        border: 1px solid rgba(107, 114, 128, 0.3);
    }
    
    /* Enhanced Metrics */
    .enhanced-metric-card {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 16px;
        margin: 8px 0;
        transition: all 0.2s ease;
    }
    
    .enhanced-metric-card:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(96, 165, 250, 0.3);
    }
    
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 4px;
    }
    
    .metric-value {
        font-size: 20px;
        font-weight: 700;
        color: #EFF6FF;
        line-height: 1.2;
    }
    
    .metric-delta {
        font-size: 12px;
        font-weight: 500;
        margin-top: 4px;
    }
    
    .metric-delta.positive { color: #10B981; }
    .metric-delta.negative { color: #EF4444; }
    .metric-delta.neutral { color: #6B7280; }
    
    /* Enhanced Table Styling */
    .enhanced-table {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        overflow: hidden;
        margin: 16px 0;
    }
    
    .table-header {
        background: rgba(59, 130, 246, 0.1);
        border-bottom: 1px solid rgba(96, 165, 250, 0.2);
        padding: 12px 16px;
        font-weight: 600;
        color: #EFF6FF;
        font-size: 13px;
    }
    
    .table-row {
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        padding: 12px 16px;
        transition: all 0.2s ease;
    }
    
    .table-row:hover {
        background: rgba(255, 255, 255, 0.03);
    }
    
    .table-row:last-child {
        border-bottom: none;
    }
    
    /* Insight Boxes */
    .insight-box {
        background: linear-gradient(135deg, rgba(96, 165, 250, 0.1) 0%, rgba(59, 130, 246, 0.05) 100%);
        border: 1px solid rgba(96, 165, 250, 0.2);
        border-radius: 8px;
        padding: 16px;
        margin: 12px 0;
    }
    
    .insight-title {
        font-weight: 600;
        color: #60A5FA;
        font-size: 14px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .insight-content {
        color: #E2E8F0;
        font-size: 13px;
        line-height: 1.5;
    }
    
    /* Performance Indicators */
    .performance-indicator {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .perf-high {
        background: rgba(16, 185, 129, 0.2);
        color: #10B981;
    }
    
    .perf-medium {
        background: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
    }
    
    .perf-low {
        background: rgba(239, 68, 68, 0.2);
        color: #EF4444;
    }
    
    /* Loading and Animation States */
    .chart-loading {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 300px;
        color: #94A3B8;
        font-size: 14px;
    }
    
    .pulse-animation {
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    
    /* Responsive Design */
    @media (max-width: 768px) {
        .enhanced-chart-container {
            padding: 16px;
            margin: 8px 0;
        }
        
        .chart-legend {
            gap: 12px;
        }
        
        .legend-item {
            font-size: 11px;
            padding: 4px 8px;
        }
        
        .chart-title {
            font-size: 16px;
        }
        
        .chart-subtitle {
            font-size: 12px;
        }
    }
    
    /* Accessibility Enhancements */
    .enhanced-chart-container:focus-within {
        outline: 2px solid #60A5FA;
        outline-offset: 2px;
    }
    
    .legend-item[tabindex="0"]:focus {
        outline: 1px solid #60A5FA;
        outline-offset: 1px;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        .enhanced-chart-container {
            border-color: #EFF6FF;
        }
        
        .chart-title, .chart-subtitle {
            color: #FFFFFF;
        }
        
        .legend-item {
            border: 1px solid #94A3B8;
        }
    }
    </style>
    """


def get_streamlit_chart_config() -> dict:
    """Return Streamlit chart configuration for enhanced styling."""
    return {
        "theme": {
            "base": "dark",
            "primaryColor": "#3B82F6",
            "backgroundColor": "#0F1E33",
            "secondaryBackgroundColor": "#1C2D4E",
            "textColor": "#EFF6FF"
        },
        "toolbar": {
            "show": True
        },
        "legend": {
            "orientation": "h",
            "x": 0,
            "y": 1.02
        }
    }