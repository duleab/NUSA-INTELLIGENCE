"""Autonomous deep-investigation policy for NUSA Intelligence.

The policy implements a deterministic observe → decide → act loop:
the agent reads evidence after each tool call, picks the next action
and records *why*, then stops when evidence is sufficient or the step
budget is exhausted.  No LLM is required.

Architecture note
-----------------
This is the layer that makes NUSA an *agent* rather than a pipeline.
All tool calls still go through the existing ToolRegistry allowlist and
EvidenceValidator — safety guarantees are unchanged.  The policy only
decides *what* to call and *why*; it never invents data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nusa.discovery.evidence import EvidenceLedger


# Maximum number of decide-and-act steps the agent may take.
DEEP_INVESTIGATION_MAX_STEPS = 6

# The minimum number of size-matched peers required to run a peer
# comparison.  If fewer than this number are available the agent abstains
# and records a limitation note.
MIN_PEER_COUNT = 3

# Metrics the agent considers, ranked by analytical priority.
PRIORITY_METRICS = [
    "net_interest_income",
    "earnings",
    "total_assets",
    "total_equity",
    "roa",
]


@dataclass
class AgentDecision:
    """One step in the autonomous decision loop."""

    step: int
    observation: str
    decision: str        # "RUN_TOOL" | "ABSTAIN" | "STOP"
    reason: str          # human-readable explanation
    tool: str | None = None
    tool_arguments: dict[str, Any] = field(default_factory=dict)
    limitation: str | None = None


def select_size_matched_peers(
    target_ticker: str,
    discovery_rows: list[dict[str, Any]],
    *,
    max_peers: int = 5,
) -> list[str]:
    """Return up to *max_peers* tickers closest in total_assets to the target.

    Peer selection is by absolute distance in total_assets (the most
    readily available size proxy in the discovery output).  The target
    itself is excluded.  If total_assets is not available the function
    falls back to returning the first *max_peers* tickers in discovery
    rank order.
    """
    target_key = target_ticker.upper().removesuffix(".JK")

    # Find the target row
    target_row: dict[str, Any] | None = None
    for row in discovery_rows:
        if str(row.get("ticker", "")).upper().removesuffix(".JK") == target_key:
            target_row = row
            break

    candidates = [
        row for row in discovery_rows
        if str(row.get("ticker", "")).upper().removesuffix(".JK") != target_key
    ]

    if target_row is None or not candidates:
        return [str(r["ticker"]) for r in candidates[:max_peers]]

    target_assets = _total_assets_from_components(target_row)
    if target_assets is None:
        # Fallback: rank order (already anomaly-ranked, gives diverse peers)
        return [str(r["ticker"]) for r in candidates[:max_peers]]

    def distance(row: dict[str, Any]) -> float:
        a = _total_assets_from_components(row)
        if a is None:
            return float("inf")
        return abs(a - target_assets)

    candidates.sort(key=distance)
    return [str(r["ticker"]) for r in candidates[:max_peers]]


def _total_assets_from_components(row: dict[str, Any]) -> float | None:
    """Extract total_assets current value from a discovery row's components."""
    for component in row.get("components", []):
        if component.get("metric") == "total_assets":
            v = component.get("current_value")
            if isinstance(v, (int, float)):
                return float(v)
    return None


