import unittest

from nusa.ui.presentation import (
    chart_numeric_value,
    format_change,
    format_evidence_value,
    format_idr_value,
    format_retrieved_date,
    comparison_table_rows,
)


class PresentationFormattingTests(unittest.TestCase):
    def test_formats_large_idr_values_without_scientific_notation(self):
        self.assertEqual(format_idr_value(606_840_000_000), "IDR 606.84B")
        self.assertEqual(format_idr_value(1_576_274_000_000), "IDR 1.58T")
        self.assertEqual(format_idr_value(None), "—")

    def test_formats_percentage_percentage_point_and_idr_changes(self):
        self.assertEqual(format_change(159.7495, "percent"), "+159.75%")
        self.assertEqual(format_change(-0.0701, "percentage_points"), "−0.07 pp")
        self.assertEqual(format_change(-1_250_000_000, "IDR"), "−IDR 1.25B")
        self.assertEqual(format_change(None, "percent"), "—")

    def test_formats_retrieval_timestamp_as_a_human_date(self):
        self.assertEqual(
            format_retrieved_date("2026-10-06T08:26:58.260744+00:00"),
            "6 Oct 2026",
        )
        self.assertEqual(format_retrieved_date(None), "Not recorded")

    def test_formats_roa_as_a_percent_and_financial_statement_values_as_idr(self):
        self.assertEqual(format_evidence_value(0.0134, "roa"), "1.34%")
        self.assertEqual(format_evidence_value(606_840_000_000, "net_interest_income"), "IDR 606.84B")
        self.assertEqual(format_evidence_value(1.2, "roa", data_mode="fixture"), "1.20% sample")
        self.assertEqual(
            format_evidence_value(606.84, "net_interest_income", data_mode="fixture"),
            "606.84 sample units",
        )

    def test_chart_numeric_value_converts_roa_to_percent(self):
        self.assertEqual(chart_numeric_value(0.0134, "roa"), 1.34)

    def test_comparison_rows_use_metric_units_and_keep_evidence_ids(self):
        rows = comparison_table_rows(
            [
                {
                    "ticker": "SUPA.JK",
                    "metric": "net_interest_income",
                    "period": "2024 to 2025",
                    "change": 159.7495,
                    "change_unit": "percent",
                    "peer_median": 1.6903,
                    "deviation": 158.0592,
                    "peer_count": 47,
                    "evidence_id": "ev-1",
                }
            ]
        )
        self.assertEqual(rows[0]["Change"], "+159.75%")
        self.assertEqual(rows[0]["Peer median"], "+1.69%")
        self.assertEqual(rows[0]["Evidence ID"], "ev-1")


if __name__ == "__main__":
    unittest.main()
