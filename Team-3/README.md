# MarketLens frontend — Team 3

Next.js research workspace connected to the Team 2 Intelligence API.

## Features

- Discovery cards and finding details can save an asset to My Assets. Saved state is confirmed by the API, with duplicate saves disabled and errors shown inline.
- My Assets supports manual ticker entry, removal, and persistence through the research profile. Saved assets with unavailable evidence remain visible and removable.
- Comparison displays 2–4 assets side by side, including Research Relevance, measured evidence, periods, source links, and limitations. Missing data is labeled explicitly; a failed asset request prevents an incomplete comparison.
- Responsive navigation, shared evidence cards, loading/empty/error states, and light/dark themes.

## Interactive controls

- Profile sections can be reached from the sticky step navigation or summary edit links. Selected sectors can be removed directly from the summary. Draft status reflects unsaved differences; reset returns to the loaded profile or initial defaults.
- Discovery searches the currently loaded findings by ticker, company, or sector; it can show saved assets only and sort by relevance or ticker. Filtering does not query the entire market or request additional upstream data.

## Local setup

Start Team 1 on port 8000 and Team 2 on port 8001 using their repositories' instructions. Then run this frontend:

```powershell
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Open http://localhost:3000 and create a research profile. The only browser storage used for profile identity is `marketlens.activeProfileId`; asset lists live in Team 2's profile database.

`NEXT_PUBLIC_API_BASE_URL` must be the Team 2 origin reachable by the user's browser, without `/api`. It defaults to `http://127.0.0.1:8001`. Set it before building for another environment, and allow the frontend origin in Team 2's CORS configuration. No Sectors or Gemini key belongs in this frontend.

## Comparison contract

Comparison uses `POST /api/profiles/{id}/comparison` with `{ "symbols": [...] }` from Team 2 v0.4.0. It renders backend values, per-symbol evidence, period/unit status and limitations. If any selected asset fails, the request shows an error instead of silently comparing a subset. No additional per-symbol requests or client-calculated rankings are needed.

Each metric retains its own period, method and source. Different periods are not assumed comparable. Explicit units are preserved; known legacy ratio metrics without units are formatted as percentages.

## Request reuse

Successful GET responses and read-only comparison requests are cached in memory for 60 seconds per browser tab (maximum 100 entries). Identical in-flight requests share one promise. Cache keys include the profile and exact request/selection. Successful mutations invalidate that profile's cached responses, including pending cache writes. Errors are not cached. Discovery/My Assets refresh buttons bypass the browser cache; backend caches still apply. There is no background polling or persistent browser data cache.

This reduces browser-to-Team-2 requests; upstream credit savings depend on Team 1/2 caching and are not guaranteed by the frontend alone.

## Validation

```powershell
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Playwright starts the production build on port 3000 and intercepts Team 2 API calls with **simulated test responses**. It checks saved assets across navigation/reload, manual ticker entry, duplicates, failed saves, unavailable assets, comparison data/periods, failed comparisons, mobile navigation, request reuse, refresh, and expiry. Separate cache tests cover simultaneous reads, error retries, and invalidation races. These tests do not establish live Sectors or Gemini integration. Run the complete three-service workflow with valid backend credentials before recording the demo.

Changes are developed on `rey/assets-comparison-ui` for review before merging into `main`.

## Visual direction

The interface uses cream surfaces, an olive charcoal navigation rail, and restrained lime accents for actions and selections. Profile sits directly beneath the MarketLens wordmark on desktop; Discovery, My Assets, and Comparison form the research navigation group. Findings use compact rows with evidence periods and sources. Both themes and responsive layouts preserve the research workflow. Motion respects the system reduced-motion setting, and Research Relevance retains neutral score styling.
