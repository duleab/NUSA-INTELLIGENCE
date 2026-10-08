"""Tests for the autonomous deep-investigation policy (nusa.agent.policy)."""

from __future__ import annotations

import unittest

from nusa.agent.policy import (
    AgentDecision,
    DEEP_INVESTIGATION_MAX_STEPS,
    PRIORITY_METRICS,
    build_deep_investigation_steps,
    select_size_matched_peers,
    _fmt_deviation,
    _highest_deviation_metric,
    _corroborating_metrics,
)
from nusa.discovery.evidence import Evidence, EvidenceLedger


# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_evidence(
    ticker: str = "SUPA.JK",
    metric: str = "net_interest_income",
    scoring_eligible: bool = True,
    deviation: float = 50.0,
    peer_count: int = 5,
) -> Evidence:
    """Return a minimal evidence item for testing."""
    return Evidence(
        ticker=ticker,
        metric=metric,
        period="2024 to 2025",
        source="test",
        source_endpoint="/v2/companies/",
        retrieved_at="2025-01-01T00:00:00+00:00",
        calculation="(current - previous) / abs(previous) * 100",
        data_mode="fixture",
        company_name="Test Bank",
        previous_value=100_000_000_000.0,
        current_value=260_000_000_000.0,
        change=160.0,
        peer_median=1.5,
        peer_count=peer_count,
        deviation=deviation,
        change_unit="percent",
        scoring_eligible=scoring_eligible,
        exclusion_reason=None,
        absolute_change=160_000_000_000.0,
        scoring_contribution=deviation,
    )


def _make_discovery_rows() -> list[dict]:
    """Return a minimal discovery row list for peer selection tests."""
    return [
        {
            "ticker": "SUPA.JK",
            "company_name": "Bank Supra",
            "score": 82,
            "components": [
                {"metric": "total_assets", "current_value": 5_000_000_000_000.0},
            ],
        },
        {
            "ticker": "BBRI.JK",
            "company_name": "Bank Rakyat",
            "score": 20,
            "components": [
                {"metric": "total_assets", "current_value": 1_800_000_000_000_000.0},
            ],
        },
        {
            "ticker": "BBCA.JK",
            "company_name": "Bank Central Asia",
            "score": 15,
            "components": [
                {"metric": "total_assets", "current_value": 1_400_000_000_000_000.0},
            ],
        },
        {
            "ticker": "BBSI.JK",
            "company_name": "Bank Bisnis",
            "score": 10,
            "components": [
                {"metric": "total_assets", "current_value": 4_500_000_000_000.0},
            ],
        },
        {
            "ticker": "BBHI.JK",
            "company_name": "Bank Harda",
            "score": 8,
            "components": [
                {"metric": "total_assets", "current_value": 6_000_000_000_000.0},
            ],
        },
    ]


# ── select_size_matched_peers ─────────────────────────────────────────────────

class TestSelectSizeMatchedPeers(unittest.TestCase):

    def test_returns_closest_by_assets(self):
        rows = _make_discovery_rows()
        peers = select_size_matched_peers("SUPA.JK", rows, max_peers=3)
        # SUPA has 5T assets; BBSI (4.5T) and BBHI (6T) are closest
        self.assertNotIn("SUPA.JK", peers)
        self.assertIn("BBSI.JK", peers)
        self.assertIn("BBHI.JK", peers)
        # Large banks (BBRI, BBCA ~1.4-1.8Q) should not be the top matches
        self.assertLessEqual(len(peers), 3)

    def test_excludes_target(self):
        rows = _make_discovery_rows()
        peers = select_size_matched_peers("SUPA.JK", rows, max_peers=10)
        self.assertNotIn("SUPA.JK", peers)

    def test_handles_missing_target(self):
        rows = _make_discovery_rows()
        peers = select_size_matched_peers("UNKNOWN.JK", rows, max_peers=3)
        self.assertIsInstance(peers, list)
        self.assertLessEqual(len(peers), 3)

    def test_handles_empty_discovery(self):
        peers = select_size_matched_peers("SUPA.JK", [], max_peers=4)
        self.assertEqual(peers, [])

    def test_jk_suffix_normalised(self):
        rows = _make_discovery_rows()
        # "SUPA" without suffix should still exclude SUPA.JK
        peers = select_size_matched_peers("SUPA", rows, max_peers=4)
        self.assertNotIn("SUPA.JK", peers)

    def test_respects_max_peers(self):
        rows = _make_discovery_rows()
        peers = select_size_matched_peers("SUPA.JK", rows, max_peers=2)
        self.assertLessEqual(len(peers), 2)


# ── build_deep_investigation_steps ───────────────────────────────────────────

