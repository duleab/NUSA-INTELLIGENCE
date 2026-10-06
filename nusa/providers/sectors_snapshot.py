"""Validated import and offline provider for Sectors Companies Screener snapshots."""

from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nusa.discovery.banks import BankUniverse, normalize_bank_universe
from nusa.discovery.workflow import build_discovery_data
from nusa.providers.base import BankUniverseResult, CompanyData, DataSourceStatus, DiscoveryData


SECTORS_COMPANIES_ENDPOINT = "/v2/companies/"
DEFAULT_SECTORS_SNAPSHOT_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "cache"
    / "sectors"
    / "banks_companies_screener.json"
)
ANNUAL_YEARS = frozenset({"2024", "2025"})
DOCUMENTED_ANNUAL_METRICS = frozenset(
    {
        "earnings",
        "net_interest_income",
        "total_assets",
        "total_equity",
        "roa",
        "roe",
        "net_interest_margin",
        "gross_loan",
        "net_loan",
        "total_deposit",
        "efficiency_ratio",
        "cost_to_income_ratio",
        "capital_adequacy_ratio",
        "casa_ratio",
        "leverage_ratio",
        "loan_to_deposit_ratio",
        "liquidity_coverage_ratio",
    }
)
_ANNUAL_FIELD = re.compile(r"^(?P<metric>[A-Za-z_][A-Za-z0-9_]*)\[(?P<year>\d{4})\]$")
_SENSITIVE_KEY = re.compile(
    r"(?i)(authorization|cookie|api.?key|access.?token|client.?secret|password|account.?id|user.?id|email|private.?key)"
)
_SECRET_TEXT = re.compile(
    r"(?i)(\bsk-[A-Za-z0-9_-]{16,}\b|\bgh[pousr]_[A-Za-z0-9_]{20,}\b|"
    r"\bgithub_pat_[A-Za-z0-9_]{20,}\b|\bBearer\s+\S+|"
    r"\bSECTORS_API_KEY\s*=\s*\S+)"
)
_SYNTHETIC_TICKER = re.compile(r"(?i)^(?:DEMO|SAMPLE|FIXTURE)(?:BANK)?[A-Z0-9.-]*$")
_SYNTHETIC_LABEL = re.compile(
    r"(?i)(?:\bDEMO/SAMPLE(?: DATA)?\b|\bsynthetic(?: demonstration)? values?\b|"
    r"\bfictional (?:demo|bank|company)\b)"
)
_ALLOWED_QUERY_FIELDS = frozenset(
    {"where", "order_by", "limit", "offset", "include_query_values"}
)


def import_sectors_response(
    response: dict[str, Any],
    *,
    query: dict[str, Any],
    retrieved_at: str,
    confirmed_sectors_origin: bool = False,
    snapshot_created_at: str | None = None,
) -> dict[str, Any]:
    """Wrap a manually saved successful Screener response as a cached snapshot.

    The caller must explicitly attest that the source was Sectors. The importer
    validates shape and blocks recognizable demo tickers but cannot cryptographically
    prove where an arbitrary JSON file originated.
    """
    if confirmed_sectors_origin is not True:
        raise ValueError("Explicit confirmation of Sectors origin is required")
    if not isinstance(query, dict):
        raise ValueError("Snapshot query must be an object")
    _validate_query(query)
    _validate_timestamp(retrieved_at, "retrieved_at")
    created_at = snapshot_created_at or _now()
    _validate_timestamp(created_at, "snapshot_created_at")
    _validate_response(response)

    snapshot = {
        "source": "Sectors",
        "endpoint": SECTORS_COMPANIES_ENDPOINT,
        "retrieved_at": retrieved_at,
        "snapshot_created_at": created_at,
        "query": deepcopy(query),
        "is_live_snapshot": True,
        "is_cached": True,
        "response": deepcopy(response),
    }
    _validate_snapshot(snapshot)
    return snapshot


def import_sectors_response_file(
    response_path: str | Path,
    *,
    query: dict[str, Any],
    retrieved_at: str,
    confirmed_sectors_origin: bool = False,
    destination: str | Path = DEFAULT_SECTORS_SNAPSHOT_PATH,
) -> Path:
    """Import a saved raw Sectors Screener JSON response into the ignored cache."""
    source_path = Path(response_path)
    try:
        response = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Could not read a valid JSON Screener response") from error
    if not isinstance(response, dict):
        raise ValueError("Screener response root must be an object")
    snapshot = import_sectors_response(
        response,
        query=query,
        retrieved_at=retrieved_at,
        confirmed_sectors_origin=confirmed_sectors_origin,
    )
    return save_sectors_snapshot(snapshot, destination)


