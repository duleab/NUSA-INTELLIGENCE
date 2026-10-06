"""Explainable peer-relative scoring for annual financial changes."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from numbers import Real
from typing import Iterable, TypeGuard

import pandas as pd


_YEAR_FIELD = re.compile(r"^(?P<metric>[A-Za-z_][A-Za-z0-9_]*)\[(?P<year>\d{4})\]$")
MIN_COMPARABLE_COMPANIES = 4  # Company plus at least three same-universe peers.
REAL_SCORING_METRICS = (
    "earnings",
    "net_interest_income",
    "total_assets",
    "total_equity",
    "roa",
)
_ROA_METRICS = {"roa"}


def _annual_pairs(frame: pd.DataFrame) -> dict[str, tuple[str, str, str, str]]:
    years_by_metric: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for column in frame.columns:
        match = _YEAR_FIELD.match(str(column))
        if match:
            years_by_metric[match.group("metric")].append((int(match.group("year")), str(column)))
    pairs: dict[str, tuple[str, str, str, str]] = {}
    for metric, fields in years_by_metric.items():
        fields.sort()
        if len(fields) >= 2:
            (prior_year, prior_col), (current_year, current_col) = fields[-2:]
            pairs[metric] = (prior_col, current_col, str(prior_year), str(current_year))
    return pairs


def rank_anomalies(
    frame: pd.DataFrame,
    *,
    metric_allowlist: Iterable[str] | None = None,
) -> pd.DataFrame:
    """Rank peer-relative annual changes with transparent eligibility flags.

    Monetary metrics use ``(current - previous) / abs(previous) * 100``. A zero,
    sign transition, or dataset-relative small base makes that percentage
    ineligible for scoring; the raw signed monetary change remains in the output.
    ROA is a decimal ratio and is measured as a percentage-point change. The
    percentile contribution is calculated using the existing universe-deviation
    method and each peer reference excludes the subject company.
    """
    output_columns = [
        "ticker",
        "company_name",
        "score",
        "mean_eligible_contribution",
        "metric_coverage",
        "eligible_metric_count",
        "primary_driver",
        "primary_change",
        "primary_change_unit",
        "primary_peer_median",
        "primary_deviation",
        "supporting_metric_changes",
        "eligible_metrics",
        "excluded_metric_flags",
        "components",
    ]
    if frame.empty or "ticker" not in frame.columns:
        return pd.DataFrame(columns=output_columns)

    pair_map = _annual_pairs(frame)
    requested = set(metric_allowlist) if metric_allowlist is not None else set(pair_map)
    metrics = [metric for metric in pair_map if metric in requested]
    if not metrics:
        return pd.DataFrame(columns=output_columns)

    raw_components: dict[str, dict[str, dict[str, object]]] = {metric: {} for metric in metrics}
    eligible_changes: dict[str, pd.Series] = {}
    for metric in metrics:
        prior_col, current_col, prior_year, current_year = pair_map[metric]
        prior = pd.to_numeric(frame[prior_col], errors="coerce")
        current = pd.to_numeric(frame[current_col], errors="coerce")
        finite = prior.map(_is_finite_number) & current.map(_is_finite_number)
        if metric in _ROA_METRICS:
            changes = pd.Series(float("nan"), index=frame.index, dtype="float64")
            changes.loc[finite] = (current.loc[finite] - prior.loc[finite]) * 100.0
            unit = "percentage_points"
            thresholds = 0.0
        else:
            valid_prior = prior.loc[finite].astype(float).abs()
            thresholds = float(valid_prior.median()) * 0.01 if not valid_prior.empty else 0.0
            changes = pd.Series(float("nan"), index=frame.index, dtype="float64")
            eligible = finite & prior.ne(0) & prior.abs().ge(thresholds)
            eligible &= ~((prior < 0) & (current > 0))
            eligible &= ~((prior > 0) & (current < 0))
            changes.loc[eligible] = (
                (current.loc[eligible] - prior.loc[eligible])
                / prior.loc[eligible].abs()
                * 100.0
            )
            unit = "percent"

        finite_changes = changes.map(_is_finite_number)
        changes = changes.where(finite_changes)
        if int(changes.notna().sum()) >= MIN_COMPARABLE_COMPANIES:
            eligible_changes[metric] = changes

        for index in frame.index:
            has_values = bool(finite.loc[index])
            prior_value = float(prior.loc[index]) if has_values else None
            current_value = float(current.loc[index]) if has_values else None
            if has_values:
                assert prior_value is not None and current_value is not None
                raw_absolute_change = current_value - prior_value
            else:
                raw_absolute_change = None
            exclusion_reasons: list[str] = []
            edge_flags: list[str] = []
            if not has_values:
                exclusion_reasons.append("MISSING_OR_NON_NUMERIC_VALUE")
            elif metric not in _ROA_METRICS:
                assert prior_value is not None and current_value is not None
                if prior_value == 0:
                    exclusion_reasons.append("ZERO_BASE")
                if prior_value * current_value < 0:
                    exclusion_reasons.append("SIGN_TRANSITION")
                if thresholds > 0 and abs(prior_value) < thresholds:
                    exclusion_reasons.append("SMALL_BASE")
                if current_value == 0:
                    edge_flags.append("CURRENT_ZERO")
            change_value = changes.loc[index]
            scoring_eligible = bool(pd.notna(change_value))
            if has_values and metric not in _ROA_METRICS and not scoring_eligible:
                change_value = raw_absolute_change
            raw_components[metric][str(index)] = {
                "metric": metric,
                "period": f"{prior_year} to {current_year}",
                "change": float(change_value) if pd.notna(change_value) else None,
                "change_pct": (
                    float(change_value)
                    if scoring_eligible and unit == "percent"
                    else None
                ),
                "change_unit": unit if scoring_eligible or metric in _ROA_METRICS else "IDR",
                "absolute_change": (
                    raw_absolute_change
                    if has_values and metric not in _ROA_METRICS and not scoring_eligible
                    else None
                ),
                "previous_value": prior_value,
                "current_value": current_value,
                "scoring_eligible": scoring_eligible,
                "exclusion_reasons": exclusion_reasons,
                "exclusion_reason": exclusion_reasons[0] if exclusion_reasons else None,
                "edge_flags": edge_flags,
                "small_base_threshold": thresholds if metric not in _ROA_METRICS else None,
                "peer_median": None,
                "peer_median_change_pct": None,
                "peer_count": 0,
                "deviation": None,
                "deviation_pct_points": None,
                "contribution": None,
                "calculation": _calculation(metric, unit, thresholds, scoring_eligible),
            }

    # Per-metric peer references and percentile contributions use only eligible values.
    for metric, changes in eligible_changes.items():
        eligible = changes.dropna()
        universe_median = float(eligible.median())
        deviations = (eligible - universe_median).abs()
        contributions = deviations.rank(method="average", pct=True) * 100.0
        for index, change in eligible.items():
            others = eligible.drop(index)
            peer_median = float(others.median())
            component = raw_components[metric][str(index)]
            deviation = abs(float(change) - peer_median)
            component.update(
                {
                    "peer_median": peer_median,
                    "peer_median_change_pct": peer_median,
                    "peer_count": int(len(others)),
                    "deviation": deviation,
                    "deviation_pct_points": deviation,
                    "contribution": float(contributions.loc[index]),
                }
            )
        # eligible_changes contains only metrics with sufficient comparable data.
    for metric in metrics:
        if metric in eligible_changes:
            continue
        for index in frame.index:
            component = raw_components[metric][str(index)]
            if component["scoring_eligible"]:
                component["scoring_eligible"] = False
                component["exclusion_reasons"] = ["INSUFFICIENT_COMPARABLE_COMPANIES"]
                component["exclusion_reason"] = "INSUFFICIENT_COMPARABLE_COMPANIES"
                component["change_pct"] = None
                previous_value = _component_number(component, "previous_value")
                current_value = _component_number(component, "current_value")
                absolute_change = (
                    current_value - previous_value
                    if metric not in _ROA_METRICS
                    and previous_value is not None
                    and current_value is not None
                    else None
                )
                component["absolute_change"] = absolute_change
                component["change"] = (
                    absolute_change
                    if metric not in _ROA_METRICS
                    else component["change"]
                )
                component["change_unit"] = (
                    "IDR" if metric not in _ROA_METRICS else "percentage_points"
                )
                component["peer_median"] = None
                component["peer_median_change_pct"] = None
                component["peer_count"] = 0
                component["deviation"] = None
                component["deviation_pct_points"] = None
                component["contribution"] = None

    records: list[dict[str, object]] = []
    metric_count = len(metrics)
    for index, original in frame.iterrows():
        components = [raw_components[metric][str(index)] for metric in metrics]
        eligible_components = [
            item for item in components
            if item["scoring_eligible"]
            and _component_number(item, "contribution") is not None
        ]
        if not eligible_components:
            continue
        eligible_components.sort(
            key=lambda item: (
                -(_component_number(item, "contribution") or 0.0),
                str(item["metric"]),
            )
        )
        excluded = [item for item in components if not item["scoring_eligible"]]
        mean_contribution = sum(
            _component_number(item, "contribution") or 0.0
            for item in eligible_components
        ) / len(eligible_components)
        coverage = len(eligible_components) / metric_count
        # Coverage adjusts confidence without assigning an ineligible metric a zero component.
        composite = mean_contribution * coverage
        primary = eligible_components[0]
        records.append(
            {
                "ticker": str(original["ticker"]),
                "company_name": original.get("company_name"),
                "score": int(round(composite)),
                "mean_eligible_contribution": round(mean_contribution, 2),
                "metric_coverage": coverage,
                "eligible_metric_count": len(eligible_components),
                "primary_driver": str(primary["metric"]),
                "primary_change": primary["change"],
                "primary_change_unit": primary["change_unit"],
                "primary_peer_median": primary["peer_median"],
                "primary_deviation": primary["deviation"],
                "supporting_metric_changes": {
                    str(item["metric"]): item["change"] for item in eligible_components
                },
                "eligible_metrics": [str(item["metric"]) for item in eligible_components],
                "excluded_metric_flags": [
                    {
                        "metric": item["metric"],
                        "reason": item["exclusion_reason"],
                        "reasons": item["exclusion_reasons"],
                        "absolute_change": item["absolute_change"],
                        "change_unit": item["change_unit"],
                    }
                    for item in excluded
                ],
                "components": components,
            }
        )
    return pd.DataFrame(records, columns=output_columns).sort_values(
        ["score", "eligible_metric_count", "ticker"],
        ascending=[False, False, True],
        ignore_index=True,
    ) if records else pd.DataFrame(columns=output_columns)


def _is_finite_number(value: object) -> TypeGuard[Real]:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(float(value))


def _component_number(component: dict[str, object], key: str) -> float | None:
    value = component.get(key)
    return float(value) if _is_finite_number(value) else None


def _calculation(metric: str, unit: str, threshold: float, eligible: bool) -> str:
    if metric in _ROA_METRICS:
        return "change=(current_roa-previous_roa)*100; unit=percentage_points"
    if not eligible:
        return (
            "percentage change not used for scoring; absolute monetary change=current-previous; "
            f"exclusion threshold=1% of median absolute previous-year peer value ({threshold})"
        )
    return (
        "change_pct=((current-previous)/abs(previous))*100; "
        f"small-base threshold=1% of median absolute previous-year peer value ({threshold}); "
        "peer_median=median(other eligible banks' change); "
        "deviation=abs(change-peer_median); contribution=percentile_rank(abs(change-universe_median))*100"
    )
