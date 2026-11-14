# explorer

Backend for the Field Shift Explorer. The scorer (separate API) picks crop rotations and computes
their water use. We add what happens on the field per season and month (yield, nitrogen, calendar,
frost/heat) and write one JSON file for the frontend.

```
scorer ──(scorer/response.json)──► explorer ──(explorer.json)──► frontend
          our INPUT                             our OUTPUT
```

## Examples

```
explorer/examples/
├─ explorer.json           # OUTPUT: field, crops, climate, rotations (incl. seasons, 48 months, summary), sources
└─ scorer/
   └─ response.json        # INPUT: what we expect from the scorer (assumption)
```

- **Frontend:** build against `explorer.json`. It replaces the mockup's `D` object. Ignore `scorer/`.
- **`scorer/response.json`** is our guess at the scorer's answer, based on the mockup. The real
  API is still a black box. When it exists, this file and `ScorerResponse` in `schema.py` change.
  The frontend format should stay the same.
- The formats are defined in [`schema.py`](schema.py). Every field and allowed value is listed there.
- **All numbers are placeholders** for now, converted from the mockup (`"placeholder": true`).
  The structure is final for v1. Real numbers replace them step by step.

Conventions:
- Units are in the field name: `_in` = inches of water, `_lb` = lb N per acre, `_ft` = feet, `_pct` = 0–100.
  Everything is in US units except temperature thresholds (°C, e.g. `heat_days_ge_35`). No unit toggle in the UI.
- All averages over the weather years are means: `monthly` (typical year) and the season values
  `irr_in` / `yield` (`v`, plus 10th–90th percentile `p10`, `p90`). So months add up to the season.
- Dates are ISO strings `YYYY-MM-DD` (`plant_date`, `harvest_date`). A season's `year` is its harvest
  year, so winter wheat for 2029 has a `plant_date` in autumn 2028.
- Every per-year list in `climate` is aligned to `climate.weather_years`.
- `provenance` says what kind of number a field is (`measured | modeled | rule | assumption`)
  and which entry in `sources` it comes from.
- `rank`, `score`, `score_parts` and `kpi` come from the scorer and are passed through unchanged.

## For us

```bash
uv run pytest    # checks that the examples match schema.py and that every rule rejects bad data
```

If you change a format: change `schema.py` first, bump `CONTRACT_VERSION`, then update the examples.
