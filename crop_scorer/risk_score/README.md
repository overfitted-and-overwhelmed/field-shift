# risk_score

Temperature risk score for 5 crops (winter wheat, corn, sorghum, soybean, sunflower) at one field (Kearny County, Kansas), 1991–2025. Temperature only.

**Score: 0 = no risk, higher = riskier.**

## Inputs

| Source | Used for |
|---|---|
| NASA POWER daily Tmin / Tmax / Tmean (`power_daily_long.csv`) | daily temperatures |
| Ecocrop (`ecocrop_selected_crops.csv`) | optimum / absolute temperature limits, kill temperature during rest (winter wheat) |
| NASS Kansas crop calendar | most-active sowing and harvest window per crop |
| FAO-56 table 11, Ecocrop crop cycle | plausibility check of season length only |

## How it works

1. **Season:** same definition as `water_usage`. One season per crop and year, from the middle of the NASS most-active sowing window to the middle of the most-active harvest window (`(start + end) // 2`, `season_days = (harvest_doy - sow_doy) % 365`). Winter wheat ends in the next year. Only season days are scored (harvest day excluded).
2. **Daily score:**
   - **Heat:** on Tmax. 0 at `temp_opt_max`, 1 at `temp_abs_max`, keeps rising above (no cap, no heat kill).
   - **Frost:** on Tmin. 0 at `temp_opt_min`, 1 at `temp_abs_min` (capped).
   - **Cold kill:** only winter wheat in its dormancy (1 Nov – 31 Mar): Tmin < −20 °C (Ecocrop, killing temperature during rest). Day scores 100 and replaces the stress value. No frost stress during dormancy.
   - **No kill outside the dormancy:** no crop has a documented killing temperature for the whole season, so cold only counts as frost stress (see Limits).
3. **Season score:** mean of the daily scores.
4. **Yearly score** (`risk_score`, per crop and sowing year): the season score of that one season. Also counts of frost / heat / kill days (`frost_days`, `heat_days`, `kill_days`).

## Run

```bash
uv run python -m crop_scorer.risk_score.run
```

Writes to `data/processed/crop_risk_score/` (git-ignored): `risk_score_annual.csv` (main result), `risk_score_seasons.csv` (per sowing day), `risk_score_daily.csv` (per calendar day with `kill`, `stress_flag`, `in_season_any`). Also prints summary, sanity checks and season lengths.

## Files

`config.py` crop limits + parameters · `loader.py` temperature loading and checks · `severity.py` daily score · `seasons.py` seasons and yearly aggregation · `rotation.py` risk on the seasons of a crop rotation (from `water_usage.build_timeline`, incl. shifted sowing) · `run.py` entry point

## Result (mean over all years)

| Crop | `risk_score` | Kill days / season |
|---|---|---|
| Corn | 0.41 | 0 |
| Sorghum | 0.53 | 0 |
| Soybean | 0.64 | 0 |
| Sunflower | 0.29 | 0 |
| Winter wheat | 0.75 | 0.15 |

## Limits and missing data

- **Temperature only:** no precipitation, soil moisture, soil, light or disease.
- **Ecocrop limits are for mean temperature,** we apply them to Tmin / Tmax (approximation).
- **No kill temperature outside the winter wheat dormancy.** Ecocrop has none for corn, sorghum and soybean. For winter wheat and sunflower it gives 0 °C for *early growth* only (seedlings), not for the whole season; applied to the whole season it made every night below 0 °C in April and October a kill day for wheat (6.85 per season, 97 % of years). K-State puts the injurious temperature of wheat much lower (about −11 °C at tillering, −4 °C at jointing, for 2 hours; K-State C646 *Spring Freeze Injury to Kansas Wheat*, https://bookstore.ksre.ksu.edu/pubs/C646.PDF), but using it needs the wheat growth stages, which we do not model. Frost below the optimum still counts as stress. Sunflower's Ecocrop dormancy value (−10 °C) is ignored (it does not overwinter).
- **Dormancy window is an approximation.** Change via `DEFAULT_WINTER_REST_START/END` in `config.py`.
- **No heat kill:** heat is only penalised through the uncapped severity.
- **Season length comes from NASS** and is the same every year (no year-specific sowing dates). One fixed sowing day per crop (middle of the most-active window), so the score does not show the effect of early vs. late sowing. Winter wheat 268 d is above Ecocrop's max (250 d, warning only). FAO-56 has no Central-USA entry for corn.
- **Ecocrop has no triticale:** rye is in the file but not used.
- **Winter wheat has no 2025 value** (season 2025/26 is not finished). Sowing years 1991–2024.
- **NASA POWER is ~50 km resolution,** not field-exact. No yield data, so the score is not validated against real losses.
