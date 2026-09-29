import json
import tempfile
import unittest
from pathlib import Path

from nusa.discovery.workflow import discover_banks
from nusa.providers.base import CompanyData, DataSourceStatus
from nusa.providers.sectors import (
    FixtureBankDataProvider,
    SectorsBankDataProvider,
    create_bank_data_provider,
)
from nusa.sectors.client import SectorsAPIError


def playground_payload():
    return {
        "results": [
            {
                "symbol": ticker,
                "company_name": f"SAMPLE BANK {ticker}",
                "query_values": {
                    "revenue[2024]": 100,
                    "revenue[2025]": value,
                    "sub_sector": "Banks",
                },
            }
            for ticker, value in [
                ("DEMO001", 110),
                ("DEMO002", 108),
                ("DEMO003", 112),
                ("DEMO004", 105),
                ("DEMO005", 200),
            ]
        ],
        "pagination": {"total_count": 5, "showing": 5, "limit": 50},
    }


class FakeSectorsClient:
    def __init__(self, payload=None, error=None):
        self.payload = payload or playground_payload()
        self.error = error
        self.calls = []

    def companies_screener(self, **kwargs):
        self.calls.append(("screener", kwargs))
        if self.error:
            raise self.error
        return self.payload

    def company_report(self, ticker, **kwargs):
        self.calls.append(("report", ticker, kwargs))
        if self.error:
            raise self.error
        return {"symbol": ticker, "financials": {"source": "live-fixture-client"}}


class ProviderTests(unittest.TestCase):
    def test_provider_selection_requires_explicit_mode(self):
        client = FakeSectorsClient()

        live = create_bank_data_provider("live", client=client)
        demo = create_bank_data_provider("demo")

        self.assertIsInstance(live, SectorsBankDataProvider)
        self.assertIsInstance(demo, FixtureBankDataProvider)
        with self.assertRaises(ValueError):
            create_bank_data_provider("automatic")

    def test_live_provider_propagates_api_error_without_fixture_fallback(self):
        api_error = SectorsAPIError(403, "/v2/companies/")
        client = FakeSectorsClient(error=api_error)
        provider = create_bank_data_provider("live", client=client)

        with self.assertRaises(SectorsAPIError) as raised:
            provider.get_discovery_data()

        self.assertIs(raised.exception, api_error)
        self.assertEqual([call[0] for call in client.calls], ["screener"])
        self.assertTrue(provider.status.is_live)
        self.assertIn("no demo fallback", provider.status.warning)
        self.assertIsNone(provider.status.retrieved_at)

    def test_bundled_demo_is_labeled_and_never_claimed_live(self):
        provider = create_bank_data_provider("demo")

        universe_result = provider.get_bank_universe()
        discovery = provider.get_discovery_data()

        self.assertFalse(universe_result.status.is_live)
        self.assertIn("DEMO/SAMPLE", universe_result.status.source)
        self.assertIn("not live", universe_result.status.warning.lower())
        self.assertTrue(all(ticker.startswith("DEMO") for ticker in universe_result.universe.frame["ticker"]))
        self.assertTrue(all(e.data_mode == "synthetic" for e in discovery.evidence_ledger))
        self.assertTrue(all(e.source == universe_result.status.source for e in discovery.evidence_ledger))
        self.assertTrue(all(e.source_endpoint == "fixture://local" for e in discovery.evidence_ledger))
        self.assertEqual(discovery.status.mode, "demo")

    def test_external_fixture_requires_explicit_label_and_loads_playground_shape(self):
        payload = playground_payload()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "playground.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                FixtureBankDataProvider.from_file(path)

            provider = FixtureBankDataProvider.from_file(
                path, source_label="Sectors Playground capture, 2026-09-29"
            )
            result = provider.get_bank_universe()
            discovery = provider.get_discovery_data()

        self.assertEqual(result.universe.frame.loc[0, "ticker"], "DEMO001")
        self.assertEqual(result.status.source, "Sectors Playground capture, 2026-09-29")
        self.assertFalse(result.status.is_live)
        self.assertEqual(result.status.mode, "fixture")
        self.assertTrue(all(e.source == result.status.source for e in discovery.evidence_ledger))
        self.assertTrue(all(e.data_mode == "fixture" for e in discovery.evidence_ledger))

    def test_external_fixture_rejects_credential_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unsafe.json"
            path.write_text(json.dumps({"Authorization": "redacted"}), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "credential-like content"):
                FixtureBankDataProvider.from_file(path, source_label="Sectors Playground capture")

    def test_external_fixture_rejects_private_key_fields(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "unsafe.json"
            path.write_text(
                json.dumps({"secrets": {"private_key": "redacted-placeholder"}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "credential-like content"):
                FixtureBankDataProvider.from_file(path, source_label="Local fixture")

    def test_fixture_company_data_keeps_source_status_and_non_live_warning(self):
        provider = create_bank_data_provider("demo")

        company = provider.get_company_data("DEMO001")

        self.assertIsInstance(company, CompanyData)
        self.assertEqual(company.ticker, "DEMO001")
        self.assertFalse(company.status.is_live)
        self.assertIn("DEMO/SAMPLE", company.status.source)

    def test_live_provider_uses_client_for_each_supported_data_method(self):
        client = FakeSectorsClient()
        provider = create_bank_data_provider("live", client=client)

        universe = provider.get_bank_universe()
        company = provider.get_company_data("BBRI")

        self.assertTrue(universe.status.is_live)
        self.assertEqual(universe.status.source, "Sectors Financial API")
        self.assertEqual(company.data["symbol"], "BBRI")
        self.assertEqual([call[0] for call in client.calls], ["screener", "report"])

    def test_discovery_workflow_accepts_provider_not_http_client(self):
        provider = create_bank_data_provider("demo")

        discovery = discover_banks(provider)

        self.assertIsInstance(discovery.status, DataSourceStatus)
        self.assertFalse(discovery.status.is_live)
        self.assertTrue(len(discovery.evidence_ledger))


if __name__ == "__main__":
    unittest.main()
