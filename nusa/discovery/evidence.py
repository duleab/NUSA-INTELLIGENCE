"""Structured, validated provenance for deterministic Discovery findings."""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from numbers import Real
from typing import Any, Iterable

import pandas as pd


_ANNUAL_PERIOD = re.compile(r"^(?P<previous>\d{4}) to (?P<current>\d{4})$")
_ALLOWED_DATA_MODES = {"live", "cached", "fixture", "synthetic", "unknown"}
_NUMERIC_FIELDS = (
    "current_value",
    "previous_value",
    "change",
    "peer_median",
    "peer_count",
    "deviation",
)


@dataclass(frozen=True)
class Evidence:
    """One auditable metric comparison; values are copied from Discovery results."""

    ticker: str
    metric: str
    period: str
    source: str
    source_endpoint: str
    retrieved_at: str
    calculation: str
    data_mode: str
    company_name: str | None = None
    current_value: int | float | None = None
    previous_value: int | float | None = None
    change: int | float | None = None
    peer_median: int | float | None = None
    peer_count: int | None = None
    deviation: int | float | None = None
    evidence_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def __post_init__(self) -> None:
        if isinstance(self.ticker, str):
            object.__setattr__(self, "ticker", self.ticker.strip().upper())
        if isinstance(self.metric, str):
            object.__setattr__(self, "metric", self.metric.strip())

    def to_dict(self) -> dict[str, Any]:
        """Return the stable, JSON-compatible evidence schema."""
        return asdict(self)


class EvidenceValidator:
    """Validate provenance, period alignment, and numeric integrity."""

    def validate_required_fields(self, evidence: Evidence) -> list[str]:
        errors: list[str] = []
        for name in (
            "evidence_id",
            "ticker",
            "metric",
            "period",
            "source",
            "source_endpoint",
            "retrieved_at",
            "calculation",
            "data_mode",
        ):
            value = getattr(evidence, name)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{name} is required")
        for name in ("current_value", "previous_value", "change"):
            if getattr(evidence, name) is None:
                errors.append(f"{name} is required")
        return errors

    def validate(self, evidence: Evidence, expected_ticker: str | None = None) -> list[str]:
        errors = self.validate_required_fields(evidence)
        if expected_ticker is not None:
            expected = expected_ticker.strip().upper()
            if evidence.ticker != expected:
                errors.append(f"ticker does not match expected ticker {expected}")

        period = evidence.period
        period_match = _ANNUAL_PERIOD.fullmatch(period) if isinstance(period, str) else None
        if period_match:
            previous_year = int(period_match.group("previous"))
            current_year = int(period_match.group("current"))
            if current_year != previous_year + 1:
                errors.append("annual comparison periods must be consecutive")
        elif period:
            errors.append("period must use 'YYYY to YYYY' annual format")

        for name in _NUMERIC_FIELDS:
            value = getattr(evidence, name)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
                errors.append(f"{name} must be a finite number")
        if evidence.peer_count is not None:
            if (
                isinstance(evidence.peer_count, bool)
                or not isinstance(evidence.peer_count, Real)
                or not math.isfinite(evidence.peer_count)
                or int(evidence.peer_count) != evidence.peer_count
                or evidence.peer_count < 0
            ):
                errors.append("peer_count must be a non-negative integer")

        if evidence.source and not evidence.source_endpoint:
            errors.append("source_endpoint is required when source is available")
        if evidence.data_mode and (
            not isinstance(evidence.data_mode, str)
            or evidence.data_mode not in _ALLOWED_DATA_MODES
        ):
            errors.append("data_mode must be live, cached, fixture, synthetic, or unknown")
        if evidence.retrieved_at and isinstance(evidence.retrieved_at, str):
            try:
                retrieved_at = datetime.fromisoformat(evidence.retrieved_at.replace("Z", "+00:00"))
                if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
                    errors.append("retrieved_at must include a timezone")
            except ValueError:
                errors.append("retrieved_at must be an ISO-8601 timestamp")
        elif evidence.retrieved_at:
            errors.append("retrieved_at must be an ISO-8601 timestamp")
        return errors

    def validate_conclusion(
        self,
        conclusion: str,
        evidence: Iterable[Evidence],
        expected_ticker: str | None = None,
    ) -> list[str]:
        if not isinstance(conclusion, str) or not conclusion.strip():
            return ["conclusion is required"]
        supporting = [
            item
            for item in evidence
            if not self.validate(item, expected_ticker=expected_ticker)
        ]
        if not supporting:
            return ["conclusion has no supporting evidence"]
        return []


