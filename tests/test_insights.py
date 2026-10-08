"""Unit tests for deterministic UI insights module (nusa.ui.insights)."""

import unittest
from nusa.ui import insights as ins
from nusa.discovery.evidence import Evidence


def _sample_discovery_row():
    return {
        "ticker": "SUPA.JK",
        "company_name": "Bank Supra",
        "score": 79,
        "eligible_metric_count": 4,
        "metric_coverage": 0.8,
        "primary_driver": "net_interest_income",
        "primary_change": 159.75,
        "primary_change_unit": "percent",
        "primary_peer_median": 1.69,
        "primary_deviation": 158.06,
        "components": [
            {
                "metric": "net_interest_income",
                "period": "2024 to 2025",
                "change": 159.75,
                "change_unit": "percent",
                "peer_median": 1.69,
                "peer_count": 46,
                "deviation": 158.06,
                "contribution": 100.0,
                "scoring_eligible": True,
                "exclusion_reason": None,
                "previous_value": 100.0,
                "current_value": 259.75,
            },
            {
                "metric": "total_assets",
                "period": "2024 to 2025",
                "change": 86.77,
                "change_unit": "percent",
                "peer_median": 9.48,
                "peer_count": 47,
                "deviation": 77.29,
                "contribution": 100.0,
                "scoring_eligible": True,
                "exclusion_reason": None,
                "previous_value": 1000.0,
                "current_value": 1867.7,
            },
            {
                "metric": "total_equity",
                "period": "2024 to 2025",
                "change": 55.59,
                "change_unit": "percent",
                "peer_median": 4.44,
                "peer_count": 47,
                "deviation": 51.15,
                "contribution": 97.9,
                "scoring_eligible": True,
                "exclusion_reason": None,
                "previous_value": 200.0,
                "current_value": 311.18,
            },
            {
                "metric": "roa",
                "period": "2024 to 2025",
                "change": 3.68,
                "change_unit": "percentage_points",
                "peer_median": -0.09,
                "peer_count": 47,
                "deviation": 3.77,
                "contribution": 95.8,
                "scoring_eligible": True,
                "exclusion_reason": None,
                "previous_value": 0.5,
                "current_value": 4.18,
            },
            {
                "metric": "earnings",
                "period": "2024 to 2025",
                "change": 466051000000.0,
                "change_unit": "IDR",
                "peer_median": None,
                "peer_count": 0,
                "deviation": None,
                "contribution": None,
                "scoring_eligible": False,
                "exclusion_reason": "SIGN_TRANSITION",
                "absolute_change": 466051000000.0,
                "previous_value": -1000000.0,
                "current_value": 466050000000.0,
            },
        ],
    }


class TestUIInsights(unittest.TestCase):

    def test_why_this_bank_bullets(self):
        row = _sample_discovery_row()
        bullets = ins.why_this_bank(row, universe_size=48)
        self.assertGreater(len(bullets), 3)
        self.assertTrue(any("79/100" in b for b in bullets))
        self.assertTrue(any("primary driver" in b for b in bullets))
        self.assertTrue(any("sign transition" in b for b in bullets))

    def test_anomaly_decomposition_formula(self):
        row = _sample_discovery_row()
        dec = ins.anomaly_decomposition(row)
        self.assertEqual(dec.score, 79)
        self.assertEqual(dec.coverage_scored, 4)
        self.assertEqual(dec.coverage_total, 5)
        self.assertIn("Score 79", dec.formula)
        self.assertEqual(len(dec.rows), 5)
        levels = [r["Level"] for r in dec.rows]
        self.assertIn("High", levels)
        self.assertIn("Excluded", levels)

    def test_investigation_questions_engine(self):
        row = _sample_discovery_row()
        qs = ins.investigation_questions(row)
        self.assertGreaterEqual(len(qs), 3)
        q_texts = [q.question for q in qs]
        self.assertTrue(any("NII" in t for t in q_texts))
        self.assertTrue(any("asset growth" in t for t in q_texts))
        self.assertTrue(any("profitability" in t or "ROA" in t for t in q_texts))

    def test_what_changed_panel(self):
        row = _sample_discovery_row()
        p = ins.what_changed_panel(row)
        self.assertIn("NII", p["what_changed"])
        self.assertIn("Peer median", p["why_unusual"])
        self.assertGreater(len(p["what_next"]), 0)

    def test_evidence_coverage_measurable(self):
        ev = [
            Evidence(
                ticker="SUPA.JK",
                metric="net_interest_income",
                period="2024 to 2025",
                source="test",
                source_endpoint="/v2/companies/",
                retrieved_at="2026-10-06T08:00:00Z",
                calculation="calc",
                data_mode="cached",
                company_name="Bank Supra",
                previous_value=100.0,
                current_value=259.75,
                change=159.75,
                peer_median=1.69,
                peer_count=46,
                deviation=158.06,
                change_unit="percent",
                scoring_eligible=True,
                exclusion_reason=None,
                absolute_change=159.75,
                scoring_contribution=100.0,
            )
        ]
        cov = ins.evidence_coverage(ev, ticker="SUPA.JK", validated=True, universe_size=48)
        self.assertEqual(cov["records_total"], 1)
        self.assertEqual(cov["records_validated"], 1)
        self.assertEqual(cov["universe_size"], 48)
        self.assertTrue(cov["all_validated"])

    def test_answer_structured_followup_intents(self):
        row = _sample_discovery_row()
        ranked = [row]

        ans_why = ins.answer_structured_followup("Why was this bank ranked first?", row, ranked_rows=ranked)
        self.assertIsNotNone(ans_why)
        self.assertEqual(ans_why.intent, "WHY_RANKED")

        ans_strongest = ins.answer_structured_followup("Show the strongest contributing metric.", row, ranked_rows=ranked)
        self.assertIsNotNone(ans_strongest)
        self.assertEqual(ans_strongest.intent, "STRONGEST")

        ans_roa = ins.answer_structured_followup("Compare its ROA with peers.", row, ranked_rows=ranked)
        self.assertIsNotNone(ans_roa)
        self.assertEqual(ans_roa.intent, "METRIC")

        ans_excl = ins.answer_structured_followup("What metrics were excluded and why?", row, ranked_rows=ranked)
        self.assertIsNotNone(ans_excl)
        self.assertEqual(ans_excl.intent, "EXCLUDED")

        ans_unrelated = ins.answer_structured_followup("Compare this change with BBRI and BBCA", row, ranked_rows=ranked)
        self.assertIsNone(ans_unrelated)


if __name__ == "__main__":
    unittest.main()
