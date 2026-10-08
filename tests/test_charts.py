import unittest

from nusa.ui import charts as chart_ui


class ChartHelperTests(unittest.TestCase):
    def test_peer_distribution_chart_frame_sorts_selected_bank_first(self):
        dist = {
            "unit": "percent",
            "bars": [
                {"label": "PEER.JK", "change": 2.0, "role": "Size-matched peer"},
                {"label": "SUBJ.JK", "change": 50.0, "role": "Selected bank"},
                {"label": "Peer median", "change": 3.0, "role": "Peer median"},
            ],
        }
        frame = chart_ui.peer_distribution_chart_frame(dist)
        self.assertIsNotNone(frame)
        self.assertEqual(list(frame.index)[0], "SUBJ.JK")

    def test_validation_from_trace_reads_evidence_counts(self):
        class _Event:
            def __init__(self, event, details):
                self.event = event
                self.details = details

        stats = chart_ui.validation_from_trace(
            [_Event("EVIDENCE_VALIDATED", {"valid": True, "evidence_count": 5, "invalid_count": 1})]
        )
        self.assertTrue(stats["valid"])
        self.assertEqual(stats["validated_count"], 4)
        self.assertEqual(stats["invalid_count"], 1)


if __name__ == "__main__":
    unittest.main()
