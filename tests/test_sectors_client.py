import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from nusa.sectors.client import SectorsAPIError, SectorsClient


class SectorsClientTests(unittest.TestCase):
    def test_company_report_uses_existing_authenticated_transport(self):
        observed = []
        payload = {"symbol": "BBRI", "financials": {}}

        def transport(url, headers, timeout):
            observed.append((url, headers, timeout))
            return 200, payload

        with tempfile.TemporaryDirectory() as cache_dir, patch.dict(
            os.environ, {"SECTORS_API_KEY": "test-secret"}
        ):
            client = SectorsClient(cache_dir=cache_dir, transport=transport)

            result = client.company_report("BBRI")

        self.assertEqual(result, payload)
        self.assertIn("/v2/company/report/BBRI/", observed[0][0])
        self.assertEqual(observed[0][1]["Authorization"], "test-secret")

    def test_sends_key_from_environment_and_caches_successful_response(self):
        payload = {"results": [{"symbol": "BBRI"}]}
        observed = []

        def transport(url, headers, timeout):
            observed.append((url, headers, timeout))
            return 200, payload

        with (
            tempfile.TemporaryDirectory() as cache_dir,
            patch.dict(os.environ, {"SECTORS_API_KEY": "test-secret"}),
        ):
            client = SectorsClient(cache_dir=cache_dir, transport=transport)
            first = client.companies_screener()
            second = client.companies_screener()

            self.assertEqual(first, payload)
            self.assertEqual(second, payload)
            self.assertEqual(len(observed), 1)
            self.assertEqual(observed[0][1]["Authorization"], "test-secret")
            self.assertNotIn("test-secret", json.dumps(list(os.walk(cache_dir))))

    def test_requires_environment_key_without_echoing_it(self):
        with patch.dict(os.environ, {}, clear=True):
            client = SectorsClient(
                cache_dir=tempfile.mkdtemp(),
                transport=lambda *_: self.fail("network called"),
            )
            with self.assertRaisesRegex(RuntimeError, "SECTORS_API_KEY"):
                client.subsectors()

    def test_rejects_unsafe_screener_parameters_before_request(self):
        with patch.dict(os.environ, {"SECTORS_API_KEY": "test-secret"}):
            client = SectorsClient(
                cache_dir=tempfile.mkdtemp(),
                transport=lambda *_: self.fail("network called"),
            )
            with self.assertRaises(ValueError):
                client.companies_screener(limit=201)

    def test_banks_request_matches_playground_and_requests_documented_annual_fields(self):
        observed = []

        def transport(url, headers, timeout):
            observed.append((url, headers))
            return 200, {"results": [], "pagination": {}}

        with patch.dict(os.environ, {"SECTORS_API_KEY": "test-secret"}):
            client = SectorsClient(cache_dir=tempfile.mkdtemp(), transport=transport)
            client.companies_screener(limit=50, offset=None)

        url, headers = observed[0]
        params = parse_qs(urlsplit(url).query)
        where = params["where"][0]
        self.assertTrue(where.startswith("sub_sector = 'Banks' and market_cap IS NOT NULL and ("))
        self.assertIn("revenue[2025] IS NOT NULL", where)
        self.assertIn("revenue[2024] IS NOT NULL", where)
        self.assertIn("net_interest_income[2025] IS NOT NULL", where)
        self.assertIn("roe[2024] IS NOT NULL", where)
        self.assertEqual(params["order_by"], ["-market_cap"])
        self.assertEqual(params["limit"], ["50"])
        self.assertEqual(params["include_query_values"], ["true"])
        self.assertNotIn("offset", params)
        self.assertEqual(headers["Authorization"], "test-secret")

    def test_does_not_retry_billable_not_found_response(self):
        calls = []

        def transport(*_):
            calls.append(1)
            raise SectorsAPIError(404, "/v2/companies/")

        with patch.dict(os.environ, {"SECTORS_API_KEY": "test-secret"}):
            client = SectorsClient(cache_dir=tempfile.mkdtemp(), transport=transport, retries=3)
            with self.assertRaises(SectorsAPIError):
                client.companies_screener()

        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
