"""Provider interface and status-bearing data result models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import pandas as pd

from nusa.discovery.banks import BankUniverse
from nusa.discovery.evidence import EvidenceLedger


@dataclass(frozen=True)
class DataSourceStatus:
    mode: str
    source: str
    is_live: bool
    retrieved_at: str | None = None
    warning: str | None = None


@dataclass(frozen=True)
class BankUniverseResult:
    universe: BankUniverse
    status: DataSourceStatus


@dataclass(frozen=True)
class DiscoveryData:
    universe: BankUniverse
    ranked: pd.DataFrame
    evidence_ledger: EvidenceLedger
    status: DataSourceStatus


@dataclass(frozen=True)
class CompanyData:
    ticker: str
    data: dict[str, Any]
    status: DataSourceStatus


class BankDataProvider(Protocol):
    """Application-facing interface independent of transport and source mode."""

    @property
    def status(self) -> DataSourceStatus:
        """Most recent source status, including any warning."""

    def get_bank_universe(self, force_refresh: bool = False) -> BankUniverseResult:
        """Fetch the bounded bank universe and its source status."""

    def get_discovery_data(self, force_refresh: bool = False) -> DiscoveryData:
        """Fetch, normalize, score, and evidence the bank universe."""

    def get_company_data(self, ticker: str) -> CompanyData:
        """Fetch one company's data without changing source mode."""
