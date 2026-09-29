"""Explainable cross-sectional ranking from documented Screener annual values."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import pandas as pd


_YEAR_FIELD = re.compile(r"^(?P<metric>[A-Za-z_][A-Za-z0-9_]*)\[(?P<year>\d{4})\]$")
MIN_COMPARABLE_COMPANIES = 4  # company plus at least three same-universe peers


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


def rank_anomalies(frame: pd.DataFrame) -> pd.DataFrame:
    """Rank unusual latest annual growth; return no score when peer evidence is thin.

    The score is a 0–100 cross-sectional research-priority percentile. It is not a
    fraud, safety, quality, or investment signal. Only fields actually returned
    by the Screener are eligible; no values are imputed.
    """
    output_columns = [
        "ticker", "company_name", "score", "primary_driver",
        "supporting_metric_changes", "components",
    ]
    if frame.empty or "ticker" not in frame.columns:
        return pd.DataFrame(columns=output_columns)

    pair_map = _annual_pairs(frame)
    growth_by_metric: dict[str, pd.Series] = {}
    periods: dict[str, str] = {}
    for metric, (prior_col, current_col, prior_year, current_year) in pair_map.items():
        prior = pd.to_numeric(frame[prior_col], errors="coerce")
        current = pd.to_numeric(frame[current_col], errors="coerce")
        valid = prior.notna() & current.notna() & prior.ne(0)
        growth = pd.Series(float("nan"), index=frame.index, dtype="float64")
        growth.loc[valid] = (current.loc[valid] / prior.loc[valid] - 1.0) * 100.0
        if int(growth.notna().sum()) >= MIN_COMPARABLE_COMPANIES:
            growth_by_metric[metric] = growth
            periods[metric] = f"{prior_year} to {current_year}"

    if not growth_by_metric:
        return pd.DataFrame(columns=output_columns)

    per_company: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for metric, growth in growth_by_metric.items():
        eligible = growth.dropna()
        median = float(eligible.median())
        deviations = (eligible - median).abs()
        # Percentile rank yields an interpretable 0–100 cross-sectional position.
        percentiles = deviations.rank(method="average", pct=True) * 100.0
        for index, change in eligible.items():
            others = eligible.drop(index)
            if len(others) < MIN_COMPARABLE_COMPANIES - 1:
                continue
            peer_median = float(others.median())
            contribution = float(percentiles.loc[index])
            per_company[index].append(
                {
                    "metric": metric,
                    "period": periods[metric],
                    "change_pct": round(float(change), 2),
                    "peer_median_change_pct": round(peer_median, 2),
                    "peer_count": int(len(others)),
                    "deviation_pct_points": round(abs(float(change) - peer_median), 2),
                    "contribution": round(contribution, 2),
                    "reason": (
                        f"{metric} changed {change:.2f}% versus a same-universe "
                        f"peer median of {peer_median:.2f}% ({len(others)} peers)."
                    ),
                }
            )

    records: list[dict[str, Any]] = []
    for index, components in per_company.items():
        if not components:
            continue
        components.sort(key=lambda item: (-item["contribution"], item["metric"]))
        original = frame.loc[index]
        records.append(
            {
                "ticker": str(original["ticker"]),
                "company_name": original.get("company_name"),
                "score": int(round(sum(c["contribution"] for c in components) / len(components))),
                "primary_driver": components[0]["metric"],
                "supporting_metric_changes": {
                    c["metric"]: c["change_pct"] for c in components
                },
                "components": components,
            }
        )
    return pd.DataFrame(records, columns=output_columns).sort_values(
        ["score", "ticker"], ascending=[False, True], ignore_index=True
    )
