import json
import os
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from nusa.sectors.client import SectorsAPIError, SectorsClient, _requests_transport


class SectorsClientTests(unittest.TestCase):
    def test_default_client_uses_the_standard_requests_transport(self):
        with tempfile.TemporaryDirectory() as cache_dir, patch.dict(
            os.environ, {"SECTORS_API_KEY": "test-secret"}
        ), patch(
            "nusa.sectors.client._requests_transport", return_value=(200, {"ok": True})
        ) as requests_transport, patch(
            "nusa.sectors.client._urllib_transport",
            side_effect=AssertionError("default client must not use urllib"),
        ):
            client = SectorsClient(cache_dir=cache_dir, retries=0)

            self.assertEqual(client.subsectors(force_refresh=True), {"ok": True})

        requests_transport.assert_called_once()

    def test_requests_transport_uses_plain_nusa_headers_and_no_environment_proxy(self):
        observed = {}
        response = unittest.mock.Mock()
        response.status_code = 200
        response.json.return_value = {"ok": True}
        session = unittest.mock.Mock()
        session.get.return_value = response

        def make_session():
            observed["session"] = session
            return session

        with patch("nusa.sectors.client.requests.Session", side_effect=make_session):
            result = _requests_transport(
                "https://api.sectors.app/v2/companies/?limit=3",
                {
                    "Authorization": "mock-secret",
                    "Accept": "application/json",
                    "User-Agent": "NUSA-Intelligence-Hackathon/1.0",
                },
                20,
            )

        self.assertEqual(result, (200, {"ok": True}))
        self.assertFalse(session.trust_env)
        session.get.assert_called_once_with(
            "https://api.sectors.app/v2/companies/?limit=3",
            headers={
                "Authorization": "mock-secret",
                "Accept": "application/json",
                "User-Agent": "NUSA-Intelligence-Hackathon/1.0",
            },
            timeout=20,
        )
        session.close.assert_called_once()

    def test_requests_transport_exposes_only_sanitized_403_diagnostics(self):
        response = unittest.mock.Mock()
        response.status_code = 403
        response.headers = {
            "server": "cloudflare",
            "cf-ray": "test-ray-id",
            "set-cookie": "private-cookie",
            "authorization": "never expose",
            "content-type": "application/json",
        }
        response.json.return_value = {
            "error_code": 1010,
            "error_name": "browser_signature_banned",
            "message": "Request rejected",
            "api_key": "private-key-value",
        }
        session = unittest.mock.Mock()
        session.get.return_value = response
        with patch("nusa.sectors.client.requests.Session", return_value=session):
            with self.assertRaises(SectorsAPIError) as raised:
                _requests_transport(
                    "https://api.sectors.app/v2/companies/?limit=3",
                    {"Authorization": "mock-secret", "Accept": "application/json"},
                    20,
                )

        error = raised.exception
        self.assertEqual(error.status, 403)
        self.assertEqual(error.body["error_code"], 1010)
        self.assertEqual(error.body["error_name"], "browser_signature_banned")
        self.assertNotIn("api_key", error.body)
        self.assertEqual(error.headers["server"], "cloudflare")
        self.assertEqual(error.headers["cf-ray"], "test-ray-id")
        self.assertNotIn("set-cookie", error.headers)
        self.assertNotIn("authorization", error.headers)

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
            self.assertEqual(
                observed[0][1]["User-Agent"], "NUSA-Intelligence-Hackathon/1.0"
            )
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
