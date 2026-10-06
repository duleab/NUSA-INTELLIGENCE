import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from nusa.providers.sectors import FixtureBankDataProvider, SectorsBankDataProvider, create_bank_data_provider
from nusa.providers.sectors_snapshot import (
    DEFAULT_SECTORS_SNAPSHOT_PATH,
    CachedSectorsBankDataProvider,
    import_sectors_response,
    import_sectors_response_file,
    load_sectors_snapshot,
    normalize_sectors_response,
    save_sectors_snapshot,
)


QUERY = {
    "where": "sub_sector = 'Banks' and market_cap IS NOT NULL",
    "order_by": "-market_cap",
    "limit": 50,
    "include_query_values": True,
}
RETRIEVED_AT = "2026-10-06T06:57:18+00:00"
RESPONSE = {
    "results": [
        {
            "symbol": "TST1.JK",
            "company_name": "Test Financial Group One",
            "query_values": {
                "sub_sector": "Banks",
                "market_cap": 123.0,
                "earnings[2024]": 10.0,
                "earnings[2025]": 12.0,
                "roa[2024]": None,
            },
        },
        {
            "symbol": "TST2.JK",
            "company_name": "Test Financial Group Two",
            "query_values": {"sub_sector": "Banks", "market_cap": 100.0},
        },
    ],
    "pagination": {"total_count": 2, "showing": 2, "limit": 50, "offset": 0},
    "llm_translation": {
        "natural_query": "",
        "translated_params": QUERY,
        "message": None,
    },
}


