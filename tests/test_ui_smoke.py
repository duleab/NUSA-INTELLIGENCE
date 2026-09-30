import unittest
import os
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class StreamlitApplicationTests(unittest.TestCase):
    def test_home_renders_three_research_sections_with_demo_warning(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch.dict(os.environ, {"NUSA_LLM_API_KEY": ""}):
            app = AppTest.from_file(str(app_path), default_timeout=15).run()

            self.assertFalse(app.exception)
            visible_text = " ".join(element.value for element in app.markdown)
            self.assertEqual(
                [tab.label for tab in app.tabs], ["DISCOVER", "INVESTIGATE", "METHODOLOGY"]
            )
            self.assertIn("LIVE — Sectors", app.selectbox[0].options)
            self.assertIn("DEMO/SAMPLE", visible_text)
            source_warning = " ".join(item.value for item in app.warning)
            self.assertIn("DEMO/SAMPLE DATA", source_warning)
            self.assertIn("Synthetic demonstration values", source_warning)
            self.assertIn("Not current market data", source_warning)

            app.button(key="demo_discover_example").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.dataframe)

            self.assertTrue(any(button.key == "demo_discover_example" for button in app.button))
            self.assertTrue(any(button.key == "demo_investigate_top" for button in app.button))

            app.button(key="demo_investigate_top").click().run()
            self.assertFalse(app.exception)
            app.button(key="run_investigation").click().run()
            self.assertFalse(app.exception)
            rendered_text = " ".join(element.value for element in app.markdown)
            self.assertIn("Research workflow", rendered_text)
            self.assertIn("Research report", rendered_text)

            app.button(key="demo_comparison_example").click().run()
            self.assertFalse(app.exception)
            app.button(key="run_followup_comparison").click().run()
            self.assertFalse(app.exception)
            rendered_text = " ".join(element.value for element in app.markdown)
            self.assertIn("Follow-up peer comparison", rendered_text)
            self.assertIn("DEMOBANK", rendered_text)
            followup = app.session_state["nusa_followup_result"]
            self.assertEqual(followup.plan.tickers, ("DEMOBANK5", "DEMOBANK2", "DEMOBANK3"))
            self.assertEqual(
                followup.plan.tasks[0].arguments["metric"],
                app.session_state["nusa_research_memory"].last_anomaly_metric,
            )


if __name__ == "__main__":
    unittest.main()
