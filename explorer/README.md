# explorer

Backend for the Field Shift Explorer. The scorer (`crop_scorer/`) picks crop rotations, decides their
seasons and computes water and temperature risk. We take that over, add yield, and write one JSON file
for the frontend.

```
scorer ──(scorer/response.json)──► explorer ──(explorer.json)──► frontend
          our INPUT                             our OUTPUT
```

## Examples

```
explorer/examples/
├─ explorer.json           # OUTPUT: field, crops, climate, rotations (seasons, months, summary), sources
└─ scorer/
   └─ response.json        # INPUT: the scorer's rotations with their seasons and scores
```

Both files are generated from real data: `uv run python -m explorer.build`.

- **Frontend:** build against `explorer.json`. Ignore `scorer/`.
- The formats are defined in [`schema.py`](schema.py). Every field and allowed value is listed there.
- The rotations are the field's current rotation plus the scorer's top 3 for the weights in
  `crop_scorer/scoring/ui_input_mock.json` (a mock until the UI sends weights).

## What a rotation looks like

A rotation is **one pass** of the scorer's crops (3 today), from the first sowing to the last harvest:

- **The number of seasons and months varies.** Two harvests can fall into one year (double crop, e.g.
  wheat harvested in June, soybean sown right after), and a year can be skipped (the next crop missed
  its planting window). Do not assume one season per year or a fixed number of months.
- `monthly` covers exactly the window: from the month of the first sowing to the month before the last
  harvest. The first and last month can be partial.
- The first sowing is in `field.rotation_start_year` (2027).

## Conventions

- Units are in the field name: `_in` = inches of water, `_lb` = lb N per acre, `_ft` = feet, `_pct` = 0–100.
  Everything is in US units except temperature thresholds (°C, e.g. `heat_days_ge_35`). No unit toggle in the UI.
- Dates are ISO strings `YYYY-MM-DD` (`plant_date`, `harvest_date`). A season's `year` is its harvest
  year. The harvest day itself is not part of the season.
- All averages over the weather years are means: `monthly` and the season values `irr_in` / `yield`
  (`v`, plus 10th–90th percentile `p10`, `p90`). So months add up to the season.
- `heat_years_pct` / `cold_stress_years_pct` / `kill_years_pct`: share of weather years with at least one
  stress day in that month.
  - heat: Tmax above the crop's optimum (close to 100 in most summer crop months)
  - cold stress: below the crop's optimum for **at least half the day** (not just a cool night)
  - kill: below the crop's killing temperature, i.e. real frost damage
  Thresholds are the scorer's (Ecocrop). There is no "frost" field on purpose: real frost is `kill`.
- **`null` means "not computed yet"**: nitrogen (`n_lb`, `n_adj_lb`, `monthly.nitrogen`, `summary.n_loss_lb`)
  is null until WP4 Nitrogen is done.
- `score` and `score_parts` are the scorer's: **0 = best, 1 = worst** among all its rotations.
  `rank`, `score`, `score_parts` and `kpi` are passed through unchanged.
- `sequence[].irrigation` is an assumption (`full` for every season) until the farmer can choose it.
- Every per-year list in `climate` is aligned to `climate.weather_years`.
- `provenance` says what kind of number a field is (`measured | modeled | rule | assumption`)
  and which entry in `sources` it comes from.

## For us

```bash
uv run python -m explorer.build    # regenerate the examples from the scorer's data
uv run pytest                      # examples match schema.py, every rule rejects bad data, adapters match the scorer
```

If you change a format: change `schema.py` first, bump `CONTRACT_VERSION`, then regenerate the examples.

| Module | Work package | What it does |
|---|---|---|
| `schema.py` | WP0 | the data contract |
| `field_climate.py` | WP1 | field, crops, climate |
| `water.py` | WP2 | irrigation per season and month, from the scorer's water balance |
| `yields.py` | WP3 | yield per season |
| `field_calendar.py` | WP5 | the scorer's seasons placed in the display years, crop per month, bare months |
| `frost_heat.py` | WP6 | heat / cold stress / kill per month (cold stress: at least half a day below the optimum) |
| `build.py` | WP7 | puts everything together and writes the examples |
