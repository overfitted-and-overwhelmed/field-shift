# frontend

React + Vite UI of Field Shift. The farmer enters crops and priorities; the results page shows the scorer's best
rotations next to today's rotation, with the explorer's seasons, monthly water and temperature risk.

## Run

Two terminals, both from the repo root:

```bash
uv run python -m explorer.api      # backend: scorer ranking + explorer, http://127.0.0.1:8000/api/explorer
cd frontend && npm install && npm run dev
```

Vite proxies `/api` to the backend (`vite.config.ts`). Without the backend the results page shows an error.

## Data

- Request: `GET /api/explorer?lat=..&lon=..&crops=corn,soybean&n=3&w=water:5,risk:3,soil_health:3,nitrogen:2`
  (built in `src/lib/request.ts`). The weights are the scorer's criteria; `n` is 1-3.
- Answer: `explorer.json`, contract in `explorer/schema.py`, mirrored in `src/types.ts`.
- `src/data/normalize.ts` derives the compared values (per year, since passes differ in length);
  labels and directions live in `src/config/metrics.ts`.
- Other source: set `VITE_EXPLORER_DATA_URL`, e.g. to a static `explorer.json` (the inputs are then ignored).
- Location: there is data for one field (Kearny County, KS) so far; other map positions show its data with a note.

```bash
npm run build   # type check + build
npm run lint
```
