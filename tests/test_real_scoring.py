import unittest

import pandas as pd

from nusa.discovery.anomaly import rank_anomalies
from nusa.discovery.evidence import evidence_from_anomalies
from nusa.discovery.banks import BankUniverse
from nusa.discovery.workflow import build_discovery_data
from nusa.providers.base import DataSourceStatus
from nusa.agent.synthesis import LLMResearchSynthesizer


REAL_METRICS = [
    "earnings",
    "net_interest_income",
    "total_assets",
    "total_equity",
    "roa",
]


def sample_frame():
    rows = [
        ("DEMOBANK1", 100, 110, 100, 110, 1000, 1100, 100, 110, 0.01, 0.02),
        ("DEMOBANK2", 100, 90, 100, 90, 1000, 900, 100, 95, 0.02, 0.01),
        ("DEMOBANK3", -100, 100, 100, 110, 1000, 1050, 100, 100, 0.02, 0.025),
        ("DEMOBANK4", 0, 10, 100, 105, 1000, 1000, 100, 100, 0.02, 0.02),
        ("DEMOBANK5", 0.5, 5, 100, 95, 1000, 1000, 100, 100, 0.01, 0.01),
        ("DEMOBANK6", 100, 100, 100, 100, 1000, 950, 100, 100, 0.01, 0.01),
        ("DEMOBANK7", 100, 105, 100, 105, 1000, 1020, 100, 101, 0.01, 0.011),
        ("DEMOBANK8", -100, -80, 100, 100, 1000, 1000, 100, 100, 0.01, 0.01),
    ]
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "company_name": ticker,
                "earnings[2024]": earn_24,
                "earnings[2025]": earn_25,
                "net_interest_income[2024]": nii_24,
                "net_interest_income[2025]": nii_25,
                "total_assets[2024]": assets_24,
                "total_assets[2025]": assets_25,
                "total_equity[2024]": equity_24,
                "total_equity[2025]": equity_25,
                "roa[2024]": roa_24,
                "roa[2025]": roa_25,
                "net_interest_margin[2024]": 0.01,
                "net_interest_margin[2025]": 0.02,
            }
            for (
                ticker, earn_24, earn_25, nii_24, nii_25, assets_24, assets_25,
                equity_24, equity_25, roa_24, roa_25,
            ) in rows
        ]
    )


