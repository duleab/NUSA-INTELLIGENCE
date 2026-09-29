import unittest

import pandas as pd

from nusa.discovery.anomaly import rank_anomalies
from nusa.discovery.banks import BankUniverse, normalize_bank_universe
from nusa.discovery.workflow import discover_banks
from nusa.providers.sectors import FixtureBankDataProvider


class BankUniverseTests(unittest.TestCase):
    def test_normalizes_documented_screener_results_and_query_values(self):
        payload = {
            "results": [
                {
                    "symbol": "bbri",
                    "company_name": "Bank Rakyat Indonesia",
                    "query_values": {"revenue[2024]": 100, "revenue[2023]": 80},
                }
            ],
            "pagination": {"limit": 50, "offset": 0},
        }

        universe = normalize_bank_universe(payload)

        self.assertIsInstance(universe, BankUniverse)
        self.assertEqual(universe.frame.loc[0, "ticker"], "BBRI")
        self.assertEqual(universe.frame.loc[0, "company_name"], "Bank Rakyat Indonesia")
        self.assertEqual(universe.frame.loc[0, "revenue[2024]"], 100)
        self.assertEqual(universe.frame.loc[0, "revenue[2023]"], 80)

    def test_missing_optional_values_are_preserved_as_missing(self):
        universe = normalize_bank_universe({"results": [{"symbol": "BBCA"}]})

        self.assertTrue(pd.isna(universe.frame.loc[0, "company_name"]))

    def test_query_values_cannot_overwrite_company_identity(self):
        universe = normalize_bank_universe(
            {"results": [{"symbol": "BBCA", "query_values": {"ticker": "FAKE"}}]}
        )
        self.assertEqual(universe.frame.loc[0, "ticker"], "BBCA")

    def test_rejects_unexpected_screener_shape(self):
        with self.assertRaises(ValueError):
            normalize_bank_universe({"data": []})


class AnomalyTests(unittest.TestCase):
    def test_ranks_cross_sectional_yoy_changes_with_explainable_components(self):
        # Synthetic test values only; not a live Sectors response.
        frame = pd.DataFrame(
            [
                {
                    "ticker": "BBCA", "company_name": "A", "revenue[2024]": 110,
                    "revenue[2023]": 100, "eps[2024]": 11, "eps[2023]": 10,
                },
                {
                    "ticker": "BBRI", "company_name": "B", "revenue[2024]": 108,
                    "revenue[2023]": 100, "eps[2024]": 10.8, "eps[2023]": 10,
                },
                {
                    "ticker": "BMRI", "company_name": "C", "revenue[2024]": 112,
                    "revenue[2023]": 100, "eps[2024]": 11.2, "eps[2023]": 10,
                },
                {
                    "ticker": "BBNI", "company_name": "D", "revenue[2024]": 105,
                    "revenue[2023]": 100, "eps[2024]": 10.5, "eps[2023]": 10,
                },
                {
                    "ticker": "BRIS", "company_name": "E", "revenue[2024]": 200,
                    "revenue[2023]": 100, "eps[2024]": 20, "eps[2023]": 10,
                },
            ]
        )

        ranked = rank_anomalies(frame)

        self.assertEqual(ranked.iloc[0]["ticker"], "BRIS")
        self.assertGreaterEqual(ranked.iloc[0]["score"], 0)
        self.assertLessEqual(ranked.iloc[0]["score"], 100)
        self.assertTrue(ranked.iloc[0]["components"])
        self.assertIn("revenue", [item["metric"] for item in ranked.iloc[0]["components"]])

    def test_abstains_when_peer_or_history_coverage_is_insufficient(self):
        frame = pd.DataFrame(
            [{"ticker": "BBCA", "revenue[2024]": 100, "revenue[2023]": 50}]
        )

        ranked = rank_anomalies(frame)

        self.assertEqual(len(ranked), 0)

    def test_missing_and_zero_denominator_values_do_not_create_scores(self):
        frame = pd.DataFrame(
            [
                {"ticker": "A", "revenue[2024]": 10, "revenue[2023]": 0},
                {"ticker": "B", "revenue[2024]": 11, "revenue[2023]": 0},
                {"ticker": "C", "revenue[2024]": None, "revenue[2023]": 2},
                {"ticker": "D", "revenue[2024]": 8, "revenue[2023]": 0},
            ]
        )

        self.assertTrue(rank_anomalies(frame).empty)

    def test_discovery_runs_end_to_end_without_an_llm(self):
        payload = {
            "results": [
                {"symbol": symbol, "query_values": {"revenue[2024]": latest, "revenue[2023]": 100}}
                for symbol, latest in [
                    ("BBCA", 110), ("BBRI", 108), ("BMRI", 112),
                    ("BBNI", 105), ("BRIS", 200),
                ]
            ]
        }

        provider = FixtureBankDataProvider(
            payload,
            source_label="DEMO/SAMPLE synthetic test fixture",
            data_mode="synthetic",
        )
        result = discover_banks(provider)

        self.assertEqual(len(result.universe.frame), 5)
        self.assertEqual(result.ranked.iloc[0]["ticker"], "BRIS")
        self.assertFalse(result.status.is_live)


if __name__ == "__main__":
    unittest.main()
