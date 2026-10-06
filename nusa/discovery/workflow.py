"""Provider-based Discovery entry point and deterministic ranking composition."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TypeAlias

from nusa.discovery.anomaly import rank_anomalies
from nusa.discovery.banks import BankUniverse
from nusa.discovery.evidence import evidence_from_anomalies
from nusa.providers.base import BankDataProvider, DataSourceStatus, DiscoveryData

DiscoveryResult: TypeAlias = DiscoveryData


def discover_banks(
    provider: BankDataProvider,
    force_refresh: bool = False,
) -> DiscoveryResult:
    """Run Discovery through the selected provider, independent of HTTP details."""
    return provider.get_discovery_data(force_refresh=force_refresh)


def build_discovery_data(
    universe: BankUniverse,
    status: DataSourceStatus,
    *,
    data_mode: str,
) -> DiscoveryData:
    """Apply the preserved deterministic anomaly engine to provider data."""
    ranked = rank_anomalies(universe.frame)
    ledger = evidence_from_anomalies(
        universe.frame,
        ranked,
        retrieved_at=status.retrieved_at or datetime.now(timezone.utc).isoformat(),
        data_mode=data_mode,
        source=status.source,
        source_endpoint=(
            "/v2/companies/"
            if status.is_live or status.mode == "cached_sectors"
            else "fixture://local"
        ),
    )
    return DiscoveryData(
        universe=universe,
        ranked=ranked,
        evidence_ledger=ledger,
        status=status,
    )
