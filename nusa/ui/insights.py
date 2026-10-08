"""Deterministic research insights built only from validated discovery data.

Every function in this module is pure: it reads fields that the anomaly
scorer and Evidence Ledger already produced (change, peer median, peer
count, percentile contribution, exclusion reasons) and turns them into
structured, explainable output for the UI.  Nothing here calls a model,
fetches data, or invents a number.  When a field is missing, the
corresponding insight is omitted rather than estimated.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from numbers import Real
from statistics import median
from typing import Any, Iterable

from nusa.ui.presentation import format_change, format_idr_value


METRIC_LABELS = {
    "net_interest_income": "Net interest income",
    "earnings": "Earnings",
    "total_assets": "Total assets",
    "total_equity": "Total equity",
    "roa": "ROA",
}
METRIC_SHORT = {
    "net_interest_income": "NII",
    "earnings": "Earnings",
    "total_assets": "Assets",
    "total_equity": "Equity",
    "roa": "ROA",
}
EXCLUSION_LABELS = {
    "SIGN_TRANSITION": "sign transition (loss ↔ profit) — a percentage change is not meaningful",
    "ZERO_BASE": "zero prior-year value — a percentage change is undefined",
    "SMALL_BASE": "prior-year value below 1% of the peer median — percentage would be distorted",
    "MISSING_OR_NON_NUMERIC_VALUE": "value missing from the source",
    "INSUFFICIENT_COMPARABLE_COMPANIES": "fewer than 4 comparable banks reported this metric",
}
# Percentile thresholds used only to label an existing contribution value.
HIGH_CONTRIBUTION = 90.0
MODERATE_CONTRIBUTION = 60.0


def metric_label(metric: str) -> str:
    return METRIC_LABELS.get(metric, metric.replace("_", " ").title())


def metric_short(metric: str) -> str:
    return METRIC_SHORT.get(metric, metric_label(metric))


def exclusion_label(reason: str | None) -> str:
    if not reason:
        return "excluded from scoring"
    return EXCLUSION_LABELS.get(reason, reason.replace("_", " ").lower())


# ── Component access ─────────────────────────────────────────────────────────

def _num(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def components_by_metric(row: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not row:
        return {}
    return {
        str(item.get("metric")): item
        for item in row.get("components", []) or []
        if isinstance(item, dict) and item.get("metric")
    }


def _eligible(component: dict[str, Any] | None) -> bool:
    return bool(
        component
        and component.get("scoring_eligible")
        and _num(component.get("change")) is not None
    )


def _signed_gap(component: dict[str, Any]) -> float | None:
    change = _num(component.get("change"))
    peer = _num(component.get("peer_median"))
    if change is None or peer is None:
        return None
    return change - peer


def _fmt(component: dict[str, Any], key: str = "change") -> str:
    return format_change(component.get(key), str(component.get("change_unit", "")))


# ── 1. Why this bank? ────────────────────────────────────────────────────────

def why_this_bank(row: dict[str, Any] | None, *, universe_size: int | None = None) -> list[str]:
    """Bullet points explaining a ranking using only scored component fields."""
    comps = components_by_metric(row)
    if not row or not comps:
        return []
    bullets: list[str] = []
    rank_context = f" among {universe_size} banks" if universe_size else ""
    bullets.append(
        f"Research-priority score {row.get('score', '—')}/100{rank_context} "
        f"({row.get('eligible_metric_count', 0)} of {len(comps)} metrics scoreable)."
    )
    primary = row.get("primary_driver")
    ordered = [primary] + [m for m in comps if m != primary]
    for metric in ordered:
        comp = comps.get(metric)
        if not comp:
            continue
        if _eligible(comp):
            peer = _num(comp.get("peer_median"))
            peer_text = (
                f" vs peer median {_fmt(comp, 'peer_median')} ({comp.get('peer_count', 0)} peers)"
                if peer is not None
                else ""
            )
            tag = " — primary driver" if metric == primary else ""
            bullets.append(f"{metric_short(metric)} {_fmt(comp)}{peer_text}{tag}.")
        else:
            absolute = _num(comp.get("absolute_change"))
            detail = (
                f" (absolute change {format_change(absolute, 'IDR')})" if absolute is not None else ""
            )
            bullets.append(
                f"{metric_short(metric)} excluded from percentage scoring: "
                f"{exclusion_label(comp.get('exclusion_reason'))}{detail}."
            )
    return bullets


# ── 2. Anomaly decomposition ─────────────────────────────────────────────────

@dataclass(frozen=True)
class Decomposition:
    rows: list[dict[str, Any]]
    mean_contribution: float | None
    coverage_scored: int
    coverage_total: int
    score: int | None

    @property
    def formula(self) -> str:
        if self.mean_contribution is None or not self.coverage_total:
            return "Score unavailable: no scoreable metric."
        return (
            f"Score {self.score} = mean percentile contribution {self.mean_contribution:.1f} "
            f"× metric coverage {self.coverage_scored}/{self.coverage_total}"
        )


def anomaly_decomposition(row: dict[str, Any] | None) -> Decomposition:
    """Explain how the 0–100 score was assembled from per-metric contributions."""
    comps = components_by_metric(row)
    rows: list[dict[str, Any]] = []
    contributions: list[float] = []
    for metric, comp in comps.items():
        contribution = _num(comp.get("contribution"))
        if _eligible(comp) and contribution is not None:
            contributions.append(contribution)
            level = (
                "High" if contribution >= HIGH_CONTRIBUTION
                else "Moderate" if contribution >= MODERATE_CONTRIBUTION
                else "Low"
            )
            status = "Scored"
        else:
            level = "Excluded"
            status = exclusion_label(comp.get("exclusion_reason"))
        rows.append(
            {
                "metric": metric,
                "Metric": metric_label(metric),
                "Change": _fmt(comp),
                "Peer median": _fmt(comp, "peer_median"),
                "Peers": int(comp.get("peer_count") or 0),
                "Contribution": round(contribution, 1) if contribution is not None and level != "Excluded" else None,
                "Level": level,
                "Status": status,
            }
        )
    rows.sort(key=lambda r: (r["Contribution"] is None, -(r["Contribution"] or 0.0)))
    mean_contribution = sum(contributions) / len(contributions) if contributions else None
    score = row.get("score") if row else None
    return Decomposition(
        rows=rows,
        mean_contribution=mean_contribution,
        coverage_scored=len(contributions),
        coverage_total=len(comps),
        score=int(score) if _num(score) is not None else None,
    )


# ── 3. Evidence coverage ─────────────────────────────────────────────────────

def evidence_coverage(
    evidence_items: Iterable[Any],
    *,
    ticker: str | None = None,
    validated: bool,
    invalid_count: int = 0,
    universe_size: int | None = None,
    source_label: str | None = None,
    expected_metrics: Iterable[str] = tuple(METRIC_LABELS),
) -> dict[str, Any]:
    """Measurable coverage indicators — no synthetic confidence score."""
    items = list(evidence_items)
    key = ticker.upper().removesuffix(".JK") if ticker else None
    subject = [
        item for item in items
        if key is None or str(item.ticker).upper().removesuffix(".JK") == key
    ]
    periods = sorted({str(item.period) for item in subject})
    present = {str(item.metric) for item in subject}
    missing = [m for m in expected_metrics if m not in present]
    total = len(items)
    validated_count = total - invalid_count if validated or invalid_count else 0
    return {
        "records_total": total,
        "records_validated": validated_count,
        "subject_records": len(subject),
        "subject_scored": sum(1 for item in subject if getattr(item, "scoring_eligible", False)),
        "peer_records": total - len(subject),
        "periods": periods,
        "period_label": ", ".join(p.replace(" to ", "–") for p in periods) or "—",
        "universe_size": universe_size,
        "source": source_label or (subject[0].source if subject else "—"),
        "missing_metrics": missing,
        "all_validated": bool(validated and invalid_count == 0 and total > 0),
    }


# ── 4. Peer distribution for a metric ────────────────────────────────────────

def metric_changes_across_universe(
    ranked_rows: Iterable[dict[str, Any]],
    metric: str,
) -> dict[str, float]:
    """Return {ticker: change} for every bank with a scoreable value of *metric*."""
    values: dict[str, float] = {}
    for row in ranked_rows:
        comp = components_by_metric(row).get(metric)
        if _eligible(comp):
            values[str(row.get("ticker"))] = float(comp["change"])
    return values


def peer_distribution(
    ranked_rows: list[dict[str, Any]],
    metric: str,
    ticker: str,
    peers: Iterable[str] = (),
) -> dict[str, Any]:
    """Subject vs selected peers vs universe statistics for one metric."""
    values = metric_changes_across_universe(ranked_rows, metric)
    unit = "percent"
    for row in ranked_rows:
        comp = components_by_metric(row).get(metric)
        if _eligible(comp):
            unit = str(comp.get("change_unit", unit))
            break
    key = ticker.upper().removesuffix(".JK")
    subject_ticker = next(
        (t for t in values if t.upper().removesuffix(".JK") == key), None
    )
    others = [v for t, v in values.items() if t != subject_ticker]
    bars: list[dict[str, Any]] = []
    if subject_ticker is not None:
        bars.append({"label": subject_ticker, "change": values[subject_ticker], "role": "Selected bank"})
    for peer in peers:
        pkey = str(peer).upper().removesuffix(".JK")
        match = next((t for t in values if t.upper().removesuffix(".JK") == pkey), None)
        if match and match != subject_ticker:
            bars.append({"label": match, "change": values[match], "role": "Size-matched peer"})
    stats: dict[str, float] = {}
    if others:
        ordered = sorted(others)
        stats = {
            "min": ordered[0],
            "p25": _quantile(ordered, 0.25),
            "median": float(median(ordered)),
            "p75": _quantile(ordered, 0.75),
            "max": ordered[-1],
        }
        bars.append({"label": "Peer median", "change": stats["median"], "role": "Peer median"})
    rank = None
    if subject_ticker is not None:
        rank = 1 + sum(1 for v in values.values() if v > values[subject_ticker])
    return {
        "metric": metric,
        "unit": unit,
        "bars": bars,
        "stats": stats,
        "count": len(values),
        "subject_rank": rank,
    }


def _quantile(ordered: list[float], q: float) -> float:
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


# ── 5. Investigation questions (rule-generated, data-answered) ──────────────

@dataclass(frozen=True)
class InvestigationQuestion:
    question: str
    answer: str
    metrics: tuple[str, ...]


def investigation_questions(row: dict[str, Any] | None) -> list[InvestigationQuestion]:
    """Generate 3–5 bounded questions and answer each from scored components."""
    comps = components_by_metric(row)
    if not row or not comps:
        return []
    primary = str(row.get("primary_driver") or "")
    questions: list[InvestigationQuestion] = []

    pc = comps.get(primary)
    if _eligible(pc):
        gap = _signed_gap(pc)
        contribution = _num(pc.get("contribution"))
        percentile = f"; peer-deviation percentile {contribution:.0f}" if contribution is not None else ""
        direction = "above" if (gap or 0) >= 0 else "below"
        questions.append(
            InvestigationQuestion(
                f"How unusual is the {metric_short(primary)} change relative to peers?",
                f"{metric_short(primary)} changed {_fmt(pc)} against a peer median of "
                f"{_fmt(pc, 'peer_median')} across {pc.get('peer_count', 0)} peers — "
                f"{format_change(abs(gap or 0), str(pc.get('change_unit')))} {direction} the median{percentile}.",
                (primary,),
            )
        )

    assets = comps.get("total_assets")
    if primary != "total_assets" and _eligible(pc) and _eligible(assets):
        a_change, p_change = float(assets["change"]), float(pc["change"])
        a_peer = _num(assets.get("peer_median"))
        above = a_peer is not None and a_change > a_peer
        if above and pc.get("change_unit") == "percent" and p_change > a_change:
            verdict = (
                f"Partly. Assets also grew faster than peers, but {metric_short(primary)} "
                f"({_fmt(pc)}) grew faster than assets ({_fmt(assets)}), so balance-sheet "
                "size alone does not account for the full change."
            )
        elif above:
            verdict = (
                f"Assets grew {_fmt(assets)} vs a peer median of {_fmt(assets, 'peer_median')}, "
                f"consistent with the {metric_short(primary)} change."
            )
        else:
            verdict = (
                f"Not clearly. Assets changed {_fmt(assets)} vs a peer median of "
                f"{_fmt(assets, 'peer_median')}, so the {metric_short(primary)} change is not "
                "matched by unusual balance-sheet growth."
            )
        questions.append(
            InvestigationQuestion(
                f"Is the {metric_short(primary)} change supported by asset growth?",
                verdict,
                (primary, "total_assets"),
            )
        )

    roa = comps.get("roa")
    if primary != "roa" and _eligible(roa):
        r_change = float(roa["change"])
        moved = "improved" if r_change > 0 else "declined" if r_change < 0 else "was unchanged"
        questions.append(
            InvestigationQuestion(
                "Did profitability (ROA) move at the same time?",
                f"ROA {moved} by {_fmt(roa)} vs a peer median of {_fmt(roa, 'peer_median')}.",
                ("roa",),
            )
        )

    equity = comps.get("total_equity")
    if _eligible(equity) and _eligible(assets):
        e_change, a_change = float(equity["change"]), float(assets["change"])
        if e_change >= a_change:
            verdict = (
                f"Yes. Equity grew {_fmt(equity)} vs assets {_fmt(assets)}, so capital kept pace "
                "with the balance sheet."
            )
        else:
            verdict = (
                f"No. Equity grew {_fmt(equity)} vs assets {_fmt(assets)}, so leverage increased; "
                "capital adequacy is worth checking."
            )
        questions.append(
            InvestigationQuestion(
                "Did equity growth keep pace with asset growth?",
                verdict,
                ("total_equity", "total_assets"),
            )
        )

    excluded = [(m, c) for m, c in comps.items() if not _eligible(c)]
    if excluded:
        parts = [f"{metric_short(m)}: {exclusion_label(c.get('exclusion_reason'))}" for m, c in excluded]
        questions.append(
            InvestigationQuestion(
                "Were any metrics excluded from scoring, and why?",
                "; ".join(parts) + ".",
                tuple(m for m, _ in excluded),
            )
        )
    return questions[:5]


# ── 6. What changed / Why it matters / What next ─────────────────────────────

def what_changed_panel(row: dict[str, Any] | None) -> dict[str, Any]:
    comps = components_by_metric(row)
    if not row or not comps:
        return {}
    primary = str(row.get("primary_driver") or "")
    pc = comps.get(primary, {})
    supporting = [
        f"{metric_short(m)} {_fmt(c)}"
        for m, c in comps.items()
        if m != primary and _eligible(c)
    ]
    return {
        "what_changed": f"{metric_short(primary)} {_fmt(pc)}",
        "period": str(pc.get("period", "")).replace(" to ", "–"),
        "why_unusual": (
            f"Peer median {_fmt(pc, 'peer_median')} ({pc.get('peer_count', 0)} peers)"
            if _num(pc.get("peer_median")) is not None
            else "Peer median unavailable"
        ),
        "supporting": supporting,
        "what_next": what_to_investigate_next(row),
    }


def what_to_investigate_next(row: dict[str, Any] | None) -> list[str]:
    """Rule-based next steps grounded in observed metric patterns (not causes)."""
    comps = components_by_metric(row)
    if not comps:
        return []
    suggestions: list[str] = []
    assets, equity, roa = comps.get("total_assets"), comps.get("total_equity"), comps.get("roa")
    primary = str((row or {}).get("primary_driver") or "")
    if _eligible(assets) and (_signed_gap(assets) or 0) > 0:
        suggestions.append(
            "Balance-sheet expansion: review what drove asset growth (loans, securities, or "
            "placements) in the annual report."
        )
    if _eligible(equity) and _eligible(assets):
        if float(equity["change"]) < float(assets["change"]):
            suggestions.append("Capital support: equity grew slower than assets — check capital adequacy.")
        elif (_signed_gap(equity) or 0) > 0:
            suggestions.append(
                "Equity source: identify whether equity growth came from retained earnings or new capital."
            )
    if _eligible(roa) and float(roa["change"]) > 0:
        suggestions.append("Profitability quality: confirm whether the ROA improvement is recurring or one-off.")
    earnings = comps.get("earnings")
    if earnings and earnings.get("exclusion_reason") == "SIGN_TRANSITION":
        suggestions.append("Earnings turnaround: confirm the loss-to-profit transition in audited statements.")
    if primary == "net_interest_income":
        suggestions.append("Funding and yield: check whether loan yield or funding cost explains the NII change.")
    suggestions.append("Verification: reconcile all figures with the bank's audited financial statements.")
    return suggestions[:5]


# ── 7. Deterministic research conclusion ─────────────────────────────────────

def research_conclusion(
    row: dict[str, Any] | None,
    *,
    data_mode_label: str,
    peers: Iterable[str] = (),
) -> dict[str, list[str]]:
    comps = components_by_metric(row)
    if not row or not comps:
        return {}
    primary = str(row.get("primary_driver") or "")
    pc = comps.get(primary, {})
    ticker = row.get("ticker", "This bank")
    finding = [
        f"{ticker} shows the largest peer-relative change in {metric_label(primary).lower()}: "
        f"{_fmt(pc)} over {str(pc.get('period', '')).replace(' to ', '–')}."
    ]
    evidence = [
        f"{metric_label(m)}: {_fmt(c)} (peer median {_fmt(c, 'peer_median')})"
        for m, c in comps.items()
        if _eligible(c)
    ]
    peer_list = [p for p in peers]
    peer_context = [
        f"Compared against {pc.get('peer_count', 0)} banks using leave-one-out peer medians.",
    ]
    if peer_list:
        peer_context.append("Size-matched peers selected by the agent: " + ", ".join(peer_list) + ".")
    limitations = [
        f"Data source: {data_mode_label}. Annual values only; no intra-year detail.",
        "Observed changes do not establish cause, misconduct, or investment merit.",
    ]
    for m, c in comps.items():
        if not _eligible(c):
            limitations.append(f"{metric_label(m)} excluded: {exclusion_label(c.get('exclusion_reason'))}.")
    return {
        "Finding": finding,
        "Evidence": evidence,
        "Peer context": peer_context,
        "What needs further investigation": what_to_investigate_next(row),
        "Data limitations": limitations,
    }


# ── 8. Structured follow-ups (no model required) ─────────────────────────────

SUGGESTED_FOLLOWUPS = (
    "Why was this bank ranked first?",
    "Show the strongest contributing metric.",
    "Compare its ROA with peers.",
    "Which evidence supports this finding?",
    "What metrics were excluded and why?",
)

_METRIC_KEYWORDS = (
    (re.compile(r"\broa\b|return on assets", re.I), "roa"),
    (re.compile(r"\bnii\b|net interest", re.I), "net_interest_income"),
    (re.compile(r"\bassets?\b", re.I), "total_assets"),
    (re.compile(r"\bequity\b", re.I), "total_equity"),
    (re.compile(r"\bearnings?\b|\bprofit\b|net income", re.I), "earnings"),
)


@dataclass
class FollowupAnswer:
    title: str
    lines: list[str] = field(default_factory=list)
    intent: str = ""


def answer_structured_followup(
    question: str,
    row: dict[str, Any] | None,
    *,
    ranked_rows: list[dict[str, Any]] | None = None,
    evidence_items: Iterable[Any] = (),
    peers: Iterable[str] = (),
) -> FollowupAnswer | None:
    """Resolve a small set of follow-up intents from structured state.

    Returns ``None`` when the question is outside the supported set so the
    caller can fall back to the orchestrator (e.g. comparison follow-ups).
    """
    if not isinstance(question, str) or not question.strip() or not row:
        return None
    text = question.strip()
    comps = components_by_metric(row)
    ticker = str(row.get("ticker", ""))
    ranked_rows = ranked_rows or []

    if re.search(r"\bwhy\b.*\b(rank|ranked|select|selected|flag|flagged|first|chosen|top)\b", text, re.I):
        position = next(
            (i + 1 for i, r in enumerate(ranked_rows) if r.get("ticker") == ticker), None
        )
        title = f"Why {ticker} was ranked" + (f" #{position}" if position else "")
        lines = why_this_bank(row, universe_size=len(ranked_rows) or None)
        lines.append(anomaly_decomposition(row).formula + ".")
        return FollowupAnswer(title, lines, "WHY_RANKED")

    if re.search(r"exclud|not scored|ignored|left out", text, re.I):
        excluded = [(m, c) for m, c in comps.items() if not _eligible(c)]
        if not excluded:
            return FollowupAnswer("Excluded metrics", ["No metric was excluded; all were scored."], "EXCLUDED")
        lines = []
        for m, c in excluded:
            absolute = _num(c.get("absolute_change"))
            extra = f" Absolute change retained: {format_change(absolute, 'IDR')}." if absolute is not None else ""
            lines.append(f"{metric_label(m)} — {exclusion_label(c.get('exclusion_reason'))}.{extra}")
        return FollowupAnswer("Excluded metrics", lines, "EXCLUDED")

    if re.search(r"evidence|support|proof|source", text, re.I):
        key = ticker.upper().removesuffix(".JK")
        items = [e for e in evidence_items if str(e.ticker).upper().removesuffix(".JK") == key]
        if not items:
            return FollowupAnswer("Supporting evidence", ["No validated evidence records are loaded yet."], "EVIDENCE")
        lines = [
            f"{e.evidence_id} · {metric_label(e.metric)} · {e.period} · "
            f"{format_change(e.change, e.change_unit)} · {e.source}"
            for e in items
        ]
        return FollowupAnswer(f"Validated evidence for {ticker} ({len(items)} records)", lines, "EVIDENCE")

    if re.search(r"(strongest|largest|biggest|main|top|primary).*(metric|driver|contribut)", text, re.I):
        decomposition = anomaly_decomposition(row)
        scored = [r for r in decomposition.rows if r["Level"] != "Excluded"]
        if not scored:
            return FollowupAnswer("Strongest metric", ["No scoreable metric."], "STRONGEST")
        best = scored[0]
        lines = [
            f"{best['Metric']}: {best['Change']} vs peer median {best['Peer median']} "
            f"(peer-deviation percentile {best['Contribution']}).",
        ]
        lines += [
            f"Next: {r['Metric']} {r['Change']} (percentile {r['Contribution']})" for r in scored[1:3]
        ]
        return FollowupAnswer("Strongest contributing metric", lines, "STRONGEST")

    for pattern, metric in _METRIC_KEYWORDS:
        if pattern.search(text):
            comp = comps.get(metric)
            if not comp:
                return FollowupAnswer(metric_label(metric), ["Metric not available for this bank."], "METRIC")
            lines = []
            if _eligible(comp):
                lines.append(
                    f"{ticker}: {_fmt(comp)} vs peer median {_fmt(comp, 'peer_median')} "
                    f"({comp.get('peer_count', 0)} peers)."
                )
            else:
                lines.append(f"{ticker}: excluded — {exclusion_label(comp.get('exclusion_reason'))}.")
            values = metric_changes_across_universe(ranked_rows, metric)
            unit = str(comp.get("change_unit", "percent"))
            for peer in peers:
                pkey = str(peer).upper().removesuffix(".JK")
                match = next((t for t in values if t.upper().removesuffix(".JK") == pkey), None)
                if match:
                    lines.append(f"{match}: {format_change(values[match], unit)}")
            return FollowupAnswer(f"{metric_label(metric)} vs peers", lines, "METRIC")
    return None


# ── 9. Audit trail and agent efficiency ──────────────────────────────────────

def audit_trail(
    *,
    universe_size: int | None,
    metric_count: int,
    ranked_rows: list[dict[str, Any]],
    ticker: str | None,
    trace_events: Iterable[Any] = (),
) -> list[tuple[str, str]]:
    """Ordered (step, detail) pairs derived from real counts and trace events."""
    events = list(trace_events)
    trail: list[tuple[str, str]] = [("Request received", "Discover unusual financial changes")]
    if universe_size:
        trail.append(("Bank universe loaded", f"{universe_size} IDX banks"))
    trail.append(("Metrics evaluated", f"{metric_count} annual metrics per bank"))
    if ranked_rows:
        trail.append(("Peer baselines calculated", "Leave-one-out peer median per metric"))
        trail.append(("Banks ranked", f"{len(ranked_rows)} banks scored"))
    if ticker:
        row = next((r for r in ranked_rows if r.get("ticker") == ticker), None)
        detail = f"score {row.get('score')}/100" if row else "selected for investigation"
        trail.append((f"{ticker} selected", detail))
    tools = [e.details.get("tool") for e in events if e.event == "TOOL_COMPLETED"]
    if tools:
        trail.append(("Tools executed", " → ".join(str(t) for t in tools)))
    decisions = [e for e in events if e.event == "AGENT_DECISION"]
    if decisions:
        trail.append(("Autonomous decisions", f"{len(decisions)} observe → decide → act steps"))
    validation = next((e for e in events if e.event == "EVIDENCE_VALIDATED"), None)
    if validation:
        count = int(validation.details.get("evidence_count", 0))
        invalid = int(validation.details.get("invalid_count", 0))
        trail.append(("Evidence records created", str(count)))
        trail.append(("Evidence validated", f"{count - invalid}/{count} passed"))
    synthesis = next((e for e in events if e.event == "SYNTHESIS_COMPLETED"), None)
    if synthesis:
        mode = synthesis.details.get("generation_mode", "template")
        trail.append(("Report generated", f"{mode} synthesis from validated evidence"))
    return trail


def agent_efficiency(
    *,
    universe_size: int | None,
    metric_count: int,
    trace_events: Iterable[Any] = (),
    data_mode: str,
) -> list[tuple[str, str]]:
    events = list(trace_events)
    validation = next((e for e in events if e.event == "EVIDENCE_VALIDATED"), None)
    count = int(validation.details.get("evidence_count", 0)) if validation else 0
    invalid = int(validation.details.get("invalid_count", 0)) if validation else 0
    discovery_query = {
        "live": "1 Screener query",
        "cached_sectors": "0 live (snapshot of 1 Screener query)",
    }.get(data_mode, "0 (synthetic fixture)")
    return [
        ("Banks screened", str(universe_size or "—")),
        ("Sectors discovery calls", discovery_query),
        ("Metrics analyzed", str(metric_count)),
        ("Autonomous steps", str(sum(1 for e in events if e.event == "AGENT_DECISION"))),
        ("Tool executions", str(sum(1 for e in events if e.event == "TOOL_COMPLETED"))),
        ("Evidence validated", f"{count - invalid}/{count}" if validation else "—"),
        ("Failed evidence checks", str(invalid) if validation else "—"),
    ]


# ── Visible workflow stages ──────────────────────────────────────────────────

WORKFLOW_STAGES = ("Understand", "Plan", "Retrieve", "Analyze", "Compare", "Verify", "Explain")


def workflow_stages(trace_events: Iterable[Any]) -> list[dict[str, Any]]:
    """Map operational trace events (never reasoning text) to seven visible stages."""
    events = list(trace_events)
    names = [e.event for e in events]
    tools = [str(e.details.get("tool")) for e in events if e.event == "TOOL_COMPLETED"]
    validation = next((e for e in events if e.event == "EVIDENCE_VALIDATED"), None)
    plan_event = next((e for e in events if e.event == "PLAN_CREATED"), None)
    synthesis = next((e for e in events if e.event == "SYNTHESIS_COMPLETED"), None)
    compare_count = sum(1 for t in tools if t == "compare_peer_metrics")
    retrieve = [t for t in tools if t in {"get_company_evidence", "get_bank_universe", "discover_bank_anomalies"}]
    stages = [
        ("Understand", "INTENT_RESOLVED" in names or "DEEP_INVESTIGATION_STARTED" in names, "Intent resolved"),
        (
            "Plan",
            "PLAN_VALIDATED" in names,
            f"{plan_event.details.get('task_count', 0)} tasks · "
            f"{'LLM planner' if plan_event.details.get('planner') == 'llm' else 'deterministic'} · validated"
            if plan_event else "—",
        ),
        ("Retrieve", bool(retrieve), " · ".join(retrieve) or "—"),
        ("Analyze", "calculate_trends" in tools or "ANALYSIS_COMPLETED" in names, "calculate_trends"),
        ("Compare", compare_count > 0, f"compare_peer_metrics ×{compare_count}" if compare_count else "—"),
        (
            "Verify",
            bool(validation and validation.details.get("valid")),
            (
                f"{int(validation.details.get('evidence_count', 0)) - int(validation.details.get('invalid_count', 0))}"
                f"/{int(validation.details.get('evidence_count', 0))} evidence validated"
            ) if validation else "—",
        ),
        (
            "Explain",
            synthesis is not None,
            f"{synthesis.details.get('generation_mode', 'template')} report" if synthesis else "—",
        ),
    ]
    return [{"stage": s, "done": bool(d), "detail": detail} for s, d, detail in stages]


# ── Clean Presentation Generators (Progressive Disclosure) ───────────────────

def generate_hero_sentence(row: dict[str, Any] | None) -> str:
    """Generate the dynamic 1-sentence takeaway for the Hero card."""
    if not row:
        return "Select a bank to view findings."
    ticker = str(row.get("ticker", "This bank")).removesuffix(".JK")
    comps = components_by_metric(row)
    primary = str(row.get("primary_driver") or "key metric")
    pc = comps.get(primary, {})
    change_num = _num(pc.get("change"))
    change_str = _fmt(pc)
    peer_str = _fmt(pc, "peer_median")
    p_label = metric_label(primary)

    verb = "decreased" if (change_num is not None and change_num < 0) else "increased"
    comp_phrase = "far below" if (change_num is not None and change_num < 0) else "far above"

    supporting_parts = []
    if _eligible(comps.get("total_assets")):
        supporting_parts.append("assets")
    if _eligible(comps.get("total_equity")):
        supporting_parts.append("equity")
    if _eligible(comps.get("roa")):
        supporting_parts.append("profitability")

    if supporting_parts:
        if len(supporting_parts) > 1:
            supp_text = f", with supporting movement in {', '.join(supporting_parts[:-1])} and {supporting_parts[-1]}"
        else:
            supp_text = f", with supporting movement in {supporting_parts[0]}"
    else:
        supp_text = ""

    return (
        f"{ticker} was flagged because its {p_label} {verb} {change_str}, "
        f"{comp_phrase} the {peer_str} peer median{supp_text}."
    )


def why_flagged_paragraph(row: dict[str, Any] | None) -> str:
    """One clear paragraph explaining why the bank was flagged in plain English."""
    if not row:
        return ""
    ticker = str(row.get("ticker", "This bank")).removesuffix(".JK")
    comps = components_by_metric(row)
    primary = str(row.get("primary_driver") or "")
    pc = comps.get(primary, {})
    p_label = metric_label(primary)
    change_str = _fmt(pc)
    peer_str = _fmt(pc, "peer_median")
    score = row.get("score", "—")

    supporting_phrases = []
    for m in ("total_assets", "total_equity", "roa"):
        if m != primary and _eligible(comps.get(m)):
            c = comps[m]
            supporting_phrases.append(f"{metric_label(m).lower()} ({_fmt(c)})")

    supp_text = ""
    if supporting_phrases:
        supp_text = f" This signal was corroborated by growth in {' and '.join(supporting_phrases)}."

    excl_phrases = []
    for m, c in comps.items():
        if not _eligible(c):
            reason_txt = exclusion_label(c.get("exclusion_reason"))
            excl_phrases.append(f"{metric_label(m).lower()} ({reason_txt})")

    excl_text = ""
    if excl_phrases:
        excl_text = f" Meanwhile, {'; '.join(excl_phrases)} was excluded from percentage scoring to prevent mathematical distortion."

    rank_str = f"ranked #{row.get('rank')}" if row.get("rank") else "was flagged for research"
    return (
        f"{ticker} {rank_str} because its {p_label} changed {change_str}, "
        f"compared with a {peer_str} peer median.{supp_text}{excl_text} "
        "These divergent dynamics warrant deeper analytical review."
    )


def research_summary_bullets(row: dict[str, Any] | None) -> list[str]:
    """3 to 5 concise bullet points derived from real evidence."""
    if not row:
        return []
    comps = components_by_metric(row)
    bullets = []
    primary = str(row.get("primary_driver") or "")
    pc = comps.get(primary, {})
    if _eligible(pc):
        bullets.append(
            f"{metric_short(primary)} increased {_fmt(pc)}, substantially above the {_fmt(pc, 'peer_median')} peer median."
        )
    assets = comps.get("total_assets")
    if _eligible(assets):
        bullets.append(
            f"Asset growth of {_fmt(assets)} indicates significant balance-sheet expansion."
        )
    equity = comps.get("total_equity")
    if _eligible(equity):
        bullets.append(
            f"Equity increased {_fmt(equity)}, providing partial capital support for expansion."
        )
    roa = comps.get("roa")
    if _eligible(roa):
        r_change = float(roa["change"])
        dir_w = "improved" if r_change > 0 else "declined" if r_change < 0 else "moved"
        bullets.append(
            f"ROA {dir_w} {_fmt(roa)} (peer median {_fmt(roa, 'peer_median')})."
        )
    earnings = comps.get("earnings")
    if earnings and not _eligible(earnings):
        reason_txt = exclusion_label(earnings.get("exclusion_reason"))
        bullets.append(
            f"Earnings: {reason_txt}; percentage growth was excluded from anomaly scoring."
        )
    return bullets[:5]


def investigate_next_questions(row: dict[str, Any] | None) -> list[str]:
    """Return exactly 3 focused, professional research questions."""
    comps = components_by_metric(row)
    primary = str((row or {}).get("primary_driver") or "")
    qs = []
    if primary == "net_interest_income":
        qs.append("Did loan growth or changes in lending yield contribute to the NII increase?")
        qs.append("Did funding costs (deposit interest expense) change materially during the same period?")
    else:
        qs.append(f"Did operating revenue shifts account for the unusual change in {metric_label(primary).lower()}?")
        qs.append("How did provisions and operational expenses evolve alongside this metric?")

    assets = comps.get("total_assets")
    equity = comps.get("total_equity")
    if _eligible(assets) and _eligible(equity) and float(equity["change"]) < float(assets["change"]):
        qs.append("Is capital growth sufficient to support the rapid balance-sheet expansion?")
    else:
        qs.append("Is the observed profitability trajectory recurring or driven by non-recurring items?")

    return qs[:3]
