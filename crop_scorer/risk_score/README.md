# risk_score

Temperature risk score for 5 crops (winter wheat, corn, sorghum, soybean, sunflower) at one field (Kearny County, Kansas), 1991–2025. Temperature only.

**Score: 0 = no risk, higher = riskier.**

## Inputs

| Source | Used for |
|---|---|
| NASA POWER daily Tmin / Tmax / Tmean (`power_daily_long.csv`) | daily temperatures |
| Ecocrop (`ecocrop_selected_crops.csv`) | optimum / absolute temperature limits, kill temperatures |
| NASS Kansas crop calendar | sowing window and harvest start per crop |
| FAO-56 table 11, Ecocrop crop cycle | plausibility check of season length only |

## How it works

1. **Season:** every sowing day in the NASS window (`planting_begin`..`planting_end`) starts one season, ending at `harvest_begin`. Winter wheat ends in the next year. Only season days are scored.
2. **Daily score:**
   - **Heat:** on Tmax. 0 at `temp_opt_max`, 1 at `temp_abs_max`, keeps rising above (no cap, no heat kill).
   - **Frost:** on Tmin. 0 at `temp_opt_min`, 1 at `temp_abs_min` (capped).
   - **Cold kill:** Tmin < 0 °C. Day scores +100 and replaces the stress value.
   - **Winter wheat dormancy** (1 Nov – 31 Mar): no frost stress, kill only below −20 °C.
3. **Season score:** mean of the daily scores.
4. **Yearly score** (`risk_score`, per crop and sowing year): mean of the season scores over the main sowing window (`planting_most_active_*`). Also `score_full_window`, `score_min`, `score_max` and counts of frost / heat / kill days.

## Run

```bash
uv run python -m crop_scorer.risk_score.run
```

Writes to `data/processed/crop_risk_score/` (git-ignored): `risk_score_annual.csv` (main result), `risk_score_seasons.csv` (per sowing day), `risk_score_daily.csv` (per calendar day with `kill`, `stress_flag`, `in_season_any`). Also prints summary, sanity checks and season lengths.

## Files

`config.py` crop limits + parameters · `loader.py` temperature loading and checks · `severity.py` daily score · `seasons.py` seasons and yearly aggregation · `run.py` entry point

## Result (mean over all years)

| Crop | `risk_score` | Kill days / season |
|---|---|---|
| Sunflower | 0.19 | 0.0 |
| Sorghum | 0.47 | 0.0 |
| Corn | 0.60 | 0.3 |
| Soybean | 0.60 | 0.0 |
| Winter wheat | 3.24 | 6.8 |

Corn: earlier sowing (DOY 95–104) has 71 % of seasons with kill days (late frost in April), sowing from DOY 125 has none. Winter wheat kill days are in October (young crop) and April (after dormancy).

## Limits and missing data

- **Temperature only:** no precipitation, soil moisture, soil, light or disease.
- **Ecocrop limits are for mean temperature,** we apply them to Tmin / Tmax (approximation).
- **Kill temperature is an assumption for corn, sorghum and soybean** (Ecocrop has none): 0 °C. Winter wheat and sunflower use Ecocrop's 0 °C. Sunflower's Ecocrop dormancy value (−10 °C) is ignored (it does not overwinter).
- **Dormancy window is an approximation** and drives the winter wheat score strongly (1 Dec – 28 Feb gave 15.07, 1 Nov – 31 Mar gives 3.24). Change via `DEFAULT_WINTER_REST_START/END` in `config.py`.
- **No heat kill:** heat is only penalised through the uncapped severity.
- **Season length comes from NASS** and is the same every year (no year-specific sowing dates). Winter wheat mean 253 d is slightly above Ecocrop's max (250 d, warning only). FAO-56 has no Central-USA entry for corn.
- **Ecocrop has no triticale:** rye is in the file but not used.
- **Winter wheat has no 2025 value** (season 2025/26 is not finished). Sowing years 1991–2024.
- **NASA POWER is ~50 km resolution,** not field-exact. No yield data, so the score is not validated against real losses.
