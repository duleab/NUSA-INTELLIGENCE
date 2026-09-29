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
            self.assertIn("DEMO/SAMPLE", visible_text)
            self.assertIn("DEMO/SAMPLE DATA", " ".join(item.value for item in app.warning))

            app.button(key="analyze_banks").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.dataframe)

            app.button(key="run_investigation").click().run()
            self.assertFalse(app.exception)
            rendered_text = " ".join(element.value for element in app.markdown)
            self.assertIn("Research workflow", rendered_text)
            self.assertIn("Research report", rendered_text)


if __name__ == "__main__":
    unittest.main()
