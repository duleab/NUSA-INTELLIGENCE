"""Small presentation-only formatters for the Streamlit interface."""

from __future__ import annotations

import math
from datetime import datetime
from html import escape
from numbers import Real
from pathlib import Path


def format_idr_value(value: object) -> str:
    """Format a finite rupiah amount with compact, readable magnitude suffixes."""
    number = _finite_number(value)
    if number is None:
        return "—"
    magnitude = abs(number)
    sign = "−" if number < 0 else ""
    for threshold, suffix in ((1_000_000_000_000, "T"), (1_000_000_000, "B"), (1_000_000, "M")):
        if magnitude >= threshold:
            return f"{sign}IDR {magnitude / threshold:,.2f}{suffix}"
    return f"{sign}IDR {magnitude:,.0f}"


def format_change(value: object, unit: str) -> str:
    """Format a validated financial change without converting units."""
    number = _finite_number(value)
    if number is None:
        return "—"
    sign = "+" if number > 0 else "−" if number < 0 else ""
    magnitude = abs(number)
    if unit == "percent":
        return f"{sign}{magnitude:,.2f}%"
    if unit == "percentage_points":
        return f"{sign}{magnitude:,.2f} pp"
    if unit.upper() == "IDR":
        return f"{sign}{format_idr_value(magnitude)}"
    return f"{sign}{magnitude:,.2f} {unit}".strip()


def format_evidence_value(
    value: object,
    metric: str,
    *,
    data_mode: str = "cached",
) -> str:
    """Format annual evidence values using the metric's displayed unit."""
    number = _finite_number(value)
    if number is None:
        return "—"
    if data_mode in {"fixture", "synthetic", "demo"}:
        if metric.lower() in {"roa", "roe"}:
            return f"{number:,.2f}% sample"
        return f"{number:,.2f} sample units"
    if metric.lower() == "roa":
        return f"{number * 100:,.2f}%"
    return format_idr_value(number)


def unit_label(unit: str) -> str:
    """Short axis label for a validated change unit."""
    if unit == "percentage_points":
        return "percentage points"
    return unit


def chart_numeric_value(
    value: object,
    metric: str,
    *,
    data_mode: str = "cached",
) -> float | None:
    """Map ledger values to chart-friendly magnitudes (ROA as percent, etc.)."""
    number = _finite_number(value)
    if number is None:
        return None
    if data_mode in {"fixture", "synthetic", "demo"}:
        return number
    if metric.lower() == "roa":
        return number * 100.0
    return number


def format_retrieved_date(value: str | None) -> str:
    """Convert a timezone-aware ISO retrieval timestamp to a compact date."""
    if not value:
        return "Not recorded"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "Not recorded"
    return f"{parsed.day} {parsed.strftime('%b %Y')}"


def comparison_table_rows(records: object) -> list[dict[str, object]]:
    """Prepare only validated evidence fields for a readable comparison table."""
    if not isinstance(records, list):
        return []
    rows: list[dict[str, object]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        unit = str(record.get("change_unit", "percent"))
        rows.append(
            {
                "Ticker": record.get("ticker", "—"),
                "Metric": str(record.get("metric", "—")).replace("_", " ").title(),
                "Period": record.get("period", "—"),
                "Change": format_change(record.get("change"), unit),
                "Peer median": format_change(record.get("peer_median"), unit),
                "Peers": record.get("peer_count", 0),
                "Deviation": format_change(record.get("deviation"), unit),
                "Evidence ID": record.get("evidence_id", "—"),
            }
        )
    return rows


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


_BRAND_GRADIENTS: dict[str, tuple[str, str]] = {
    "BBCA": ("#0284C7", "#0369A1"),  # BCA Blue
    "BBRI": ("#0284C7", "#075985"),  # BRI Navy
    "BMRI": ("#1E3A8A", "#0F172A"),  # Mandiri Indigo
    "BBNI": ("#0F766E", "#115E59"),  # BNI Teal
    "SUPA": ("#9333EA", "#4C1D95"),  # Superbank Purple
    "BBSI": ("#4F46E5", "#312E81"),  # Krom Bank Indigo
    "BBHI": ("#EC4899", "#831843"),  # Allo Bank Pink
    "ARTO": ("#CA8A04", "#854D0E"),  # Bank Jago Gold
    "BRIS": ("#0D9488", "#115E59"),  # BSI Teal
    "BNGA": ("#DC2626", "#991B1B"),  # CIMB Red
    "BDMN": ("#EA580C", "#9A3412"),  # Danamon Orange
    "NISP": ("#DC2626", "#7F1D1D"),  # OCBC Red
    "BBTN": ("#1D4ED8", "#1E3A8A"),  # BTN Blue
    "BTPN": ("#2563EB", "#1E40AF"),  # BTPN Blue
    "MEGA": ("#D97706", "#78350F"),  # Bank Mega Amber
    "BNLI": ("#059669", "#064E3B"),  # Permata Green
    "DEMOBANK5": ("#F59E0B", "#B45309"),  # Sample Bank
}


def bank_logo_html(ticker: str, *, size_px: int = 40) -> str:
    """Return an inline HTML badge for a bank: SVG logo if available, else a stylized avatar badge."""
    clean = str(ticker).removesuffix(".JK").strip()
    svg_file = Path("assets") / "logos" / f"{clean}.svg"
    if svg_file.is_file():
        try:
            svg_content = svg_file.read_text(encoding="utf-8").strip()
            return (
                f'<div style="width:{size_px}px;height:{size_px}px;border-radius:22%;'
                f'overflow:hidden;display:inline-flex;align-items:center;justify-content:center;'
                f'flex-shrink:0;box-shadow:0 2px 6px rgba(0,0,0,0.3);">'
                f'{svg_content}</div>'
            )
        except Exception:
            pass

    c1, c2 = _BRAND_GRADIENTS.get(clean, ("#2563EB", "#1E293B"))
    display_label = clean[:4] if len(clean) > 4 and not clean.startswith("DEMO") else clean[:5]
    font_size = max(int(size_px * 0.32), 10)
    return (
        f'<div style="width:{size_px}px;height:{size_px}px;border-radius:22%;'
        f'background:linear-gradient(135deg, {c1}, {c2});border:1px solid rgba(255,255,255,0.18);'
        f'display:inline-flex;align-items:center;justify-content:center;'
        f'font-weight:800;font-size:{font_size}px;color:#FFFFFF;flex-shrink:0;'
        f'box-shadow:0 2px 6px rgba(0,0,0,0.25);letter-spacing:-0.03em;">'
        f'{escape(display_label)}</div>'
    )


def bank_header_html(
    ticker: str,
    company_name: str | None = None,
    *,
    size_px: int = 44,
) -> str:
    """Render bank logo icon + ticker + company name side-by-side with crisp typography."""
    logo = bank_logo_html(ticker, size_px=size_px)
    name_escaped = escape(company_name or "Company name unavailable")
    ticker_escaped = escape(str(ticker))
    return (
        f'<div style="display:flex;align-items:center;gap:12px;margin:.25rem 0 .5rem 0;">'
        f'{logo}'
        f'<div>'
        f'<div class="nusa-priority-ticker" style="margin:0;line-height:1.15;">{ticker_escaped}</div>'
        f'<div class="nusa-priority-company" style="margin:0;">{name_escaped}</div>'
        f'</div>'
        f'</div>'
    )

