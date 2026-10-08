import unittest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from nusa.providers.sectors_snapshot import import_sectors_response, save_sectors_snapshot


class StreamlitApplicationTests(unittest.TestCase):
    def test_home_renders_three_research_sections_with_demo_warning(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"NUSA_LLM_API_KEY": ""}
        ), patch(
            "nusa.providers.sectors_snapshot.DEFAULT_SECTORS_SNAPSHOT_PATH",
            Path(temp_dir) / "absent-snapshot.json",
        ):
            app = AppTest.from_file(str(app_path), default_timeout=30).run()

            self.assertFalse(app.exception)
            visible_text = " ".join(element.value for element in app.markdown)
            self.assertIn("Evidence-grounded AI research for Indonesian banking", visible_text)
            self.assertIn("Discover unusual financial changes", [item.value for item in app.subheader])
            self.assertIn("Run Discovery", [button.label for button in app.button])
            self.assertTrue(any("Run Judge Demo" in button.label for button in app.button))
            self.assertIn("NUSA for judges", visible_text)
            self.assertEqual(
                [tab.label for tab in app.tabs], ["DISCOVER", "INVESTIGATE", "BANKS", "METHODOLOGY"]
            )
            self.assertIn("LIVE SECTORS", app.selectbox[0].options)
            self.assertIn("DEMO/SAMPLE", app.selectbox[0].options)
            self.assertIn("DEMO/SAMPLE", visible_text)
            source_warning = " ".join(item.value for item in app.warning)
            self.assertIn("DEMO/SAMPLE DATA", source_warning)
            self.assertIn("Synthetic demonstration values", source_warning)
            self.assertIn("Not current market data", source_warning)

            app.button(key="demo_discover_example").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(app.dataframe)
            discovery_text = " ".join(element.value for element in app.markdown)
            self.assertIn("#1 Research Priority", discovery_text)
            self.assertTrue(any(button.label.startswith("Investigate ") for button in app.button))

            self.assertTrue(any(button.key == "demo_discover_example" for button in app.button))
            self.assertTrue(any(button.key == "investigate_top_result" for button in app.button))

            app.button(key="investigate_top_result").click().run()
            self.assertFalse(app.exception)
            app.text_input(key="nusa_research_question").set_value(
                "Investigate DEMOBANK5"
            ).run()
            app.button(key="run_investigation").click().run()
            self.assertFalse(app.exception)
            self.assertIn(
                "Investigate DEMOBANK5",
                app.session_state["nusa_investigation_result"].plan.objective,
            )
            rendered_text = " ".join(element.value for element in app.markdown)
            self.assertIn("Evidence ledger", rendered_text)
            self.assertIn("Research Summary", rendered_text)

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

    def test_live_mode_failure_is_visible_and_does_not_substitute_demo_data(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"SECTORS_API_KEY": "", "NUSA_LLM_API_KEY": ""}
        ), patch(
            "nusa.providers.sectors_snapshot.DEFAULT_SECTORS_SNAPSHOT_PATH",
            Path(temp_dir) / "absent-snapshot.json",
        ), patch(
            "nusa.sectors.client.SectorsClient._read_cache",
            return_value=None,
        ):
            app = AppTest.from_file(str(app_path), default_timeout=30).run()
            self.assertFalse(app.exception)
            app.selectbox[0].select("live").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["nusa_source_mode"], "live")
            self.assertIn("LIVE SECTORS DATA", " ".join(item.value for item in app.markdown))
            app.button(key="analyze_banks").click().run()
            self.assertFalse(app.exception)
            self.assertTrue(
                app.error,
                f"source={app.selectbox[0].value}; "
                f"buttons={[button.label for button in app.button]}; "
                f"has_discovery_rows={'nusa_discovery_rows' in app.session_state}",
            )
            error_text = " ".join(item.value for item in app.error)
            self.assertIn("Could not analyze the selected source", error_text)
            self.assertNotIn("nusa_discovery_rows", app.session_state)

    def test_cached_source_badge_displays_original_retrieval_date_and_not_live_label(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        query = {
            "where": "sub_sector = 'Banks' and market_cap IS NOT NULL",
            "order_by": "-market_cap",
            "limit": 50,
            "include_query_values": True,
        }
        response = {
            "results": [
                {
                    "symbol": "TST1.JK",
                    "company_name": "Test Bank",
                    "query_values": {
                        "sub_sector": "Banks",
                        "market_cap": 1,
                        "total_assets[2024]": 10,
                        "total_assets[2025]": 11,
                    },
                }
            ],
            "pagination": {"total_count": 1},
        }
        retrieved_at = "2026-10-06T08:26:58+00:00"
        snapshot = import_sectors_response(
            response,
            query=query,
            retrieved_at=retrieved_at,
            confirmed_sectors_origin=True,
        )
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"NUSA_LLM_API_KEY": ""}
        ), patch(
            "nusa.providers.sectors_snapshot.DEFAULT_SECTORS_SNAPSHOT_PATH",
            Path(temp_dir) / "banks-snapshot.json",
        ) as snapshot_path:
            save_sectors_snapshot(snapshot, snapshot_path)
            app = AppTest.from_file(str(app_path), default_timeout=30).run()

            self.assertFalse(app.exception)
            visible_text = " ".join(element.value for element in app.markdown)
            captions = " ".join(element.value for element in app.caption)
            self.assertIn("SECTORS CACHED SNAPSHOT", visible_text)
            self.assertIn("Retrieved 6 Oct 2026", captions)
            self.assertIn("Not a live refresh", captions)

    def test_judge_demo_flow_executes_autonomous_investigation(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with patch.dict(os.environ, {"NUSA_LLM_API_KEY": ""}):
            app = AppTest.from_file(str(app_path), default_timeout=30).run()
            self.assertFalse(app.exception)
            app.selectbox[0].select("demo").run()
            self.assertFalse(app.exception)

            judge_button = next((b for b in app.button if b.key == "run_judge_demo"), None)
            self.assertIsNotNone(judge_button)
            judge_button.click().run()
            self.assertFalse(app.exception)

            self.assertIn("nusa_deep_result", app.session_state)
            deep_res = app.session_state["nusa_deep_result"]
            self.assertIsNotNone(deep_res)
            self.assertTrue(deep_res.ticker.startswith("DEMOBANK") or deep_res.ticker == "SUPA.JK")

            all_markdown = " ".join(element.value for element in app.markdown)
            self.assertIn("Autonomous investigation complete", all_markdown)
            self.assertIn("Key Investigation Insights", all_markdown)
            self.assertIn("What Changed", all_markdown)
            self.assertIn("Why It Is Unusual", all_markdown)
            self.assertIn("What NUSA Did", all_markdown)
            self.assertIn("What to Investigate Next", all_markdown)
            self.assertIn("Evidence Strength & Verification", all_markdown)

    def test_switching_source_mode_clears_deep_investigation_and_followup_state(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"NUSA_LLM_API_KEY": ""}
        ), patch(
            "nusa.providers.sectors_snapshot.DEFAULT_SECTORS_SNAPSHOT_PATH",
            Path(temp_dir) / "absent-snapshot.json",
        ):
            app = AppTest.from_file(str(app_path), default_timeout=30).run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["nusa_source_mode"], "demo")

            app.button(key="run_judge_demo").click().run()
            self.assertFalse(app.exception)
            self.assertIn("nusa_deep_result", app.session_state)
            self.assertIsNotNone(app.session_state["nusa_deep_result"])
            self.assertTrue(
                str(app.session_state["nusa_deep_result"].ticker).startswith("DEMOBANK")
            )

            source_box = next(box for box in app.selectbox if any("LIVE" in str(opt).upper() for opt in box.options))
            source_box.select("live").run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state["nusa_source_mode"], "live")
            self.assertNotIn("nusa_deep_result", app.session_state)
            self.assertNotIn("nusa_structured_followup_answer", app.session_state)
            self.assertNotIn("nusa_followup_result", app.session_state)
            self.assertNotIn("nusa_discovery_rows", app.session_state)
            self.assertNotIn("nusa_investigation_result", app.session_state)
            self.assertNotIn("nusa_selected_ticker", app.session_state)

    def test_banks_tab_renders_grid_and_allows_selection(self):
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        with tempfile.TemporaryDirectory() as temp_dir, patch.dict(
            os.environ, {"NUSA_LLM_API_KEY": ""}
        ), patch(
            "nusa.providers.sectors_snapshot.DEFAULT_SECTORS_SNAPSHOT_PATH",
            Path(temp_dir) / "absent-snapshot.json",
        ):
            app = AppTest.from_file(str(app_path), default_timeout=30).run()
            self.assertFalse(app.exception)
            subheaders = [item.value for item in app.subheader]
            self.assertTrue(any("Indonesian Banking Universe" in s for s in subheaders))
            self.assertTrue(any("Total Banks" in m.label for m in app.metric))
            self.assertTrue(any("Vector Brand Logos" in m.label for m in app.metric))
            # Find any bank grid investigation button
            bank_inv_btn = next((b for b in app.button if b.key and b.key.startswith("inv_btn_grid_")), None)
            self.assertIsNotNone(bank_inv_btn)
            bank_inv_btn.click().run()
            self.assertFalse(app.exception)
            self.assertIn("nusa_selected_ticker", app.session_state)
            self.assertTrue(
                str(app.session_state["nusa_selected_ticker"]).startswith("DEMOBANK")
                or str(app.session_state["nusa_selected_ticker"]).endswith(".JK")
            )


if __name__ == "__main__":
    unittest.main()