class RealScoringTests(unittest.TestCase):
    def test_real_metric_allowlist_excludes_nim_and_computes_roa_in_percentage_points(self):
        ranked = rank_anomalies(sample_frame(), metric_allowlist=REAL_METRICS)
        bank = ranked.loc[ranked["ticker"] == "DEMOBANK1"].iloc[0]
        components = {item["metric"]: item for item in bank["components"]}

        self.assertNotIn("net_interest_margin", components)
        self.assertEqual(components["roa"]["change"], 1.0)
        self.assertEqual(components["roa"]["change_unit"], "percentage_points")

    def test_monetary_changes_use_absolute_denominator_for_same_sign_negative_values(self):
        ranked = rank_anomalies(sample_frame(), metric_allowlist=["earnings"])
        bank = ranked.loc[ranked["ticker"] == "DEMOBANK8"].iloc[0]
        earnings = next(item for item in bank["components"] if item["metric"] == "earnings")

        self.assertTrue(earnings["scoring_eligible"])
        self.assertEqual(earnings["change"], 20.0)
        self.assertEqual(earnings["change_unit"], "percent")

    def test_sign_zero_and_small_base_values_are_ineligible_not_zero_scored(self):
        ranked = rank_anomalies(sample_frame(), metric_allowlist=REAL_METRICS)

        cases = {
            "DEMOBANK3": "SIGN_TRANSITION",
            "DEMOBANK4": "ZERO_BASE",
            "DEMOBANK5": "SMALL_BASE",
        }
        for ticker, reason in cases.items():
            with self.subTest(ticker=ticker):
                row = ranked.loc[ranked["ticker"] == ticker].iloc[0]
                item = next(component for component in row["components"] if component["metric"] == "earnings")
                self.assertFalse(item["scoring_eligible"])
                self.assertIn(reason, item["exclusion_reasons"])
                self.assertIsNone(item["contribution"])
                self.assertIn("earnings", [flag["metric"] for flag in row["excluded_metric_flags"]])

    def test_all_monetary_fields_flag_sign_zero_and_small_base_cases(self):
        for metric in ("earnings", "net_interest_income", "total_assets", "total_equity"):
            with self.subTest(metric=metric):
                frame = sample_frame()
                prior = f"{metric}[2024]"
                current = f"{metric}[2025]"
                frame[prior] = frame[prior].astype(float)
                frame[current] = frame[current].astype(float)
                frame.loc[2, current] = -frame.loc[2, prior]
                frame.loc[3, prior] = 0
                frame.loc[4, prior] = 0.5
                ranked = rank_anomalies(frame, metric_allowlist=[metric, "roa"])

                for ticker, expected in (
                    ("DEMOBANK3", "SIGN_TRANSITION"),
                    ("DEMOBANK4", "ZERO_BASE"),
                    ("DEMOBANK5", "SMALL_BASE"),
                ):
                    bank = ranked.loc[ranked["ticker"] == ticker].iloc[0]
                    component = next(
                        item for item in bank["components"] if item["metric"] == metric
                    )
                    self.assertIn(expected, component["exclusion_reasons"])
                    self.assertIsNone(component["contribution"])
                    if expected == "SMALL_BASE":
                        expected_threshold = frame[prior].abs().median() * 0.01
                        self.assertEqual(
                            component["small_base_threshold"], expected_threshold
                        )

    def test_real_source_workflow_uses_only_initial_hackathon_metric_allowlist(self):
        frame = sample_frame()
        data = build_discovery_data(
            BankUniverse(frame=frame, pagination={"total_count": len(frame)}),
            DataSourceStatus(
                mode="cached_sectors",
                source="SECTORS CACHED SNAPSHOT",
                is_live=False,
                retrieved_at="2026-10-06T08:26:58.260744+00:00",
            ),
            data_mode="cached",
        )

        self.assertEqual(
            {item.metric for item in data.evidence_ledger},
            set(REAL_METRICS),
        )
        self.assertNotIn(
            "net_interest_margin",
            {item.metric for item in data.evidence_ledger},
        )

    def test_fallback_report_labels_percentage_points_and_excluded_earnings(self):
        frame = sample_frame()
        ranked = rank_anomalies(frame, metric_allowlist=REAL_METRICS)
        ledger = evidence_from_anomalies(
            frame,
            ranked,
            retrieved_at="2026-10-06T08:26:58.260744+00:00",
            data_mode="cached",
            source="SECTORS CACHED SNAPSHOT",
        )
        report = LLMResearchSynthesizer().synthesize(
            "Investigate DEMOBANK3", {"intent": "INVESTIGATE"}, ledger
        )
        text = " ".join(report.key_findings)

        self.assertIn("percentage points", text)
        self.assertIn("percentage change not used for scoring", text)

    def test_leave_one_out_peer_median_does_not_include_company_value(self):
        frame = pd.DataFrame(
            [
                {"ticker": f"DEMOBANK{index}", "total_assets[2024]": 100, "total_assets[2025]": current}
                for index, current in enumerate((110, 110, 110, 110, 200), start=1)
            ]
        )
        ranked = rank_anomalies(frame, metric_allowlist=["total_assets"])
        outlier = ranked.loc[ranked["ticker"] == "DEMOBANK5"].iloc[0]
        component = outlier["components"][0]

        self.assertEqual(component["peer_count"], 4)
        self.assertEqual(component["peer_median"], 10.0)

    def test_composite_score_is_normalized_and_coverage_adjusted(self):
        ranked = rank_anomalies(sample_frame(), metric_allowlist=REAL_METRICS)
        self.assertTrue(((ranked["score"] >= 0) & (ranked["score"] <= 100)).all())
        row = ranked.loc[ranked["ticker"] == "DEMOBANK3"].iloc[0]
        eligible = [item for item in row["components"] if item["scoring_eligible"]]
        mean_contribution = sum(item["contribution"] for item in eligible) / len(eligible)

        self.assertEqual(row["eligible_metric_count"], len(eligible))
        self.assertEqual(row["metric_coverage"], len(eligible) / len(REAL_METRICS))
        self.assertEqual(
            row["score"], round(mean_contribution * row["metric_coverage"])
        )
        self.assertTrue(all(0 <= item["contribution"] <= 100 for item in eligible))

    def test_evidence_keeps_roa_units_and_sign_transition_reason(self):
        frame = sample_frame()
        ranked = rank_anomalies(frame, metric_allowlist=REAL_METRICS)
        ledger = evidence_from_anomalies(
            frame,
            ranked,
            retrieved_at="2026-10-06T08:26:58.260744+00:00",
            data_mode="cached",
            source="SECTORS CACHED SNAPSHOT",
        )
        roa = next(item for item in ledger.by_ticker("DEMOBANK1") if item.metric == "roa")
        crossing = next(item for item in ledger.by_ticker("DEMOBANK3") if item.metric == "earnings")

        self.assertEqual(roa.change, 1.0)
        self.assertEqual(roa.change_unit, "percentage_points")
        self.assertTrue(roa.scoring_eligible)
        self.assertFalse(crossing.scoring_eligible)
        self.assertEqual(crossing.change_unit, "IDR")
        self.assertEqual(crossing.exclusion_reason, "SIGN_TRANSITION")
        self.assertIn("percentage change not used", crossing.calculation)
        self.assertEqual(ledger.validate(), {})


if __name__ == "__main__":
    unittest.main()
