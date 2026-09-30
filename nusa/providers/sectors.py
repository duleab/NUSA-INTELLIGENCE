"""Live Sectors and explicit non-live fixture implementations."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nusa.discovery.banks import normalize_bank_universe
from nusa.providers.base import (
    BankDataProvider,
    BankUniverseResult,
    CompanyData,
    DataSourceStatus,
    DiscoveryData,
)
from nusa.sectors.client import SectorsClient


_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(?:sk|pk|rk|ghp|github_pat|xox[baprs])[-_][A-Za-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(r"(?i)\bSECTORS_API_KEY\s*=\s*\S+"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)
_SECRET_FIELD_NAMES = {
    "authorization",
    "apikey",
    "apitoken",
    "accesstoken",
    "clientsecret",
    "credentials",
    "password",
    "secret",
    "secrets",
    "secretkey",
    "sectorsapikey",
    "token",
    "privatekey",
}
_TICKER_PATTERN = re.compile(r"^[A-Z0-9.-]{1,20}$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SectorsBankDataProvider:
    """Live source provider; API or normalization failures are never hidden."""

    def __init__(self, client: Any | None = None) -> None:
        self.client = client or SectorsClient()
        self._status = DataSourceStatus(
            mode="live",
            source="Sectors Financial API",
            is_live=True,
            warning="The Sectors client may serve its local response cache.",
        )

    @property
    def status(self) -> DataSourceStatus:
        return self._status

    def get_bank_universe(self, force_refresh: bool = False) -> BankUniverseResult:
        try:
            payload = self.client.companies_screener(limit=50, force_refresh=force_refresh)
            universe = normalize_bank_universe(payload)
        except Exception as error:
            self._record_failure(error)
            raise
        self._status = DataSourceStatus(
            mode="live",
            source="Sectors Financial API",
            is_live=True,
            retrieved_at=_now(),
            warning="Sectors source; the existing client may have returned cached data.",
        )
        return BankUniverseResult(universe=universe, status=self._status)

    def get_discovery_data(self, force_refresh: bool = False) -> DiscoveryData:
        from nusa.discovery.workflow import build_discovery_data

        universe_result = self.get_bank_universe(force_refresh=force_refresh)
        return build_discovery_data(
            universe_result.universe,
            universe_result.status,
            data_mode="live",
        )

    def get_company_data(self, ticker: str) -> CompanyData:
        normalized = _normalize_ticker(ticker)
        try:
            payload = self.client.company_report(normalized, force_refresh=False)
        except Exception as error:
            self._record_failure(error)
            raise
        self._status = DataSourceStatus(
            mode="live",
            source="Sectors Financial API",
            is_live=True,
            retrieved_at=_now(),
            warning="Sectors source; the existing client may have returned cached data.",
        )
        return CompanyData(ticker=normalized, data=payload, status=self._status)

    def _record_failure(self, error: Exception) -> None:
        self._status = DataSourceStatus(
            mode="live",
            source="Sectors Financial API",
            is_live=True,
            retrieved_at=None,
            warning=(
                f"Live request failed ({type(error).__name__}); "
                "the error was propagated and no demo fallback was used."
            ),
        )


class FixtureBankDataProvider:
    """Load a sanitized sample or user-supplied Screener snapshot as non-live data."""

    def __init__(
        self,
        payload: dict[str, Any],
        *,
        source_label: str,
        data_mode: str = "fixture",
    ) -> None:
        if not isinstance(source_label, str) or not source_label.strip():
            raise ValueError("Fixture source_label must be explicit and non-empty")
        if data_mode not in {"fixture", "synthetic"}:
            raise ValueError("Fixture data_mode must be fixture or synthetic")
        _ensure_secret_free(payload)
        normalize_bank_universe(payload)
        self._payload = deepcopy(payload)
        self._data_mode = data_mode
        mode = "demo" if data_mode == "synthetic" else "fixture"
        warning = (
            "DEMO/SAMPLE DATA — Synthetic demonstration values. Not current market data."
            if data_mode == "synthetic"
            else "Fixture snapshot; not live or necessarily current Sectors data."
        )
        self._status = DataSourceStatus(
            mode=mode,
            source=source_label.strip(),
            is_live=False,
            warning=warning,
        )

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        source_label: str | None = None,
    ) -> FixtureBankDataProvider:
        if not source_label or not source_label.strip():
            raise ValueError("An explicit source_label is required for external fixtures")
        fixture_path = Path(path)
        raw = fixture_path.read_text(encoding="utf-8")
        _ensure_secret_free_text(raw)
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Fixture root must be a JSON object")
        return cls(payload, source_label=source_label, data_mode="fixture")

    @property
    def status(self) -> DataSourceStatus:
        return self._status

    def get_bank_universe(self, force_refresh: bool = False) -> BankUniverseResult:
        del force_refresh  # Fixture data is local and has no refresh operation.
        universe = normalize_bank_universe(deepcopy(self._payload))
        self._status = DataSourceStatus(
            mode=self._status.mode,
            source=self._status.source,
            is_live=False,
            retrieved_at=_now(),
            warning=self._status.warning,
        )
        return BankUniverseResult(universe=universe, status=self._status)

    def get_discovery_data(self, force_refresh: bool = False) -> DiscoveryData:
        from nusa.discovery.workflow import build_discovery_data

        universe_result = self.get_bank_universe(force_refresh=force_refresh)
        return build_discovery_data(
            universe_result.universe,
            universe_result.status,
            data_mode=self._data_mode,
        )

    def get_company_data(self, ticker: str) -> CompanyData:
        universe = self.get_bank_universe()
        normalized = _normalize_ticker(ticker)
        rows = universe.universe.frame
        matching = rows[rows["ticker"] == normalized]
        if matching.empty:
            raise KeyError(f"Ticker {normalized} is not present in this fixture")
        self._status = universe.status
        return CompanyData(
            ticker=normalized,
            data=matching.iloc[0].dropna().to_dict(),
            status=self._status,
        )


def create_bank_data_provider(
    mode: str,
    *,
    client: Any | None = None,
    fixture_path: str | Path | None = None,
    source_label: str | None = None,
) -> BankDataProvider:
    """Select a provider explicitly; errors never trigger implicit source switching."""
    if mode == "live":
        if fixture_path is not None or source_label is not None:
            raise ValueError("Fixture options cannot be combined with live mode")
        return SectorsBankDataProvider(client=client)
    if mode in {"demo", "fixture"}:
        if fixture_path is not None:
            if not source_label:
                raise ValueError("An explicit source_label is required for external fixtures")
            return FixtureBankDataProvider.from_file(fixture_path, source_label=source_label)
        if source_label is not None:
            raise ValueError("source_label requires an external fixture_path")
        if mode == "fixture":
            raise ValueError("Fixture mode requires fixture_path and source_label")
        demo_path = Path(__file__).resolve().parents[2] / "data" / "fixtures" / "banks_demo.json"
        raw_demo = demo_path.read_text(encoding="utf-8")
        _ensure_secret_free_text(raw_demo)
        return FixtureBankDataProvider(
            json.loads(raw_demo),
            source_label="DEMO/SAMPLE — bundled synthetic development fixture",
            data_mode="synthetic",
        )
    raise ValueError("mode must be explicitly set to live, demo, or fixture")


def _ensure_secret_free(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    _ensure_secret_free_text(serialized)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, nested in value.items():
                normalized_key = re.sub(r"[^a-z0-9]", "", str(key).lower())
                if normalized_key in _SECRET_FIELD_NAMES:
                    raise ValueError("Fixture contains credential-like content")
                visit(nested)
        elif isinstance(value, list):
            for nested in value:
                visit(nested)

    visit(payload)


def _ensure_secret_free_text(raw: str) -> None:
    if any(pattern.search(raw) for pattern in _SECRET_PATTERNS):
        raise ValueError("Fixture contains credential-like content")


def _normalize_ticker(ticker: str) -> str:
    if not isinstance(ticker, str):
        raise ValueError("ticker must be a string")
    normalized = ticker.strip().upper()
    if not _TICKER_PATTERN.fullmatch(normalized):
        raise ValueError("ticker contains unsupported characters")
    return normalized
