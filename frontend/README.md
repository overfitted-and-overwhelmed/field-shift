# frontend

React + Vite UI of Field Shift: one long page that is rebuilt from the explorer API on every change.

1. **Your situation**: crops the picks may use, weights (always 3 picks).
2. **Your field**: map of the fields around the farm (USDA CDL, Sentinel-2 NDVI). Illustration only, it does not
   change the numbers.
3. **Build your rotation**: three year cards (the scorer ranks three-crop rotations), drag and drop or menus and
   arrows, optional triticale cover. Sent to the API as `rotation=`; it replaces the crop-history rotation.
4. **Compare**: table against the scorer's picks, water vs. nitrogen.
5. **Season view** and **Why**: monthly timeline (water / nitrogen / temperature risk), effects per season,
   score breakdown.

The page state lives in the URL hash, so a view can be shared. Design: the team's Mockup v2.

## Run

Two terminals, both from the repo root:

```bash
uv run python -m explorer.api      # backend: scorer ranking + explorer, http://127.0.0.1:8000/api/explorer
cd frontend && npm install && npm run dev
```

Vite proxies `/api` to the backend (`vite.config.ts`). Without the backend the results page shows an error.

## Data

- Request: `GET /api/explorer?crops=corn,soybean&n=3&w=water:5,risk:3,soil_health:3,nitrogen:2&rotation=corn-soybean-sorghum%2Btriticale`
  (built in `src/lib/request.ts`). The weights are the scorer's criteria; `n` is 1-3; `rotation` is optional.
- Answer: `explorer.json`, contract in `explorer/schema.py`, mirrored in `src/types.ts`.
- `src/data/normalize.ts` derives the compared values (per year, since passes differ in length);
  labels and directions live in `src/config/metrics.ts`.
- Other source: set `VITE_EXPLORER_DATA_URL`, e.g. to a static `explorer.json` (the inputs are then ignored).
- Location: there is data for one field (Kearny County, KS) so far; the map does not change the numbers.

```bash
npm run build   # type check + build
npm run lint
```
