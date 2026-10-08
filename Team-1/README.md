# MarketLens Team 1 Backend

Starter backend for the MarketLens Team 1 ownership:

- Sectors API/MCP integration layer
- FastAPI
- server-side credentials
- caching
- normalization
- validation/error handling
- stable backend contract for Team 2 / Team 3

## Current verified Sectors v2 integration

All three endpoints below have their exact v2 path confirmed straight from Sectors' own
OpenAPI spec (see `SKILL.md` §4/§12) and are wired end-to-end:

- `GET /v2/company/report/{symbol}/` — selective sections, default request is
  `overview,financials,valuation` (not the full 8-section report) to save credits. The
  normalized model still keeps all 8 possible sections (`overview`, `valuation`,
  `future`, `peers`, `financials`, `dividend`, `management`, `ownership`) so that
  requesting a non-default combo via `/company-report?sections=...` never silently
  drops data you already paid a credit for.
- `GET /v2/daily/{symbol}/` — params `start`, `end` (Sectors defaults to a 30-day
  window, 90-day max; wider ranges silently clamp on their end).
- `GET /v2/foreign-flow/{symbol}/` — params `start`, `end` (90-day max). Normalized
  rows include `foreign_buy_idr`/`foreign_sell_idr` alongside `net_foreign_inflow`/
  `foreign_share`, since Sectors returns all four.

**Not yet wired** (out of MVP default scope for now, still true unknowns per
`SKILL.md` §12): `GET /v2/financials/quarterly/{symbol}/` (bank/insurance metrics
nest under `financials_sector_metrics` — don't flatten those if you add this later),
company-segments, helper-lists, ranking/screener endpoints.

## P0 valuation + quality — 2026-10-01

Default Company Report sections are `overview,financials,valuation`. The supplied
BBCA capture (retrieved 2026-10-01T14:45:07.645465+00:00) verified the P0 paths.
No extra Sectors requests were made while implementing this update.

The original `valuation`, `financials` and other raw fields stay available.
The additive `company.intelligence` contract has `schema_version: "1.0"`,
normalized `valuation` and `quality`, source metadata, and limitations.
The standalone Company Report endpoint returns the same new `intelligence`
object directly on its report response. See `../P0_CONTRACT.md`.

- Valuation: forward PE plus PE/PB/PEG and same-year PE/PB peer averages.
- Quality: annual ROE, ROA, net profit margin and operating profit margin.
- Histories are sorted by validated year. Latest means the latest reported year,
  including rows with null metrics; older values are never silently substituted.
- Profitability is stored as a decimal fraction. For example 0.204259 is 20.4259%.
- Conflicting duplicate-year rows yield unavailable metrics with a limitation.
- The capture's latest valuation year is 2026; latest quality year is 2025.
  The 2026 valuation row is not asserted to be a complete annual/TTM observation.
- Forward PE remains explicitly an estimate with an unspecified forecast horizon.
- Dividend/income, leverage, cash-flow signals and a new peer request are outside
  this P0 implementation.

The user's allocation was 1,000 total, approximately 200 already consumed when
work began. Account balance after their local requests has not been checked.
A successful uncached default **company report** costs 3 credits according to
the supplied docs. `/api/assets/{symbol}` also fetches daily and foreign-flow
endpoints; the company-report cost is not the total asset-request cost.

## Credit hygiene already built in

- `404` responses are billable per Sectors' docs, so they're cached as a negative
  result for the same endpoint-specific TTL as a success — repeat lookups of an invalid/delisted
  symbol don't keep re-spending credits. `400`/`401`/`403`/`429`/`5xx` are free and
  are never cached, since a retry could legitimately succeed.
- `SECTORS_API_KEY` is env-only and the client sends it as a raw `Authorization`
  header (no `Bearer` prefix), matching the confirmed auth scheme.

- Company-report cache TTL defaults to 3,600 seconds; override with
  `COMPANY_REPORT_CACHE_TTL_SECONDS`. Trading-series cache uses
  `CACHE_TTL_SECONDS` (default 300).
- Section order and duplicate section names share the same cache entry.
- Concurrent identical requests share one upstream fetch **within one process**.
- Report retrieval timestamps are preserved across cache hits; sources include
  the actual query parameters.
- Invalid IDX symbol formats and invalid/empty section lists are rejected locally.
- Cache is memory-only. Restarts/reload and separate workers have independent
  caches. Use one worker for the hackathon; this is not a hard spending limit.

Do not commit `.env`.

## Run

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
uvicorn app.main:app --reload
```

Health:

`GET http://127.0.0.1:8000/health`

Company Report:

`GET http://127.0.0.1:8000/api/assets/BBCA/company-report`

or select sections:

`GET /api/assets/BBCA/company-report?sections=overview,financials,valuation`

Combined asset contract:

`GET /api/assets/BBCA`

## Tests

Unit tests do not require an API key or an internet connection.

```bash
pytest -q
```

For live Sectors integration, create `.env` from `env.example` and set:

```env
SECTORS_API_KEY=your_hackathon_key
```

The application can be imported and unit-tested without this secret; live API calls
will return a clear configuration error until the key is set.

## Team 2 handoff

The normalized backend contract is intended to give Team 2 stable data without making Team 2 call Sectors directly.

They should consume:

```text
symbol
company
market
foreign_flow
limitations
source_endpoints
```

and build the Multi-Signal Intelligence Engine separately.

## API credit hygiene

- Prefer selective Company Report sections.
- Cache repeated requests.
- Validate symbols before calling billable endpoints.
- Use fixtures for development when possible.
- Keep real Sectors calls for integration/demo validation.

## Offline replay / verification

The previous 503 issue was resolved in the user's environment before the BBCA
capture. Settings now also load `.env` from the Team-1 project root, independent
of the terminal working directory, and accept UTF-8 files with a BOM.

From the parent folder containing both Team-1 and Team-2:

```powershell
.\Team-1\.venv\Scripts\python.exe .\verify_p0.py
```

This replays the included capture through normalization, intelligence, grounding
and the deterministic fallback, with no API calls or keys required. Its result
is explicitly report-only: daily and foreign-flow data were not supplied.

For a new capture when needed, `python scripts/capture_company_report.py BBCA`
still requests only Company Report, with no daily/foreign-flow fetch or retries.
Use saved captures for development and reserve provider calls for integration.

30 Team 1 tests passed locally. The older API audit file refers to the initial
MVP multi-ticker checks, not multi-ticker validation of this P0 contract.