class TestBuildDeepInvestigationSteps(unittest.TestCase):

    def _ledger_with_evidence(self, *items: Evidence) -> EvidenceLedger:
        ledger = EvidenceLedger()
        for item in items:
            ledger.add(item)
        return ledger

    def test_requests_company_evidence_when_not_run(self):
        ledger = EvidenceLedger()
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools=set(),
        )
        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].decision, "RUN_TOOL")
        self.assertEqual(steps[0].tool, "get_company_evidence")
        self.assertEqual(steps[0].tool_arguments["ticker"], "SUPA.JK")

    def test_stops_when_no_scoreable_evidence(self):
        ev = _make_evidence(scoring_eligible=False)
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        stop_steps = [s for s in steps if s.decision == "STOP"]
        self.assertTrue(
            len(stop_steps) > 0,
            "Expected a STOP decision when no scoreable evidence"
        )

    def test_selects_compare_peer_metrics_for_primary_driver(self):
        ev = _make_evidence(
            ticker="SUPA.JK",
            metric="net_interest_income",
            scoring_eligible=True,
            deviation=50.0,
        )
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        run_steps = [s for s in steps if s.decision == "RUN_TOOL"]
        self.assertTrue(len(run_steps) > 0, "Expected at least one RUN_TOOL")
        primary_step = run_steps[0]
        self.assertEqual(primary_step.tool, "compare_peer_metrics")
        self.assertIn("net_interest_income", primary_step.tool_arguments.get("metric", ""))

    def test_includes_target_in_comparison_tickers(self):
        ev = _make_evidence(ticker="SUPA.JK", scoring_eligible=True, deviation=50.0)
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        for step in steps:
            if step.tool == "compare_peer_metrics":
                tickers = step.tool_arguments.get("tickers", [])
                self.assertIn("SUPA.JK", tickers)
                break

    def test_all_decisions_are_agent_decision_instances(self):
        ev = _make_evidence(scoring_eligible=True)
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        for step in steps:
            self.assertIsInstance(step, AgentDecision)

    def test_step_numbers_are_sequential(self):
        ev = _make_evidence(scoring_eligible=True)
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        step_nums = [s.step for s in steps]
        self.assertEqual(step_nums, sorted(step_nums))

    def test_does_not_exceed_max_steps(self):
        ev = _make_evidence(scoring_eligible=True)
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        self.assertLessEqual(len(steps), DEEP_INVESTIGATION_MAX_STEPS)

    def test_all_run_tool_steps_have_tool_set(self):
        ev = _make_evidence(scoring_eligible=True)
        ledger = self._ledger_with_evidence(ev)
        steps = build_deep_investigation_steps(
            "SUPA.JK",
            _make_discovery_rows(),
            ledger,
            already_ran_tools={"get_company_evidence"},
        )
        for step in steps:
            if step.decision == "RUN_TOOL":
                self.assertIsNotNone(step.tool, "RUN_TOOL decision must have a tool set")


# ── Helpers ───────────────────────────────────────────────────────────────────

class TestPolicyHelpers(unittest.TestCase):

    def test_highest_deviation_metric_picks_largest(self):
        items = [
            _make_evidence(metric="earnings", deviation=10.0, scoring_eligible=True),
            _make_evidence(metric="net_interest_income", deviation=50.0, scoring_eligible=True),
            _make_evidence(metric="total_assets", deviation=5.0, scoring_eligible=True),
        ]
        result = _highest_deviation_metric(items)
        self.assertEqual(result, "net_interest_income")

    def test_highest_deviation_metric_ignores_ineligible(self):
        items = [
            _make_evidence(metric="earnings", deviation=1000.0, scoring_eligible=False),
            _make_evidence(metric="net_interest_income", deviation=5.0, scoring_eligible=True),
        ]
        result = _highest_deviation_metric(items)
        self.assertEqual(result, "net_interest_income")

    def test_highest_deviation_metric_returns_none_if_all_ineligible(self):
        items = [
            _make_evidence(metric="earnings", deviation=50.0, scoring_eligible=False),
        ]
        result = _highest_deviation_metric(items)
        self.assertIsNone(result)

    def test_corroborating_metrics_excludes_primary(self):
        items = [
            _make_evidence(metric="net_interest_income", deviation=50.0, scoring_eligible=True),
            _make_evidence(metric="earnings", deviation=10.0, scoring_eligible=True),
        ]
        result = _corroborating_metrics(items, "net_interest_income")
        self.assertNotIn("net_interest_income", result)
        self.assertIn("earnings", result)

    def test_corroborating_metrics_requires_meaningful_deviation(self):
        items = [
            _make_evidence(metric="net_interest_income", deviation=50.0, scoring_eligible=True),
            _make_evidence(metric="earnings", deviation=0.5, scoring_eligible=True),  # < 1%
        ]
        result = _corroborating_metrics(items, "net_interest_income")
        # earnings deviation 0.5% is below threshold
        self.assertNotIn("earnings", result)

    def test_fmt_deviation_formats_positive(self):
        self.assertEqual(_fmt_deviation(5.3), "+5.3%")

    def test_fmt_deviation_formats_negative(self):
        self.assertEqual(_fmt_deviation(-12.7), "-12.7%")

    def test_fmt_deviation_handles_none(self):
        self.assertEqual(_fmt_deviation(None), "—")


if __name__ == "__main__":
    unittest.main()
