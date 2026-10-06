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
control, then import it into the ignored cache. A user with authorized API
credentials can retrieve the documented bounded discovery request through the
existing client and write the response body locally as follows. `SECTORS_API_KEY`
must be present in the process environment or ignored `.env`; the code never
prints or stores request headers.

```python
from datetime import datetime, timezone
import json
from pathlib import Path

from nusa.sectors.client import SectorsClient
from nusa.providers.sectors_snapshot import import_sectors_response_file

client = SectorsClient()
years = client.discovery_years
fields = [
    f"{metric}[{year}]"
    for metric in client.discovery_metrics
    for year in years
]
where = f"{client.bank_filter} and (" + " or ".join(
    f"{field} IS NOT NULL" for field in fields
) + ")"
query = {
    "where": where,
    "order_by": "-market_cap",
    "limit": 50,
    "include_query_values": True,
}

# force_refresh bypasses this client's local response cache for the retrieval.
response = client.companies_screener(limit=50, force_refresh=True)
retrieved_at = datetime.now(timezone.utc).isoformat()
response_path = Path("data/cache/sectors/companies-response.json")
response_path.parent.mkdir(parents=True, exist_ok=True)
response_path.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")

snapshot_path = import_sectors_response_file(
    response_path,
    query=query,
    retrieved_at=retrieved_at,
    confirmed_sectors_origin=True,
)
print(f"Validated local snapshot saved at {snapshot_path}")
```

Both `companies-response.json` and the generated snapshot are under ignored
`data/cache/`; do not stage them. The timestamp is recorded immediately after a
successful retrieval, and the importer creates `snapshot_created_at` itself.
The importer validates the result structure and fails closed on missing
metadata, suspicious synthetic tickers, or credential-like fields. The cached
provider never calls Sectors; `force_refresh=True` raises an error and requires
an explicit import of a new response. Delete or securely retain the raw response
according to local data-handling policy; neither file belongs in public Git.

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
