"""Small structured, in-memory research state for Streamlit-style sessions."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar, MutableMapping


_TICKER_RE = re.compile(r"(?<![A-Z0-9])([A-Z0-9]{3,8}(?:\.JK)?)(?![A-Z0-9])", re.I)
_FOLLOWUP_RE = re.compile(r"\bthis\s+change\b", re.I)
_TICKER_STOPWORDS = {
    "AND", "OR", "THE", "WITH", "PEER", "PEERS", "BANK", "BANKS", "IDX",
    "VERSUS", "COMPARE", "COMPARISON", "CHANGE", "CHANGES", "THIS", "THAT",
}


@dataclass
class ResearchSessionMemory:
    """Only the compact context needed to ground immediate research follow-ups."""

    active_ticker: str | None = None
    active_sector: str | None = None
    last_investigation_objective: str | None = None
    last_anomaly_metric: str | None = None
    selected_peers: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    previous_plan: dict[str, Any] | None = None

    SESSION_KEY: ClassVar[str] = "nusa_research_memory"

    def to_dict(self) -> dict[str, Any]:
        """Return only the approved state fields for persistence in a UI session."""
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ResearchSessionMemory:
        """Load the supported fields and ignore unrelated session data."""
        return cls(
            active_ticker=_optional_string(value.get("active_ticker")),
            active_sector=_optional_string(value.get("active_sector")),
            last_investigation_objective=_optional_string(
                value.get("last_investigation_objective")
            ),
            last_anomaly_metric=_optional_string(value.get("last_anomaly_metric")),
            selected_peers=_string_list(value.get("selected_peers")),
            evidence_ids=_string_list(value.get("evidence_ids")),
            previous_plan=(
                dict(value["previous_plan"])
                if isinstance(value.get("previous_plan"), dict)
                else None
            ),
        )

    @classmethod
    def from_session_state(
        cls,
        session_state: MutableMapping[str, Any],
        key: str = SESSION_KEY,
    ) -> ResearchSessionMemory:
        """Get or initialize one in-memory object under a Streamlit session key."""
        existing = session_state.get(key)
        if isinstance(existing, cls):
            return existing
        memory = cls.from_dict(existing) if isinstance(existing, dict) else cls()
        session_state[key] = memory
        return memory

    def resolve_request(self, request: str) -> str:
        """Expand a supported “this change” comparison using prior ticker state."""
        if not self.is_change_followup(request):
            return request
        with_match = re.search(r"\bwith\b(?P<peers>.+)$", request, re.I)
        if not with_match:
            return request
        peers: list[str] = []
        seen = {_ticker_key(self.active_ticker or "")}
        for match in _TICKER_RE.finditer(with_match.group("peers").upper()):
            ticker = match.group(1).upper()
            if ticker in _TICKER_STOPWORDS:
                continue
            if len(ticker) == 4 and ticker.isalpha():
                ticker += ".JK"
            key = _ticker_key(ticker)
            if key not in seen:
                peers.append(ticker)
                seen.add(key)
        if not peers:
            return request
        return f"Compare {self.active_ticker} with {' and '.join(peers)}"

    def is_change_followup(self, request: str) -> bool:
        """Whether the request can be grounded in a prior metric investigation."""
        return bool(
            self.active_ticker
            and self.last_anomaly_metric
            and self.evidence_ids
            and _FOLLOWUP_RE.search(request)
        )

    def record_run(self, request: str, result: Any) -> None:
        """Replace session context with the completed run's structured state."""
        plan = result.plan
        tickers = list(plan.tickers)
        if not tickers:
            anomalies = result.outputs.get("discover_bank_anomalies")
            if anomalies:
                tickers = [
                    str(row["ticker"]).upper()
                    for row in anomalies.value.get("anomalies", [])
                    if isinstance(row, dict) and row.get("ticker")
                ][:1]

        if plan.intent == "INVESTIGATE":
            self.last_investigation_objective = request
        if tickers:
            self.active_ticker = tickers[0]
            self.active_sector = "Banks"
        active_key = _ticker_key(self.active_ticker or "")
        self.selected_peers = [
            ticker for ticker in tickers if _ticker_key(ticker) != active_key
        ]
        items = list(result.evidence_ledger)
        active_evidence = [item for item in items if _ticker_key(item.ticker) == active_key]
        metric_evidence = active_evidence or items
        if metric_evidence:
            self.last_anomaly_metric = metric_evidence[0].metric
        self.evidence_ids = [item.evidence_id for item in items]
        self.previous_plan = plan.to_dict()


def _ticker_key(ticker: str) -> str:
    return ticker.strip().upper().removesuffix(".JK")


def _optional_string(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]
