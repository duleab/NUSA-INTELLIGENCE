"""Normalize documented Companies Screener results into a bank DataFrame."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class BankUniverse:
    frame: pd.DataFrame
    pagination: dict[str, Any]


def normalize_bank_universe(payload: Any) -> BankUniverse:
    """Flatten Screener query values while preserving missing metrics as nulls."""
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        raise ValueError("Sectors Screener response must contain a results list")

    rows: list[dict[str, Any]] = []
    for result in payload["results"]:
        if not isinstance(result, dict) or not isinstance(result.get("symbol"), str):
            raise ValueError("Each Screener result must contain a string symbol")
        ticker = result["symbol"].strip().upper()
        if not ticker:
            raise ValueError("Screener symbol cannot be empty")
        row: dict[str, Any] = {
            "ticker": ticker,
            "company_name": result.get("company_name"),
        }
        query_values = result.get("query_values")
        if query_values is not None:
            if not isinstance(query_values, dict):
                raise ValueError(f"query_values for {ticker} must be an object when present")
            row.update({key: value for key, value in query_values.items() if key not in row})
        # Preserve explicitly returned top-level values without guessing schema aliases.
        for key, value in result.items():
            if key not in {"symbol", "company_name", "query_values"} and key not in row:
                row[key] = value
        rows.append(row)

    frame = pd.DataFrame(rows)
    if "ticker" not in frame.columns:
        frame = pd.DataFrame(columns=["ticker", "company_name"])
    return BankUniverse(frame=frame, pagination=payload.get("pagination", {}))
