# Integrated Comparison + P1

Start with [UPDATE_COMPARISON.md](UPDATE_COMPARISON.md) for installation and offline verification.

The previous setup notes below are retained for reference.

# MarketLens — Team 2

## P0 valuation + quality — 2026-10-01

Team 2 now consumes the versioned `company.intelligence` contract from Team 1.
The existing `fundamental`, `market_activity` and `investor_flow` group names
stay intact. New groups are `valuation` and `quality`. Research focuses accept
`valuation`, `profitability` and the `quality` alias, alongside existing focuses.
The dashboard exposes valuation/profitability and displays percentage, multiple
and percentage-point units explicitly.

Valuation/quality fields never come from raw Sectors dictionaries in this engine.
Legacy Team 1 responses still produce existing evidence, with limitations for
unavailable P0 fields. Both services should be upgraded together.

Finding/evidence fields are preserved; units, provenance details, contextual
baselines and `methodology_version: "2.0-p0"` are additive. The methodology now
expects five groups for every asset, so scores should not be compared directly
with the earlier three-group methodology.

Explain Finding keeps `finding` and `explanation`, with `ai_explanation` and the
`/explain` route as compatibility aliases. `explanation_source` distinguishes
Gemini from `deterministic_fallback`. Gemini sees the same complete evidence,
periods, units, limitations and profile weights; it never calculates the score.
The fallback uses those same facts and keeps the score intact.

## Run locally

Start Team 1 on port 8000 first. Team 2 calls Team 1; do not copy a Sectors key
into Team 2. In a new folder, create a virtual environment and install packages:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item env.example .env
python -m uvicorn marketlens.api:app --host 127.0.0.1 --port 8001
```

If you already have `.env`, retain it and review the settings instead of
replacing it. `MARKETLENS_ASSET_API_BASE_URL` is the Team 1 origin without
`/api/assets`. `MARKETLENS_API_BASE_URL` is the Team 2 origin for the dashboard.
The example starts Discovery with BBCA only to reduce validation spending.

The cache setting for Team 2 is **MARKETLENS_CACHE_TTL_SECONDS**, not
`CACHE_TTL_SECONDS`. Default TTL is 300 seconds, in-process. SQLite profiles use
`MARKETLENS_DB_PATH`, default `marketlens.sqlite3`. Retain the old SQLite file if
you want to retain existing profiles and saved assets.

Gemini is optional. Put `GEMINI_API_KEY` and an available `GEMINI_MODEL` in the
backend `.env`. Missing/invalid credentials or provider errors result in the
deterministic fallback. No live Gemini request was made during this repair.

Run Streamlit in another terminal from this folder:

```powershell
python -m streamlit run dashboard/app.py
```

Swagger: `http://127.0.0.1:8001/docs`. Dashboard: `http://localhost:8501`.

## API flow

1. `POST /api/profiles` with sectors, research focus and horizon.
2. `GET /api/profiles/{id}/discovery` for ranked findings.
3. `PUT /api/profiles/{id}/assets/BBCA` to save an asset.
4. `GET /api/profiles/{id}/assets` for saved-asset findings.
5. `GET /api/profiles/{id}/assets/BBCA/finding` for one finding.
6. `GET /api/profiles/{id}/assets/BBCA/explanation-context` for grounded facts;
   this endpoint does not call an LLM.
7. `POST /api/profiles/{id}/assets/BBCA/explanation` for the explanation.

## Method and contract

See `../P0_CONTRACT.md` for field paths, units, periods and complete scoring rules.
The existing three groups retain their original magnitude/threshold rules.
P0 raw levels receive fixed context-availability strength 0.25, regardless of
whether the number is high, low or negative. Comparable derived gaps receive
`min(abs(gap)/threshold, 1)`:

- PE/PB vs median of positive prior-year observations (minimum two), or positive
  same-year provider peer average: threshold 0.50 (50% descriptive difference).
- ROE year-to-year difference: threshold 0.02 (2 percentage points).
- ROA difference: threshold 0.005 (0.5 percentage points).
- Net/operating margin difference: threshold 0.05 (5 percentage points).

A group's strength remains its maximum evidence strength. Focus weights are 1
for selected groups and 0.4 for others; no selection means all 1. Sector factor
is 1 for a match/no filter, otherwise 0.5.

`Research Relevance = 10 * weighted_group_strength * (available_groups / 5) * sector_factor`.

All thresholds are explicit MVP design choices, not empirically calibrated
investment signals. Magnitudes are direction-neutral. The group named quality
contains profitability evidence; it does not grade investment quality.

Negative/zero multiples remain visible as provider facts but are excluded from
ratio-gap calculations. Profitability changes use the immediately preceding
financial year and are displayed in percentage points, not relative percent.
PEG and forward PE are context only. No forecast horizon, intrinsic-value
assessment, buy/sell/hold recommendation, or winning asset is inferred.

Dividend/income is still P1. The separately developed Comparison branch is not
included or integration-tested here; its existing Finding/evidence fields are
retained. Comparison should honor the additive units and periods when rendering
new metrics and avoid comparing scores from different methodology versions.

The normalized BBCA fixture is a replay of a user-supplied capture, not current
live data. It intentionally contains no daily/foreign-flow data. Annual company
periods are independent of the market-data horizon selected by the user.

## Verification

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

All 23 Team 2 tests passed locally using captured fixtures and mocked upstream/LLM calls.
A separate in-process test joins both FastAPI services and verifies Discovery,
My Assets, explanation grounding, fallback and shared upstream caching.
All Python modules were syntax-checked. The Streamlit UI was not exercised in a
browser, and a complete live Sectors-to-Gemini demo remains unverified. A mocked Gemini
request verifies the enriched context and unchanged deterministic score.