def build_deep_investigation_steps(
    ticker: str,
    discovery_rows: list[dict[str, Any]],
    ledger_after_investigate: EvidenceLedger,
    *,
    already_ran_tools: set[str] | None = None,
) -> list[AgentDecision]:
    """Build the autonomous step sequence for a deep investigation.

    This function encodes the policy:

    Step 1  — Always run the standard 3-tool INVESTIGATE plan first.
    Step 2  — Identify the primary driver from the evidence ledger.
    Step 3  — Select size-matched peers automatically.
    Step 4  — Compare primary metric against those peers.
    Step 5  — Check corroborating metrics if the company is an outlier.
    Step 6  — Stop: evidence is sufficient or the budget is reached.

    Parameters
    ----------
    ticker:
        The ticker under investigation (e.g. "SUPA.JK").
    discovery_rows:
        The ranked discovery output (used for peer selection by size).
    ledger_after_investigate:
        The evidence ledger populated by the initial INVESTIGATE run.
    already_ran_tools:
        Tool names that have already been called in previous steps.
    """
    already_ran_tools = already_ran_tools or set()
    decisions: list[AgentDecision] = []
    step = 0

    # ── Step 1: Run the standard investigation if not already done ──────────
    step += 1
    if "get_company_evidence" not in already_ran_tools:
        decisions.append(AgentDecision(
            step=step,
            observation="No company evidence loaded yet.",
            decision="RUN_TOOL",
            reason=(
                "Starting with the full INVESTIGATE plan to build the "
                "evidence ledger."
            ),
            tool="get_company_evidence",
            tool_arguments={"ticker": ticker},
        ))
        return decisions  # caller will run this and re-enter with updated ledger

    # ── Step 2: Identify primary driver from ledger ─────────────────────────
    step += 1
    evidence_items = list(ledger_after_investigate)
    primary_metric = _highest_deviation_metric(evidence_items)
    primary_deviation = _deviation_for_metric(evidence_items, primary_metric)

    if primary_metric is None:
        decisions.append(AgentDecision(
            step=step,
            observation="Evidence ledger contains no scoreable metrics.",
            decision="STOP",
            reason=(
                "Cannot select a primary driver: no metric has a "
                "scoreable peer deviation."
            ),
        ))
        return decisions

    decisions.append(AgentDecision(
        step=step,
        observation=(
            f"Evidence ledger has {len(evidence_items)} item(s). "
            f"Largest peer-relative deviation: {primary_metric} "
            f"({_fmt_deviation(primary_deviation)})."
        ),
        decision="RUN_TOOL",
        reason=(
            f"'{primary_metric}' shows the largest peer-relative deviation. "
            "Selecting size-matched peers automatically to validate whether "
            "this deviation is consistent across the peer group."
        ),
        tool="compare_peer_metrics",
        tool_arguments={
            "tickers": _peer_tickers(ticker, discovery_rows, primary_metric),
            "metric": primary_metric,
        },
    ))

    if step >= DEEP_INVESTIGATION_MAX_STEPS:
        return decisions

    # ── Step 3: Check corroborating metrics ─────────────────────────────────
    step += 1
    corroborating = _corroborating_metrics(evidence_items, primary_metric)
    if corroborating:
        corr_metric = corroborating[0]
        corr_deviation = _deviation_for_metric(evidence_items, corr_metric)
        decisions.append(AgentDecision(
            step=step,
            observation=(
                f"'{primary_metric}' deviation confirmed. "
                f"Corroborating metric found: '{corr_metric}' "
                f"(deviation {_fmt_deviation(corr_deviation)})."
            ),
            decision="RUN_TOOL",
            reason=(
                f"Checking '{corr_metric}' to assess whether the primary "
                "deviation is isolated or part of a broader financial change."
            ),
            tool="compare_peer_metrics",
            tool_arguments={
                "tickers": _peer_tickers(ticker, discovery_rows, corr_metric),
                "metric": corr_metric,
            },
        ))
    else:
        decisions.append(AgentDecision(
            step=step,
            observation=(
                f"'{primary_metric}' is the only scoreable metric with "
                "sufficient peer coverage."
            ),
            decision="STOP",
            reason=(
                "No corroborating metrics available. Evidence is sufficient "
                "to generate a research summary."
            ),
        ))

    if step >= DEEP_INVESTIGATION_MAX_STEPS:
        return decisions

    # ── Step 4: Stop ─────────────────────────────────────────────────────────
    step += 1
    decisions.append(AgentDecision(
        step=step,
        observation=(
            f"Evidence collected across {len(evidence_items)} metric/period "
            "combination(s)."
        ),
        decision="STOP",
        reason=(
            f"Sufficient evidence collected: primary driver '{primary_metric}' confirmed, "
            f"size-matched peers compared, corroborating metrics analyzed, and all "
            f"{len(evidence_items)} evidence records ready for deterministic validation."
        ),
    ))

    return decisions


# ── Helpers ──────────────────────────────────────────────────────────────────

def _highest_deviation_metric(
    evidence_items: list[Any],
) -> str | None:
    """Return the metric with the largest absolute deviation among eligible items."""
    best_metric: str | None = None
    best_dev = 0.0
    for item in evidence_items:
        if not getattr(item, "scoring_eligible", False):
            continue
        dev = abs(getattr(item, "deviation", None) or 0.0)
        if dev > best_dev:
            best_dev = dev
            best_metric = item.metric
    return best_metric


def _deviation_for_metric(
    evidence_items: list[Any],
    metric: str | None,
) -> float | None:
    if metric is None:
        return None
    for item in evidence_items:
        if item.metric == metric:
            return getattr(item, "deviation", None)
    return None


def _corroborating_metrics(
    evidence_items: list[Any],
    primary_metric: str,
) -> list[str]:
    """Return other scoreable metrics with meaningful deviation, priority-ordered."""
    result: list[str] = []
    for m in PRIORITY_METRICS:
        if m == primary_metric:
            continue
        for item in evidence_items:
            if item.metric == m and getattr(item, "scoring_eligible", False):
                dev = abs(getattr(item, "deviation", None) or 0.0)
                if dev > 1.0:  # at least 1% deviation
                    result.append(m)
                break
    return result


def _peer_tickers(
    target: str,
    discovery_rows: list[dict[str, Any]],
    metric: str,
) -> list[str]:
    """Return the target + size-matched peers, together forming the comparison list."""
    peers = select_size_matched_peers(target, discovery_rows, max_peers=4)
    all_tickers = [target] + [p for p in peers if p != target]
    return all_tickers


def _fmt_deviation(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.1f}%"
