"""Entry point: compute all crops, write CSVs to data/processed/crop_risk_score/ and print a short summary.

Run from the repo root:  ``uv run python -m crop_scorer.risk_score.run``
"""

from pathlib import Path

import numpy as np
import pandas as pd

from crop_scorer.risk_score.config import (
    DEFAULT_DATA_DIR,
    DEFAULT_KILL_PENALTY,
    DEFAULT_WINTER_REST_END,
    DEFAULT_WINTER_REST_START,
    CropConfig,
    load_crop_configs,
)
from crop_scorer.risk_score.loader import load_temperature_data
from crop_scorer.risk_score.seasons import (
    aggregate_yearly,
    check_season_lengths,
    simulate_seasons,
)
from crop_scorer.risk_score.severity import compute_daily_risk, in_winter_rest

DEFAULT_OUTPUT_DIR = DEFAULT_DATA_DIR / "processed" / "crop_risk_score"
DAILY_FILE = "risk_score_daily.csv"
SEASONS_FILE = "risk_score_seasons.csv"
ANNUAL_FILE = "risk_score_annual.csv"

DAILY_COLUMNS = [
    "crop_key",
    "date",
    "tmin",
    "tmax",
    "tmean",
    "in_season_any",
    "frost_severity",
    "heat_severity",
    "kill",
    "stress_flag",
    "comfort_deviation",
    "daily_score",
]


def _in_season_any(dates: pd.Series, seasons: pd.DataFrame) -> pd.Series:
    """True for days that lie in at least one simulated season (earliest sowing to harvest)."""
    mask = pd.Series(False, index=dates.index)
    spans = seasons.groupby("season_year").agg(start=("sow_date", "min"), end=("harvest_date", "max"))
    for start, end in zip(spans["start"], spans["end"], strict=True):
        mask |= (dates >= start) & (dates <= end)
    return mask


def build_daily_table(
    temps: pd.DataFrame, crop: CropConfig, seasons: pd.DataFrame, kill_penalty: float
) -> pd.DataFrame:
    """Daily risk per calendar day for one crop (all days, flagged with ``in_season_any``)."""
    risk = compute_daily_risk(temps, crop, kill_penalty)
    out = pd.concat([temps[["date", "tmin", "tmax", "tmean"]], risk], axis=1)
    out.insert(0, "crop_key", crop.crop_key)
    out["in_season_any"] = _in_season_any(out["date"], seasons)
    return out[DAILY_COLUMNS]


def sanity_checks(
    daily: pd.DataFrame, seasons: pd.DataFrame, crops: dict[str, CropConfig]
) -> list[tuple[str, bool, str]]:
    """Plausibility checks. Returns (name, ok, detail); never raises."""
    results: list[tuple[str, bool, str]] = []
    season_days = daily[daily["in_season_any"]]

    bad = int((daily["daily_score"] < 0).sum() + daily["daily_score"].isna().sum())
    results.append(("scores_non_negative_and_complete", bad == 0, f"{bad} invalid daily scores"))
    bad = int((seasons["season_score"] < 0).sum() + seasons["season_score"].isna().sum())
    results.append(("season_scores_non_negative_and_complete", bad == 0, f"{bad} invalid season scores"))

    # Heat must never create a kill: every kill day has tmin below the crop's (non-rest) kill limit,
    # or, for winter wheat in the dormancy window, below the rest limit.
    n_bad = 0
    for key, cfg in crops.items():
        d = daily[(daily["crop_key"] == key) & daily["kill"]]
        if cfg.is_winter_crop and cfg.kill_temp_rest is not None:
            rest = in_winter_rest(d["date"].dt.month, d["date"].dt.day, DEFAULT_WINTER_REST_START, DEFAULT_WINTER_REST_END)
            limit = np.where(rest, cfg.kill_temp_rest, cfg.kill_temp_lower)
        else:
            limit = cfg.kill_temp_lower
        n_bad += int((d["tmin"] >= limit).sum())
    results.append(("kill_days_only_from_cold", n_bad == 0, f"{n_bad} kill days not explained by cold"))

    # Kill days in-season should occur in the cold half of the year, not in Jun-Aug.
    summer_kill = int((season_days["kill"] & season_days["date"].dt.month.isin([6, 7, 8])).sum())
    results.append(("no_kill_in_jun_aug", summer_kill == 0, f"{summer_kill} in-season kill days in Jun-Aug"))

    # Winter wheat: dormancy kill only below -20 C.
    ww = crops.get("winter_wheat")
    if ww is not None and ww.kill_temp_rest is not None:
        d = daily[daily["crop_key"] == "winter_wheat"]
        rest = in_winter_rest(d["date"].dt.month, d["date"].dt.day, DEFAULT_WINTER_REST_START, DEFAULT_WINTER_REST_END)
        wrong = int((d["kill"] & rest & (d["tmin"] >= ww.kill_temp_rest)).sum())
        n_rest_kill = int((d["kill"] & rest).sum())
        results.append(
            ("winter_wheat_rest_kill_only_below_limit", wrong == 0, f"{wrong} wrong; {n_rest_kill} rest-window kill days in total")
        )
    return results


def main(output_dir: Path | str = DEFAULT_OUTPUT_DIR, kill_penalty: float = DEFAULT_KILL_PENALTY) -> dict[str, pd.DataFrame]:
    """Compute all crops, write the three CSVs and print a summary."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    crops = load_crop_configs()
    temps = load_temperature_data()

    season_frames, daily_frames = [], []
    for crop in crops.values():
        seasons = simulate_seasons(temps, crop, kill_penalty)
        season_frames.append(seasons)
        daily_frames.append(build_daily_table(temps, crop, seasons, kill_penalty))
    seasons_all = pd.concat(season_frames, ignore_index=True)
    daily_all = pd.concat(daily_frames, ignore_index=True)
    annual = aggregate_yearly(seasons_all)

    daily_all.to_csv(out_dir / DAILY_FILE, index=False, float_format="%.6g")
    seasons_all.to_csv(out_dir / SEASONS_FILE, index=False, float_format="%.6g")
    annual.to_csv(out_dir / ANNUAL_FILE, index=False, float_format="%.6g")

    print(f"Geschrieben nach {out_dir}: {DAILY_FILE} ({len(daily_all)}), {SEASONS_FILE} ({len(seasons_all)}), {ANNUAL_FILE} ({len(annual)})")
    summary = annual.groupby("crop_key").agg(
        years=("season_year", "nunique"),
        risk_score=("risk_score", "mean"),
        score_full_window=("score_full_window", "mean"),
        kill_days_mean=("kill_days_mean", "mean"),
    )
    print("\nMittel über alle Jahre (Hauptsaatfenster):")
    print(summary.round(2).to_string())
    kill_in_season = daily_all[daily_all["in_season_any"] & daily_all["kill"]].groupby("crop_key").size()
    print("\nKill-Tage in Saisons (Kalendertage, alle Jahre):")
    print(kill_in_season.reindex(list(crops)).fillna(0).astype(int).to_string())

    print("\nSanity-Checks:")
    for name, ok, detail in sanity_checks(daily_all, seasons_all, crops):
        print(f"  [{'OK' if ok else 'WARN'}] {name}: {detail}")

    print("\nSaisonlängen (Plausibilität):")
    print(check_season_lengths(seasons_all).round(1).to_string(index=False))

    return {"daily": daily_all, "seasons": seasons_all, "annual": annual}


if __name__ == "__main__":
    main()
