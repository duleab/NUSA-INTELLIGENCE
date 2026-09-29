"""Small Sectors API v2 client for NUSA bank discovery and company data."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


Transport = Callable[[str, dict[str, str], float], tuple[int, Any]]


class SectorsAPIError(RuntimeError):
    """An API failure without credential or response-body disclosure."""

    def __init__(self, status: int, path: str):
        self.status = status
        self.path = path
        super().__init__(f"Sectors API returned HTTP {status} for {path}")


def _urllib_transport(url: str, headers: dict[str, str], timeout: float) -> tuple[int, Any]:
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise SectorsAPIError(error.code, Request(url).full_url.split("?", 1)[0]) from None
    except URLError as error:
        raise RuntimeError(f"Sectors API connection failed: {error.reason}") from None


class SectorsClient:
    """API v2 wrapper with success-only disk caching and bounded transient retries."""

    base_url = "https://api.sectors.app"
    bank_filter = "sub_sector = 'Banks' and market_cap IS NOT NULL"
    discovery_years = (2025, 2024)
    discovery_metrics = (
        "revenue",
        "earnings",
        "eps",
        "net_interest_income",
        "interest_income",
        "interest_expense",
        "non_interest_income",
        "total_assets",
        "total_liabilities",
        "total_equity",
        "total_deposit",
        "gross_loan",
        "net_loan",
        "allowance_for_loans",
        "total_capital",
        "total_risk_weighted_asset",
        "operating_cash_flow",
        "free_cash_flow",
        "pe",
        "pb",
        "roa",
        "roe",
        "net_interest_margin",
        "capital_adequacy_ratio",
        "casa_ratio",
        "leverage_ratio",
        "loan_to_deposit_ratio",
        "liquidity_coverage_ratio",
        "efficiency_ratio",
    )

    def __init__(
        self,
        cache_dir: str | Path = "data/cache",
        timeout: float = 15.0,
        retries: int = 2,
        transport: Transport | None = None,
        now: Callable[[], float] = time.time,
    ) -> None:
        if timeout <= 0 or retries < 0:
            raise ValueError("timeout must be positive and retries cannot be negative")
        self.cache_dir = Path(cache_dir)
        self.timeout = timeout
        self.retries = retries
        self.transport = transport or _urllib_transport
        self.now = now

    def subsectors(self, force_refresh: bool = False) -> Any:
        """Return the documented and live-validated subsector taxonomy."""
        return self._get(
            "/v2/subsectors/",
            {},
            ttl_seconds=30 * 24 * 60 * 60,
            force_refresh=force_refresh,
        )

    def companies_screener(
        self,
        limit: int = 50,
        offset: int | None = None,
        force_refresh: bool = False,
    ) -> Any:
        """Fetch Banks and documented historical metrics in one structured query."""
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        if offset is not None and offset < 0:
            raise ValueError("offset cannot be negative")

        requested_fields = [
            f"{metric}[{year}]"
            for metric in self.discovery_metrics
            for year in self.discovery_years
        ]
        metric_availability = " or ".join(
            f"{field} IS NOT NULL" for field in requested_fields
        )
        params = {
            "where": f"{self.bank_filter} and ({metric_availability})",
            "order_by": "-market_cap",
            "limit": limit,
            "include_query_values": "true",
        }
        if offset is not None:
            params["offset"] = offset
        return self._get(
            "/v2/companies/",
            params,
            ttl_seconds=24 * 60 * 60,
            force_refresh=force_refresh,
        )

    def company_report(self, ticker: str, force_refresh: bool = False) -> Any:
        """Fetch selected company-report sections through the authenticated client."""
        normalized = ticker.strip().upper()
        if not re.fullmatch(r"[A-Z0-9.-]{1,20}", normalized):
            raise ValueError("ticker contains unsupported characters")
        symbol = quote(normalized, safe=".-")
        return self._get(
            f"/v2/company/report/{symbol}/",
            {"sections": "overview,financials,peers,valuation"},
            ttl_seconds=24 * 60 * 60,
            force_refresh=force_refresh,
        )

    def _get(self, path: str, params: dict[str, Any], ttl_seconds: int, force_refresh: bool) -> Any:
        cache_path = self._cache_path(path, params)
        if not force_refresh:
            cached = self._read_cache(cache_path, ttl_seconds)
            if cached is not None:
                return cached

        api_key = os.environ.get("SECTORS_API_KEY")
        if not api_key:
            raise RuntimeError("Set SECTORS_API_KEY in the environment before calling Sectors API")

        query = urlencode(params)
        url = f"{self.base_url}{path}?{query}" if query else f"{self.base_url}{path}"
        headers = {"Authorization": api_key, "Accept": "application/json"}
        attempt = 0
        while True:
            try:
                status, payload = self.transport(url, headers, self.timeout)
                if 200 <= status < 300:
                    self._write_cache(cache_path, payload)
                    return payload
                error = SectorsAPIError(status, path)
            except SectorsAPIError as caught:
                error = caught
            if error.status not in (429, 500, 502, 503, 504) or attempt >= self.retries:
                raise error
            time.sleep(min(0.5 * (2**attempt), 2.0))
            attempt += 1

    def _cache_path(self, path: str, params: dict[str, Any]) -> Path:
        fingerprint = json.dumps(["v2", path, sorted(params.items())], separators=(",", ":"))
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _read_cache(self, path: Path, ttl_seconds: int) -> Any | None:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            if self.now() - record["cached_at"] > ttl_seconds:
                return None
            return record["response"]
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _write_cache(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"cached_at": self.now(), "response": payload}, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)