class SectorsSnapshotTests(unittest.TestCase):
    def test_imports_screener_response_with_explicit_sectors_provenance(self):
        snapshot = import_sectors_response(
            RESPONSE,
            query=QUERY,
            retrieved_at=RETRIEVED_AT,
            confirmed_sectors_origin=True,
            snapshot_created_at=RETRIEVED_AT,
        )

        self.assertEqual(snapshot["source"], "Sectors")
        self.assertEqual(snapshot["endpoint"], "/v2/companies/")
        self.assertEqual(snapshot["retrieved_at"], RETRIEVED_AT)
        self.assertEqual(snapshot["snapshot_created_at"], RETRIEVED_AT)
        self.assertTrue(snapshot["is_live_snapshot"])
        self.assertTrue(snapshot["is_cached"])
        self.assertEqual(snapshot["query"], QUERY)
        self.assertEqual(snapshot["response"], RESPONSE)

    def test_rejects_malformed_screener_response(self):
        malformed = {"results": [{"symbol": "TST1.JK"}]}
        with self.assertRaises(ValueError):
            import_sectors_response(
                malformed,
                query=QUERY,
                retrieved_at=RETRIEVED_AT,
                confirmed_sectors_origin=True,
            )

    def test_normalizes_only_present_annual_metrics_and_keeps_missing_values_missing(self):
        universe = normalize_sectors_response(RESPONSE)

        self.assertEqual(universe.frame.loc[0, "ticker"], "TST1.JK")
        self.assertEqual(universe.frame.loc[0, "company_name"], "Test Financial Group One")
        self.assertEqual(universe.frame.loc[0, "earnings[2024]"], 10.0)
        self.assertEqual(universe.frame.loc[0, "earnings[2025]"], 12.0)
        self.assertTrue(pd.isna(universe.frame.loc[0, "roa[2024]"]))
        self.assertTrue(pd.isna(universe.frame.loc[1, "earnings[2024]"]))
        self.assertNotIn("roa[2025]", universe.frame.columns)
        self.assertNotIn("net_interest_income[2024]", universe.frame.columns)

    def test_rejects_non_numeric_documented_annual_metric(self):
        bad = json.loads(json.dumps(RESPONSE))
        bad["results"][0]["query_values"]["earnings[2024]"] = "not numeric"

        with self.assertRaises(ValueError):
            normalize_sectors_response(bad)

    def test_rejects_demobank_fixture_mislabeled_as_sectors(self):
        fixture = json.loads(
            (Path(__file__).resolve().parents[1] / "data/fixtures/banks_demo.json").read_text(
                encoding="utf-8"
            )
        )
        with self.assertRaisesRegex(ValueError, "Synthetic"):
            import_sectors_response(
                fixture,
                query=QUERY,
                retrieved_at=RETRIEVED_AT,
                confirmed_sectors_origin=True,
            )

    def test_rejects_explicit_synthetic_metadata_even_with_non_demo_tickers(self):
        response = json.loads(json.dumps(RESPONSE))
        response["data_mode"] = "synthetic"

        with self.assertRaisesRegex(ValueError, "Synthetic"):
            import_sectors_response(
                response,
                query=QUERY,
                retrieved_at=RETRIEVED_AT,
                confirmed_sectors_origin=True,
            )

    def test_rejects_secret_material_in_snapshot(self):
        bad_query = {**QUERY, "Authorization": "do-not-persist"}
        with self.assertRaisesRegex(ValueError, "credential"):
            import_sectors_response(
                RESPONSE,
                query=bad_query,
                retrieved_at=RETRIEVED_AT,
                confirmed_sectors_origin=True,
            )

    def test_snapshot_round_trip_preserves_provenance_without_credentials(self):
        snapshot = import_sectors_response(
            RESPONSE, query=QUERY, retrieved_at=RETRIEVED_AT, confirmed_sectors_origin=True
        )
        with tempfile.TemporaryDirectory() as cache_dir:
            path = Path(cache_dir) / "snapshot.json"
            save_sectors_snapshot(snapshot, path)
            serialized = path.read_text(encoding="utf-8")
            cached = CachedSectorsBankDataProvider(path)

        self.assertNotIn("Authorization", serialized)
        self.assertNotIn("api_key", serialized)
        self.assertEqual(cached.status.source, "SECTORS CACHED SNAPSHOT")
        self.assertEqual(cached.status.mode, "cached_sectors")
        self.assertFalse(cached.status.is_live)
        self.assertEqual(cached.status.retrieved_at, RETRIEVED_AT)

    def test_imports_saved_response_into_cache_without_api_access(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw_path = root / "successful-response.json"
            raw_path.write_text(json.dumps(RESPONSE), encoding="utf-8")
            destination = root / "cache" / "snapshot.json"
            written = import_sectors_response_file(
                raw_path,
                query=QUERY,
                retrieved_at=RETRIEVED_AT,
                confirmed_sectors_origin=True,
                destination=destination,
            )
            loaded = load_sectors_snapshot(written)

        self.assertEqual(written, destination)
        self.assertTrue(loaded["is_cached"])
        self.assertEqual(loaded["source"], "Sectors")
        self.assertEqual(loaded["response"]["results"][0]["symbol"], "TST1.JK")

    def test_cached_provider_supplies_universe_and_company_data(self):
        snapshot = import_sectors_response(
            RESPONSE, query=QUERY, retrieved_at=RETRIEVED_AT, confirmed_sectors_origin=True
        )
        with tempfile.TemporaryDirectory() as cache_dir:
            path = save_sectors_snapshot(snapshot, Path(cache_dir) / "snapshot.json")
            provider = CachedSectorsBankDataProvider(path)
            universe = provider.get_bank_universe()
            company = provider.get_company_data("TST1.JK")

        self.assertEqual(len(universe.universe.frame), 2)
        self.assertEqual(company.ticker, "TST1.JK")
        self.assertEqual(company.data["earnings[2025]"], 12.0)
        self.assertEqual(company.status.retrieved_at, RETRIEVED_AT)

    def test_company_data_preserves_missing_metric_as_missing(self):
        snapshot = import_sectors_response(
            RESPONSE, query=QUERY, retrieved_at=RETRIEVED_AT, confirmed_sectors_origin=True
        )
        with tempfile.TemporaryDirectory() as cache_dir:
            path = save_sectors_snapshot(snapshot, Path(cache_dir) / "snapshot.json")
            company = CachedSectorsBankDataProvider(path).get_company_data("TST2.JK")

        self.assertIsNone(company.data["earnings[2025]"])

    def test_cached_provider_never_refreshes_or_silently_falls_back(self):
        snapshot = import_sectors_response(
            RESPONSE, query=QUERY, retrieved_at=RETRIEVED_AT, confirmed_sectors_origin=True
        )
        with tempfile.TemporaryDirectory() as cache_dir:
            path = save_sectors_snapshot(snapshot, Path(cache_dir) / "snapshot.json")
            provider = CachedSectorsBankDataProvider(path)
            with self.assertRaisesRegex(RuntimeError, "import a new snapshot"):
                provider.get_bank_universe(force_refresh=True)

    def test_discovery_evidence_keeps_cached_sectors_provenance(self):
        response = json.loads(json.dumps(RESPONSE))
        base = response["results"][0]
        response["results"] = []
        periods = ((10, 12), (20, 22), (30, 33), (40, 44), (50, 80))
        for index, (prior, current) in enumerate(periods, start=1):
            row = json.loads(json.dumps(base))
            row["symbol"] = f"TST{index}.JK"
            row["company_name"] = f"Test Financial Group {index}"
            row["query_values"]["earnings[2024]"] = prior
            row["query_values"]["earnings[2025]"] = current
            response["results"].append(row)
        response["pagination"]["total_count"] = 5
        response["pagination"]["showing"] = 5

        snapshot = import_sectors_response(
            response, query=QUERY, retrieved_at=RETRIEVED_AT, confirmed_sectors_origin=True
        )
        with tempfile.TemporaryDirectory() as cache_dir:
            path = save_sectors_snapshot(snapshot, Path(cache_dir) / "snapshot.json")
            discovery = CachedSectorsBankDataProvider(path).get_discovery_data()

        self.assertEqual(discovery.status.mode, "cached_sectors")
        self.assertFalse(discovery.status.is_live)
        self.assertTrue(len(discovery.evidence_ledger))
        for evidence in discovery.evidence_ledger:
            self.assertEqual(evidence.data_mode, "cached")
            self.assertEqual(evidence.source_endpoint, "/v2/companies/")

    def test_factory_requires_explicit_snapshot_path_for_cached_mode(self):
        with self.assertRaisesRegex(ValueError, "snapshot_path"):
            create_bank_data_provider("cached_sectors")

    def test_factory_uses_only_the_explicit_cached_snapshot(self):
        snapshot = import_sectors_response(
            RESPONSE, query=QUERY, retrieved_at=RETRIEVED_AT, confirmed_sectors_origin=True
        )
        with tempfile.TemporaryDirectory() as cache_dir:
            path = save_sectors_snapshot(snapshot, Path(cache_dir) / "snapshot.json")
            provider = create_bank_data_provider("cached_sectors", snapshot_path=path)

        self.assertIsInstance(provider, CachedSectorsBankDataProvider)
        self.assertEqual(provider.status.mode, "cached_sectors")

    def test_live_cached_and_demo_sources_remain_distinct(self):
        live = SectorsBankDataProvider(client=object())
        demo = FixtureBankDataProvider(
            json.loads(
                (Path(__file__).resolve().parents[1] / "data/fixtures/banks_demo.json").read_text(
                    encoding="utf-8"
                )
            ),
            source_label="DEMO_SAMPLE test fixture",
            data_mode="synthetic",
        )
        self.assertTrue(live.status.is_live)
        self.assertFalse(demo.status.is_live)
        self.assertNotEqual(live.status.source, demo.status.source)
        self.assertEqual(DEFAULT_SECTORS_SNAPSHOT_PATH.name, "banks_companies_screener.json")


if __name__ == "__main__":
    unittest.main()
