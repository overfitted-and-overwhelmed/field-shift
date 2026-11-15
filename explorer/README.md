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
  `crop_scorer/scoring/ui_input_mock.json` (a mock until the UI sends weights). Picks have at most one Sclerotinia host
  (sunflower or soybean) per pass (scorer rotation rule, NDSU A1995 p. 46, see `data/processed/rotation_scores/README.md`).

## What a rotation looks like

A rotation is **one pass** of the scorer's crops (3 today), from the first sowing to the last harvest:

- **The number of seasons and months varies.** Two harvests can fall into one year (double crop, e.g.
  wheat harvested in June, soybean sown right after), and a year can be skipped (the next crop missed
  its planting window). Do not assume one season per year or a fixed number of months.
- `monthly` covers exactly the window: from the month of the first sowing to the month of the day before
  the last harvest (e.g. harvest 2 October -> last month is October). The first and last month can be partial.
- The first sowing is in `field.rotation_start_year` (2027).

### Cover crops

The scorer also has every rotation with a **triticale cover crop** where it fits: the `id` then ends in
`+triticale` (e.g. `corn-soybean-sorghum+triticale`). The scorer sows it in every gap of the pass where it fits
(after harvest, terminated before the next crop), so not every season gets one:

- `sequence[].cover` is `"triticale"` for each season with a cover crop in the gap after it, else `null`
  (never after the last season: that gap is outside the window).
- `monthly[].kind` is `"cover"` (with `crop: "triticale"`) in months where the cover crop stands most days.
- Cover crop days are not bare (`bare_months`) and are not irrigated. The cover takes soil water, so the
  next crop's water need and rain-fed yield can change.

**Cover crop switch:** every rotation in `rotations` carries `cover_variant`: the same crops with the cover crop
toggled (`corn-corn-corn` ↔ `corn-corn-corn+triticale`), as a full rotation with its own score, kpi, sequence,
monthly and summary. To switch, show `cover_variant` instead of the rotation. It takes the same slot
(`is_current`, `rank`, `short`), so the farmer's rotation stays "Your rotation" and pick #1 stays pick #1.
`cover_variant` is `null` where no gap of the rotation fits a cover crop (e.g. corn → winter wheat → sorghum),
and a variant never has a variant itself. The ranking is not redone: switched off, the picks are the same crops
without the cover crop, not the best rotations without a cover crop (`kpi.rank_all` shows where they stand).

## Conventions

- Units are in the field name: `_in` = inches of water, `_lb` = lb N per acre, `_ft` = feet, `_pct` = 0–100.
  Everything is in US units except temperature thresholds (°C, e.g. `heat_days_ge_35`). No unit toggle in the UI.
- Dates are ISO strings `YYYY-MM-DD` (`plant_date`, `harvest_date`). A season's `year` is its harvest
  year. The harvest day itself is not part of the season.
- All averages over the weather years are means: `monthly` and the season values `irr_in` / `yield`
  (`v`, plus 10th–90th percentile `p10`, `p90`). So months add up to the season.
- Temperature stress per month, only while a crop stands:
  - `heat_days` / `cold_stress_days` / `kill_days`: **mean number of stress days** in that month. Show these.
    Continuous corn: heat 4.4 days in May, 19.9 in July, 8.2 in September; cold stress 1.3 in May, 0 in summer.
  - `heat_years_pct` / `cold_stress_years_pct` / `kill_years_pct`: share of weather years with at least one
    stress day in that month. One day is enough, so heat is ~100 in every summer month; use the days instead.
  - heat: Tmax above the crop's optimum (e.g. corn 33 °C)
  - cold stress: below the crop's **absolute minimum** (Ecocrop: no growth below it, e.g. corn 10 °C,
    sorghum 8 °C) for **at least half the day**. Below the optimum the crop only grows slower, that is not
    counted, so there is no cold stress in summer.
  - kill: below the crop's killing temperature, i.e. real frost damage. Only winter wheat in its winter rest
    (Nov–Mar, below −20 °C) has a documented one, so `kill_*` is 0 for every other crop and month
    (see `crop_scorer/risk_score/README.md`).
  Thresholds are the scorer's (Ecocrop). There is no "frost" field on purpose: real frost is `kill`.
- Nitrogen comes from the scorer: `sequence[].n_lb` = N fertilizer of the season after K-State MF2586,
  `n_adj_lb` = the previous-crop adjustment in that formula (negative = credit, e.g. −40 after soybean;
  +27.5 after a cover crop, SARE). Soybean is 0 (no K-State formula, assumption, see its `effects`).
  **`null` means "not computed"**: K-State gives the need per season, not a monthly balance or losses, so
  `monthly.nitrogen` and `summary.n_loss_lb` stay null.
- `score` and `score_parts` are the scorer's: **0 = best, 1 = worst** among all its rotations.
  `score_parts` has one value per scorer criterion: `water`, `risk`, `soil_health`, `nitrogen`.
  `rank`, `score` and `score_parts` are passed through unchanged. `kpi` holds the scorer's values for the
  whole pass, converted to US units (`irrigation_in`, `water_in_per_day`, `n_lb`), plus per year of the rotation
  (`irrigation_in_per_year`, `n_lb_per_year` = pass value / (`cycle_days` / 365.25); `cycle_days` = first sowing
  to the first sowing of the next pass). Compare rotations per year: a pass is 2–3 years long and not the same
  for every rotation. The scorer's `frost_days` is left out (days below the optimum, not frost).
- Two kinds of "per year": `summary.bare_months` is per year of the **window** (first sowing to last harvest;
  the gap after the last harvest is not counted, e.g. continuous corn 5.7, over the full cycle about 6.9). The
  `kpi.*_per_year` values are per year of the **cycle** (first sowing to the first sowing of the next pass).
  In the UI say "bare months within the rotation", not just "per year".
- `sequence[].irrigation` is an assumption (`full` for every season) until the farmer can choose it.
- Every per-year list in `climate` is aligned to `climate.weather_years`.
- `provenance` says what kind of number a field is (`measured | modeled | rule | assumption`)
  and which entry in `sources` it comes from.

## For us

```bash
uv run python -m explorer.build    # regenerate the examples from the scorer's data
uv run python -m explorer.api      # API for the frontend on http://127.0.0.1:8000/api/explorer
uv run pytest                      # examples match schema.py, every rule rejects bad data, adapters match the scorer
```

If you change a format: change `schema.py` first, bump `CONTRACT_VERSION`, then regenerate the examples.

| Module | Work package | What it does |
|---|---|---|
| `schema.py` | WP0 | the data contract |
| `field_climate.py` | WP1 | field, crops, climate |
| `water.py` | WP2 | irrigation per season and month, from the scorer's water balance |
| `yields.py` | WP3 | yield per season |
| `nitrogen.py` | WP4 | N fertilizer and previous-crop adjustment per season, from the scorer (K-State) |
| `field_calendar.py` | WP5 | the scorer's seasons placed in the display years, crop per month, bare months |
| `frost_heat.py` | WP6 | heat / cold stress / kill per month (cold stress: at least half a day below the optimum) |
| `build.py` | WP7 | puts everything together and writes the examples |
| `api.py` | WP7 | HTTP API for the frontend: `build_explorer` for the farmer's weights, crops and number of picks |
