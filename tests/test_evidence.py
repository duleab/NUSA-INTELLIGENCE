import json
import unittest

import pandas as pd

from nusa.discovery.evidence import (
    Evidence,
    EvidenceLedger,
    EvidenceValidator,
    evidence_from_anomalies,
)
from nusa.discovery.workflow import discover_banks
from nusa.providers.sectors import FixtureBankDataProvider


class EvidenceLedgerTests(unittest.TestCase):
    def make_evidence(self, **overrides):
        values = {
            "ticker": "DEMOBANK1",
            "company_name": "Archipelago Sample Bank",
            "metric": "revenue",
            "current_value": 120.0,
            "previous_value": 100.0,
            "change": 20.0,
            "peer_median": 8.0,
            "peer_count": 4,
            "deviation": 12.0,
            "period": "2024 to 2025",
            "source": "Sectors Financial API",
            "source_endpoint": "/v2/companies/",
            "retrieved_at": "2026-09-29T10:00:00+00:00",
            "calculation": "(current / previous - 1) * 100",
            "data_mode": "unknown",
        }
        values.update(overrides)
        return Evidence(**values)

    def test_ledger_adds_and_retrieves_evidence_by_ticker_and_metric(self):
        ledger = EvidenceLedger()
        item = self.make_evidence()
        ledger.add(item)

        self.assertEqual(ledger.by_ticker("demobank1"), [item])
        self.assertEqual(ledger.by_metric("REVENUE"), [item])

    def test_validator_reports_missing_required_fields_and_source(self):
        item = self.make_evidence(metric="", source="", source_endpoint="")

        errors = EvidenceValidator().validate(item)

        self.assertIn("metric is required", errors)
        self.assertIn("source is required", errors)
        self.assertIn("source_endpoint is required", errors)

    def test_validator_treats_null_required_strings_as_missing(self):
        item = self.make_evidence(ticker=None, period=None)

        errors = EvidenceValidator().validate(item)

        self.assertIn("ticker is required", errors)
        self.assertIn("period is required", errors)

    def test_validator_reports_missing_financial_values(self):
        item = self.make_evidence(current_value=None, previous_value=None)

        errors = EvidenceValidator().validate(item)

        self.assertIn("current_value is required", errors)
        self.assertIn("previous_value is required", errors)

    def test_validator_checks_ticker_consistency(self):
        errors = EvidenceValidator().validate(self.make_evidence(), expected_ticker="DEMOBANK2")

        self.assertIn("ticker does not match expected ticker DEMOBANK2", errors)

    def test_validator_rejects_incompatible_annual_periods(self):
        errors = EvidenceValidator().validate(self.make_evidence(period="2022 to 2025"))

        self.assertIn("annual comparison periods must be consecutive", errors)

    def test_validator_rejects_non_finite_numeric_evidence(self):
        errors = EvidenceValidator().validate(self.make_evidence(change=float("nan")))

        self.assertIn("change must be a finite number", errors)

    def test_conclusion_requires_supporting_ticker_evidence(self):
        validator = EvidenceValidator()

        self.assertIn(
            "conclusion has no supporting evidence",
            validator.validate_conclusion("Revenue accelerated", []),
        )
        self.assertEqual(
            validator.validate_conclusion(
                "Revenue accelerated", [self.make_evidence()], expected_ticker="DEMOBANK1"
            ),
            [],
        )

    def test_compact_llm_context_is_structured_and_serializable(self):
        ledger = EvidenceLedger([self.make_evidence()])

        context = ledger.to_llm_context(ticker="DEMOBANK1")

        self.assertEqual(context["evidence"][0]["metric"], "revenue")
        self.assertEqual(context["evidence"][0]["current_value"], 120.0)
        json.dumps(context)

    def test_anomaly_results_become_evidence_with_source_values(self):
        frame = pd.DataFrame(
            [
                {"ticker": ticker, "company_name": ticker, "revenue[2024]": 100, "revenue[2025]": val}
                for ticker, val in [("A", 110), ("B", 108), ("C", 112), ("D", 105), ("E", 200)]
            ]
        )
        from nusa.discovery.anomaly import rank_anomalies

        ranked = rank_anomalies(frame)
        ledger = evidence_from_anomalies(
            frame,
            ranked,
            retrieved_at="2026-09-29T10:00:00+00:00",
            data_mode="fixture",
        )

        result = ledger.by_ticker("E")[0]
        self.assertEqual(result.metric, "revenue")
        self.assertEqual(result.previous_value, 100)
        self.assertEqual(result.current_value, 200)
        self.assertEqual(result.change, 100.0)
        self.assertEqual(result.data_mode, "fixture")
        self.assertIn("change_pct=((current-previous)/abs(previous))*100", result.calculation)

    def test_discovery_result_exposes_evidence_ledger(self):
        payload = {
            "results": [
                {
                    "symbol": ticker,
                    "company_name": ticker,
                    "query_values": {"revenue[2024]": 100, "revenue[2025]": value},
                }
                for ticker, value in [("A", 110), ("B", 108), ("C", 112), ("D", 105), ("E", 200)]
            ]
        }

        provider = FixtureBankDataProvider(
            payload,
            source_label="DEMO/SAMPLE synthetic test fixture",
            data_mode="synthetic",
        )
        result = discover_banks(provider)

        self.assertIsInstance(result.evidence_ledger, EvidenceLedger)
        self.assertTrue(result.evidence_ledger.by_ticker("E"))


if __name__ == "__main__":
    unittest.main()
