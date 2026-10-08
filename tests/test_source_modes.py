import unittest

from nusa.ui.source_modes import (
    format_excluded_metric_flags,
    format_source_status,
    source_mode_options,
)


class SourceModeTests(unittest.TestCase):
    def test_cached_snapshot_is_default_only_when_present(self):
        self.assertEqual(
            source_mode_options(snapshot_available=True),
            [
                ("cached_sectors", "SECTORS CACHED SNAPSHOT"),
                ("demo", "DEMO/SAMPLE"),
                ("live", "LIVE SECTORS"),
            ],
        )
        self.assertEqual(
            source_mode_options(snapshot_available=False),
            [("demo", "DEMO/SAMPLE"), ("live", "LIVE SECTORS")],
        )

    def test_cached_status_is_not_reported_as_demo_or_live(self):
        display = format_source_status("cached_sectors", "2026-10-06T08:26:58+00:00")
        self.assertEqual(display["badge"], "SECTORS CACHED SNAPSHOT")
        self.assertIn("Sectors-origin data retrieved 2026-10-06T08:26:58+00:00", display["message"])
        self.assertIn("Not a live refresh", display["message"])
        self.assertEqual(display["kind"], "info")

    def test_live_and_demo_have_distinct_truthful_labels(self):
        live = format_source_status("live")
        demo = format_source_status("demo")
        self.assertEqual(live["badge"], "LIVE SECTORS DATA")
        self.assertEqual(demo["badge"], "DEMO/SAMPLE DATA")
        self.assertIn("Synthetic demonstration values", demo["message"])
        self.assertNotEqual(live["message"], demo["message"])
        self.assertNotIn("Retrieved", live["message"])
        with self.assertRaises(ValueError):
            format_source_status("unknown")

    def test_excluded_metric_flags_render_the_reason_or_an_empty_marker(self):
        self.assertEqual(format_excluded_metric_flags([]), "—")
        self.assertEqual(
            format_excluded_metric_flags(
                [{"metric": "earnings", "reason": "SIGN_TRANSITION"}]
            ),
            "Earnings · excluded from % scoring — sign transition",
        )


if __name__ == "__main__":
    unittest.main()