class EvidenceLedger:
    """In-memory evidence store with validated insertion and compact export."""

    def __init__(self, evidence: Iterable[Evidence] = ()) -> None:
        self._items: list[Evidence] = []
        self._ids: set[str] = set()
        self.validator = EvidenceValidator()
        for item in evidence:
            self.add(item)

    def add(self, evidence: Evidence) -> None:
        errors = self.validator.validate(evidence)
        if errors:
            raise ValueError("Invalid evidence: " + "; ".join(errors))
        if evidence.evidence_id in self._ids:
            raise ValueError(f"Duplicate evidence_id: {evidence.evidence_id}")
        self._items.append(evidence)
        self._ids.add(evidence.evidence_id)

    def by_ticker(self, ticker: str) -> list[Evidence]:
        normalized = ticker.strip().upper()
        return [item for item in self._items if item.ticker == normalized]

    def by_metric(self, metric: str) -> list[Evidence]:
        normalized = metric.strip().casefold()
        return [item for item in self._items if item.metric.casefold() == normalized]

    def validate_required_fields(self) -> dict[str, list[str]]:
        return {
            item.evidence_id: errors
            for item in self._items
            if (errors := self.validator.validate_required_fields(item))
        }

    def validate(self) -> dict[str, list[str]]:
        return {
            item.evidence_id: errors
            for item in self._items
            if (errors := self.validator.validate(item))
        }

    def to_llm_context(self, ticker: str | None = None) -> dict[str, Any]:
        """Return evidence only, without asking a model to derive financial values."""
        items = self._items if ticker is None else self.by_ticker(ticker)
        return {
            "schema_version": 1,
            "evidence": [item.to_dict() for item in items],
        }

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self):
        return iter(self._items)


def evidence_from_anomalies(
    frame: pd.DataFrame,
    ranked: pd.DataFrame,
    *,
    retrieved_at: str | datetime | None = None,
    data_mode: str = "unknown",
    source: str = "Sectors Financial API",
    source_endpoint: str = "/v2/companies/",
) -> EvidenceLedger:
    """Copy ranked components and source values into validated evidence records."""
    timestamp = retrieved_at or datetime.now(timezone.utc)
    timestamp_text = timestamp.isoformat() if isinstance(timestamp, datetime) else timestamp
    ledger = EvidenceLedger()
    if ranked.empty:
        return ledger
    if "ticker" not in frame.columns:
        raise ValueError("Source frame must contain ticker values")

    for _, result in ranked.iterrows():
        ticker = str(result["ticker"]).strip().upper()
        matches = frame[frame["ticker"].astype(str).str.strip().str.upper() == ticker]
        if len(matches) != 1:
            raise ValueError(f"Expected one source row for anomaly ticker {ticker}")
        source_row = matches.iloc[0]
        for component in result.get("components", []):
            metric = str(component["metric"])
            previous_year, current_year = component["period"].split(" to ", maxsplit=1)
            previous_value = source_row[f"{metric}[{previous_year}]"]
            current_value = source_row[f"{metric}[{current_year}]"]
            previous_value = _native_number(previous_value)
            current_value = _native_number(current_value)
            if previous_value is None or current_value is None:
                continue
            ledger.add(
                Evidence(
                    ticker=ticker,
                    company_name=(
                        None if pd.isna(source_row.get("company_name"))
                        else str(source_row.get("company_name"))
                    ),
                    metric=metric,
                    current_value=current_value,
                    previous_value=previous_value,
                    change=_native_number(component["change_pct"]),
                    peer_median=_native_number(component["peer_median_change_pct"]),
                    peer_count=int(component["peer_count"]),
                    deviation=_native_number(component["deviation_pct_points"]),
                    period=component["period"],
                    source=source,
                    source_endpoint=source_endpoint,
                    retrieved_at=timestamp_text,
                    calculation=(
                        f"change_pct=((current/previous)-1)*100 using {metric}[{current_year}] "
                        f"and {metric}[{previous_year}]; peer_median=median(other comparable "
                        "companies' change_pct; deviation=abs(change_pct-peer_median); "
                        "contribution=percentile_rank(abs(change_pct-universe_median))*100"
                    ),
                    data_mode=data_mode,
                )
            )
    return ledger


def _native_number(value: Any) -> int | float | None:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    return value
