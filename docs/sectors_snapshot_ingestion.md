# Sectors Companies Screener snapshot ingestion

The snapshot importer lets an authorized, successful Sectors Companies Screener
response be brought into NUSA without making an API call. The default destination
is `data/cache/sectors/banks_companies_screener.json`; the existing `.gitignore`
excludes `data/cache/` so local financial snapshots are not committed by default.

## Snapshot envelope

```json
{
  "source": "Sectors",
  "endpoint": "/v2/companies/",
  "retrieved_at": "2026-10-06T06:57:18+00:00",
  "snapshot_created_at": "2026-10-06T07:10:00+00:00",
  "query": {
    "where": "sub_sector = 'Banks' and market_cap IS NOT NULL",
    "order_by": "-market_cap",
    "limit": 50,
    "include_query_values": true
  },
  "is_live_snapshot": true,
  "is_cached": true,
  "response": {
    "results": [],
    "pagination": {"total_count": 0}
  }
}
```

`is_live_snapshot` records that the response was explicitly attested as originating
from a successful Sectors retrieval. `is_cached` indicates it is now being read
from disk. It does **not** mean the data is current. The cached provider reports
`mode="cached_sectors"`, `is_live=false`, source `SECTORS CACHED SNAPSHOT`, and the
original `retrieved_at` timestamp. The live API provider and synthetic DEMO/SAMPLE
provider remain separate modes; importing or reading a snapshot never falls back
between them.

The importer requires an explicit `confirmed_sectors_origin=True` attestation,
validates the response and provenance envelope, rejects recognizable DEMOBANK /
SAMPLE / FIXTURE tickers, and rejects credential/account-related fields. This is
input validation—not cryptographic proof of origin—so only import a response saved
from the authorized Sectors source. Do not include request headers, API keys,
cookies, account identifiers, or other credentials in the raw response file.

## Import and read

Save only the JSON response body (not headers) to a local file outside version
control, then run:

```python
from nusa.providers.sectors_snapshot import import_sectors_response_file
from nusa.providers.sectors import create_bank_data_provider

snapshot_path = import_sectors_response_file(
    r"C:\secure-local-path\companies-response.json",
    query={
        "where": "sub_sector = 'Banks' and market_cap IS NOT NULL",
        "order_by": "-market_cap",
        "limit": 50,
        "include_query_values": True,
    },
    retrieved_at="<original timezone-aware retrieval timestamp>",
    confirmed_sectors_origin=True,
)
provider = create_bank_data_provider("cached_sectors", snapshot_path=snapshot_path)
```

The timestamp must be the response's original retrieval time, not the import time.
The importer creates `snapshot_created_at` itself. An invalid file, missing
metadata, suspicious synthetic ticker, or credential-like field fails closed.
The cached provider never calls Sectors; `force_refresh=True` raises an error and
requires an explicit import of a new response.

## Annual-field normalization

Only returned, recognized values are flattened from each result's
`query_values`. Annual bracket keys for 2024 and 2025 are supported for:

- `earnings`
- `net_interest_income`
- `total_assets`
- `total_equity`
- `roa`, `roe`, and `net_interest_margin`
- `gross_loan`, `net_loan`, and `total_deposit`
- `efficiency_ratio`, `cost_to_income_ratio`, and documented bank ratios

Absent fields are not created. JSON `null` and per-company omissions remain missing
(represented as null/NA in normalized data); no imputation or synthetic values are
added. Non-numeric, non-finite values for supported numeric fields are rejected.
Actual field coverage, units/scales, and comparability must be assessed from the
authorized response before using the existing Discovery analysis.

## Provenance and mode mapping

| Use | Provider/status mode | `is_live` | Source label |
| --- | --- | ---: | --- |
| Request Sectors directly | `live` | `true` | Sectors Financial API |
| Read imported Sectors snapshot | `cached_sectors` | `false` | SECTORS CACHED SNAPSHOT |
| Use bundled fictional fixture | `demo` | `false` | DEMO/SAMPLE synthetic fixture |

No response body, query metadata, or cached file should contain authorization
headers, cookies, API keys, or account identifiers.
