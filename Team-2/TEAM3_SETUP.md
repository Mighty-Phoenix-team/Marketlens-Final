# MarketLens MVP - Team 3 Setup Guide

## Services

| Service | Port |
|---|---:|
| Team 1 API | 8000 |
| Team 2 API | 8001 |
| Streamlit | 8501 |

## Running Order

### 1. Start Team 1

```powershell
uvicorn app.main:app --reload
```

Team 1 provides market asset data.

---

### 2. Start Team 2

Create `.env`:

```env
MARKETLENS_ASSET_API_BASE_URL=http://127.0.0.1:8000
MARKETLENS_API_BASE_URL=http://127.0.0.1:8001
MARKETLENS_DISCOVERY_UNIVERSE=BBCA

GEMINI_API_KEY=<YOUR_KEY>
GEMINI_MODEL=gemini-flash-latest
```

Run:

```powershell
python -m uvicorn marketlens.api:app --host 127.0.0.1 --port 8001
```

Swagger:
```
http://127.0.0.1:8001/docs
```

---

### 3. Start Streamlit

```powershell
python -m streamlit run dashboard/app.py
```

Open:

```
http://localhost:8501
```

## Demo Flow

1. Create research profile
2. Apply profile
3. Open Discovery
4. Select asset
5. Open Finding Detail
6. Click Explain Finding

Expected:
- Evidence appears
- Research relevance appears
- Explanation appears; deterministic fallback is used if Gemini is unavailable

## Troubleshooting

### API unavailable

Check:
```
http://127.0.0.1:8001/docs
```

### Discovery empty

Check:
```
MARKETLENS_DISCOVERY_UNIVERSE
```

### Explanation error

Check:
- GEMINI_API_KEY
- GEMINI_MODEL

## Existing Features (including P0 valuation and quality evidence)

- Intelligence engine
- Evidence grounding
- Research relevance
- Discovery dashboard
- Finding detail
- AI explanation layer

## P0 update

Upgrade both Team 1 and Team 2 source files, retain local .env and SQLite data,
and restart both APIs. The sidebar now includes valuation and profitability.
Evidence uses percentages, multiples and percentage points, with source years.
See ../P0_UPDATE.md and ../P0_CONTRACT.md. An offline report-only replay is
available via ../verify_p0.py; it makes no Sectors or Gemini requests.
