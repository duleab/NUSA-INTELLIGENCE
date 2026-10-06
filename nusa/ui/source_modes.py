"""Truthful labels and ordering for the three explicit NUSA data modes."""

from __future__ import annotations


def source_mode_options(*, snapshot_available: bool) -> list[tuple[str, str]]:
    """List only available modes, preferring a local snapshot when present."""
    options = [
        ("demo", "DEMO/SAMPLE"),
        ("live", "LIVE SECTORS"),
    ]
    if snapshot_available:
        return [("cached_sectors", "SECTORS CACHED SNAPSHOT"), *options]
    return options


def format_excluded_metric_flags(flags: object) -> str:
    """Render scorer exclusions compactly in the Discovery results table."""
    if not isinstance(flags, list):
        return "—"
    labels = [
        f"{item['metric']}: {item['reason']}"
        for item in flags
        if isinstance(item, dict) and item.get("metric") and item.get("reason")
    ]
    return ", ".join(labels) if labels else "—"


def format_source_status(mode: str, retrieved_at: str | None = None) -> dict[str, str]:
    """Return a mode-specific badge and truthful explanatory copy."""
    if mode == "live":
        message = "LIVE SECTORS DATA — Explicit live Sectors API source."
        if retrieved_at:
            message += f" Retrieved {retrieved_at}."
        return {
            "badge": "LIVE SECTORS DATA",
            "message": message,
            "kind": "success",
        }
    if mode == "cached_sectors":
        retrieval = f" retrieved {retrieved_at}" if retrieved_at else " available locally"
        return {
            "badge": "SECTORS CACHED SNAPSHOT",
            "message": (
                "SECTORS CACHED SNAPSHOT — Sectors-origin data"
                f"{retrieval}. Not a live refresh."
            ),
            "kind": "info",
        }
    if mode in {"demo", "fixture"}:
        return {
            "badge": "DEMO/SAMPLE DATA",
            "message": "DEMO/SAMPLE DATA — Synthetic demonstration values. Not current market data.",
            "kind": "warning",
        }
    raise ValueError(f"Unsupported data mode: {mode}")