def save_sectors_snapshot(snapshot: dict[str, Any], path: str | Path) -> Path:
    """Validate and atomically write a provenance envelope to disk."""
    _validate_snapshot(snapshot)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    try:
        temporary.write_text(
            json.dumps(snapshot, ensure_ascii=False, allow_nan=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def load_sectors_snapshot(path: str | Path) -> dict[str, Any]:
    """Load and validate a cached Sectors provenance envelope; never fetch data."""
    try:
        snapshot = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Could not read a valid Sectors snapshot") from error
    _validate_snapshot(snapshot)
    return snapshot


def normalize_sectors_response(response: dict[str, Any]) -> BankUniverse:
    """Flatten only returned, documented annual bank metrics; never impute values."""
    _validate_response(response)
    normalized = normalize_bank_universe(response)
    keep = ["ticker", "company_name"]
    for field in ("sub_sector", "market_cap"):
        if field in normalized.frame.columns:
            keep.append(field)
    for column in normalized.frame.columns:
        match = _ANNUAL_FIELD.fullmatch(str(column))
        if (
            match
            and match.group("metric") in DOCUMENTED_ANNUAL_METRICS
            and match.group("year") in ANNUAL_YEARS
        ):
            keep.append(str(column))
    # Preserve order while preventing duplicate labels.
    keep = list(dict.fromkeys(keep))
    return BankUniverse(
        frame=normalized.frame.loc[:, [name for name in keep if name in normalized.frame]],
        pagination=normalized.pagination,
    )


class CachedSectorsBankDataProvider:
    """Offline BankDataProvider that reports the snapshot's original retrieval time."""

    def __init__(self, snapshot_path: str | Path) -> None:
        self.snapshot = load_sectors_snapshot(snapshot_path)
        self._universe = normalize_sectors_response(self.snapshot["response"])
        self._status = DataSourceStatus(
            mode="cached_sectors",
            source="SECTORS CACHED SNAPSHOT",
            is_live=False,
            retrieved_at=self.snapshot["retrieved_at"],
            warning=(
                "Cached Sectors-origin snapshot; this is not a live API request. "
                f"Original retrieval: {self.snapshot['retrieved_at']}."
            ),
        )

    @property
    def status(self) -> DataSourceStatus:
        return self._status

    def get_bank_universe(self, force_refresh: bool = False) -> BankUniverseResult:
        if force_refresh:
            raise RuntimeError(
                "Cached Sectors snapshots cannot refresh; import a new snapshot explicitly"
            )
        return BankUniverseResult(universe=self._universe, status=self._status)

    def get_discovery_data(self, force_refresh: bool = False) -> DiscoveryData:
        if force_refresh:
            raise RuntimeError(
                "Cached Sectors snapshots cannot refresh; import a new snapshot explicitly"
            )
        return build_discovery_data(
            self._universe,
            self._status,
            data_mode="cached",
        )

    def get_company_data(self, ticker: str) -> CompanyData:
        normalized = ticker.strip().upper()
        matches = self._universe.frame[self._universe.frame["ticker"] == normalized]
        if matches.empty:
            raise KeyError(f"Ticker {normalized} is not present in this Sectors snapshot")
        data = matches.iloc[0].to_dict()
        for key, value in data.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if math.isnan(float(value)):
                    data[key] = None
        return CompanyData(
            ticker=normalized,
            data=data,
            status=self._status,
        )


def _validate_snapshot(snapshot: Any) -> None:
    if not isinstance(snapshot, dict):
        raise ValueError("Sectors snapshot must be an object")
    _reject_sensitive_content(snapshot)
    required = {
        "source",
        "endpoint",
        "retrieved_at",
        "snapshot_created_at",
        "query",
        "is_live_snapshot",
        "is_cached",
        "response",
    }
    missing = required.difference(snapshot)
    if missing:
        raise ValueError("Sectors snapshot is missing required metadata")
    if snapshot["source"] != "Sectors":
        raise ValueError("Snapshot source must be Sectors, not demo/sample data")
    if snapshot["endpoint"] != SECTORS_COMPANIES_ENDPOINT:
        raise ValueError("Snapshot endpoint must be /v2/companies/")
    if snapshot["is_live_snapshot"] is not True or snapshot["is_cached"] is not True:
        raise ValueError("Disk snapshots must be Sectors-origin and explicitly cached")
    _validate_timestamp(snapshot["retrieved_at"], "retrieved_at")
    _validate_timestamp(snapshot["snapshot_created_at"], "snapshot_created_at")
    _validate_query(snapshot["query"])
    _validate_response(snapshot["response"])
    try:
        json.dumps(snapshot, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("Sectors snapshot must contain finite JSON values") from error


def _validate_response(response: Any) -> None:
    if not isinstance(response, dict) or not isinstance(response.get("results"), list):
        raise ValueError("Sectors Companies Screener response must contain a results list")
    pagination = response.get("pagination")
    if not isinstance(pagination, dict):
        raise ValueError("Sectors Screener response must contain pagination metadata")
    total_count = pagination.get("total_count")
    if isinstance(total_count, bool) or not isinstance(total_count, int) or total_count < 0:
        raise ValueError("pagination.total_count must be a non-negative integer")

    for result in response["results"]:
        if not isinstance(result, dict):
            raise ValueError("Each Sectors Screener result must be an object")
        ticker = result.get("symbol")
        company_name = result.get("company_name")
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("Each Sectors Screener result needs a company ticker")
        if _SYNTHETIC_TICKER.fullmatch(ticker.strip()):
            raise ValueError("Synthetic DEMO/SAMPLE tickers cannot be labeled as Sectors data")
        if not isinstance(company_name, str) or not company_name.strip():
            raise ValueError("Each Sectors Screener result needs a company name")
        query_values = result.get("query_values", {})
        if not isinstance(query_values, dict):
            raise ValueError(f"query_values for {ticker} must be an object")
        for key, value in query_values.items():
            match = _ANNUAL_FIELD.fullmatch(str(key))
            if not match or match.group("metric") not in DOCUMENTED_ANNUAL_METRICS:
                continue
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"Annual metric {key} must be numeric or null")
            if not math.isfinite(float(value)):
                raise ValueError(f"Annual metric {key} must be finite or null")
    _reject_sensitive_content(response)
    _reject_synthetic_content(response)


def _validate_query(query: Any) -> None:
    if not isinstance(query, dict):
        raise ValueError("Snapshot query must be an object")
    _reject_sensitive_content(query)
    if set(query).difference(_ALLOWED_QUERY_FIELDS):
        raise ValueError("Snapshot query contains unsupported or credential-bearing fields")
    if not isinstance(query.get("where"), str) or not isinstance(query.get("order_by"), str):
        raise ValueError("Snapshot query requires structured where and order_by expressions")
    limit = query.get("limit")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 200:
        raise ValueError("Snapshot query limit must be between 1 and 200")
    if query.get("offset") is not None and (
        isinstance(query["offset"], bool)
        or not isinstance(query["offset"], int)
        or query["offset"] < 0
    ):
        raise ValueError("Snapshot query offset must be a non-negative integer or null")
    include = query.get("include_query_values")
    if not (include is True or (isinstance(include, str) and include.lower() == "true")):
        raise ValueError("Snapshot query must record include_query_values=true")


def _validate_timestamp(value: Any, field: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware ISO timestamp")


def _reject_sensitive_content(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if _SENSITIVE_KEY.search(str(key)):
                raise ValueError("Snapshot contains credential or account information")
            _reject_sensitive_content(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_sensitive_content(nested)
    elif isinstance(value, str) and _SECRET_TEXT.search(value):
        raise ValueError("Snapshot contains credential-like text")


def _reject_synthetic_content(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if re.sub(r"[^a-z0-9]", "", str(key).lower()) == "datamode":
                if isinstance(nested, str) and nested.strip().lower() in {
                    "demo", "sample", "synthetic", "fixture", "demo_sample"
                }:
                    raise ValueError("Synthetic DEMO/SAMPLE data cannot be imported as Sectors")
            _reject_synthetic_content(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_synthetic_content(nested)
    elif isinstance(value, str) and _SYNTHETIC_LABEL.search(value):
        raise ValueError("Synthetic DEMO/SAMPLE data cannot be imported as Sectors")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
