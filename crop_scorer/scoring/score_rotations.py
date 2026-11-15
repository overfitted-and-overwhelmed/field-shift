"""Score crop rotations on water, temperature risk and soil health, rank them and export the best ones.

All three scores use the same seasons (water_usage.build_timeline) and the same window: first sowing to last
harvest of one pass through the rotation, replayed for every start year with weather 1991-2025. Scores are per
day, so rotations of different length compare:
- water: irrigation need (mm) per window day
- risk: mean daily temperature risk score per crop day (fallow has no risk)
- soil_health: share of bare (fallow) days in the window
Each score is min-max normalised over all rotations of ROTATION_LENGTH crops (0 = best, 1 = worst).
Weights and the farmer's rotation come from ui_input_mock.json until the UI exists; total = weighted mean.

Output (data/processed/rotation_scores): for all rotations rotation_scores.csv (cache for the ranking),
rotation_seasons_by_year.csv and rotation_monthly.csv (so any rotation a user picks can be shown), and for the
TOP_N rotations plus the farmer's rotation top_rotations.csv, top_rotations_seasons.csv, top_rotations_daily_long.csv.
Run from the repo root: uv run python -m crop_scorer.scoring.score_rotations [--rescore]
"""

import itertools
import json
import sys
from functools import cache
from pathlib import Path

import pandas as pd

from crop_scorer.risk_score import load_crop_configs, load_temperature_data, rotation_daily_risk
from crop_scorer.water_usage.water_usage import FIRST_YEAR, LAST_YEAR, REPO, load_crop_params, simulate

OUT_DIR = REPO / "data/processed/rotation_scores"
SCORES_FILE = OUT_DIR / "rotation_scores.csv"
SEASONS_BY_YEAR_FILE = OUT_DIR / "rotation_seasons_by_year.csv"
MONTHLY_FILE = OUT_DIR / "rotation_monthly.csv"
UI_INPUT_FILE = Path(__file__).with_name("ui_input_mock.json")
ROTATION_LENGTH = 3
TOP_N = 10

# criterion -> raw column; smaller is better for all of them
CRITERIA = {"water": "water_mm_per_day", "risk": "risk_per_crop_day", "soil_health": "bare_share"}

# daily export: internal column -> (parameter, unit); means over the start years
DAILY_PARAMS = {
    "etc": ("crop_evapotranspiration", "mm/day"),
    "precipitation": ("precipitation", "mm/day"),
    "irrigation_need": ("irrigation_need", "mm/day"),
    "daily_score": ("temperature_risk_score", "score"),
    "frost": ("frost_day_share", "share of years"),
    "heat": ("heat_day_share", "share of years"),
    "kill": ("kill_day_share", "share of years"),
}


@cache
def risk_inputs() -> tuple[pd.DataFrame, dict]:
    return load_temperature_data(), load_crop_configs()


def rotation_days(rotation: list[str]) -> pd.DataFrame:
    # one row per window day and start year; segment = 2 * season (crop) or 2 * season + 1 (fallow after it)
    windows, all_seasons = [], []
    for start_year in range(FIRST_YEAR, LAST_YEAR + 1):
        daily, seasons = simulate(rotation, start_year)
        if len(seasons) < len(rotation):
            continue  # the pass does not fit into the weather data
        seasons = seasons[: len(rotation)]
        all_seasons += seasons
        window = daily.loc[seasons[0][1] : seasons[-1][2] - pd.Timedelta(days=1)]
        sows = pd.DatetimeIndex([sow for _, sow, _ in seasons])
        harvests = pd.DatetimeIndex([harvest for _, _, harvest in seasons])
        season = sows.searchsorted(window.index, side="right") - 1
        in_crop = window.index < harvests[season]
        assert (in_crop == (window["crop"] != "fallow").to_numpy()).all()
        windows.append(pd.DataFrame({
            "start_year": start_year,
            "date": window.index,
            "segment": 2 * season + (~in_crop).astype(int),
            "crop": window["crop"].to_numpy(),
            **{col: window[col].to_numpy() for col in ["etc", "precipitation", "irrigation_need"]},
        }))
    days = pd.concat(windows, ignore_index=True)
    days["segment_day"] = days.groupby(["start_year", "segment"]).cumcount()

    # the daily risk only depends on crop and date, so overlapping seasons of different start years are equal
    temps, crops = risk_inputs()
    risk = rotation_daily_risk(temps, crops, sorted(set(all_seasons))).drop_duplicates(["crop_key", "date"])
    risk = pd.DataFrame({
        "crop": risk["crop_key"],
        "date": risk["date"],
        "daily_score": risk["daily_score"],
        "frost": ((risk["frost_severity"] > 0) & ~risk["kill"]).astype(float),
        "heat": ((risk["heat_severity"] > 0) & ~risk["kill"]).astype(float),
        "kill": risk["kill"].astype(float),
    })
    return days.merge(risk, on=["crop", "date"], how="left")


def score_days(rotation: list[str], days: pd.DataFrame) -> dict:
    per_year = days.groupby("start_year").agg(
        window_days=("date", "size"),
        crop_days=("daily_score", "count"),
        irrigation_mm=("irrigation_need", "sum"),
        risk_sum=("daily_score", "sum"),
        frost_days=("frost", "sum"),
        heat_days=("heat", "sum"),
        kill_days=("kill", "sum"),
    )
    per_year["water_mm_per_day"] = per_year["irrigation_mm"] / per_year["window_days"]
    per_year["risk_per_crop_day"] = per_year["risk_sum"] / per_year["crop_days"]
    per_year["bare_share"] = 1 - per_year["crop_days"] / per_year["window_days"]
    mean = per_year.mean()
    return {
        "rotation": "-".join(rotation),
        "n_start_years": len(per_year),
        **{col: mean[col] for col in CRITERIA.values()},
        **{col: mean[col] for col in ["window_days", "irrigation_mm", "frost_days", "heat_days", "kill_days"]},
    }


def score_rotation(rotation: list[str]) -> dict:
    # raw scores of any rotation, e.g. one typed in by the farmer
    return score_days(rotation, rotation_days(rotation))


def normalize(scores: pd.DataFrame, reference: pd.DataFrame) -> pd.DataFrame:
    # fixed reference (all rotations), so a rotation's score does not change when another one is added;
    # rotations outside the reference (e.g. other length) can fall below 0 or above 1
    out = scores.copy()
    for name, col in CRITERIA.items():
        low, high = reference[col].min(), reference[col].max()
        out[f"{name}_score"] = (scores[col] - low) / (high - low)
    return out


def rank(scores: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    total = sum(weights[name] * scores[f"{name}_score"] for name in CRITERIA) / sum(weights[name] for name in CRITERIA)
    ranked = scores.assign(total_score=total).sort_values("total_score", ignore_index=True)
    ranked.insert(0, "rank", range(1, len(ranked) + 1))
    return ranked


def score_all(length: int = ROTATION_LENGTH) -> pd.DataFrame:
    rotations = [list(r) for r in itertools.product(load_crop_params().index, repeat=length)]
    print(f"[score] scoring {len(rotations)} rotations of {length} crops")
    rows, seasons, monthly = [], [], []
    for i, rotation in enumerate(rotations, 1):
        days = rotation_days(rotation)
        rows.append(score_days(rotation, days))
        key = "-".join(rotation)
        seasons.append(season_by_year(days).assign(rotation=key))
        monthly.append(monthly_table(days).assign(rotation=key))
        if i % 25 == 0:
            print(f"[score] {i}/{len(rotations)}")
    scores = pd.DataFrame(rows)
    scores = normalize(scores, scores)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    scores.to_csv(SCORES_FILE, index=False, float_format="%.6g")
    for frame, path in [(seasons, SEASONS_BY_YEAR_FILE), (monthly, MONTHLY_FILE)]:
        frame = pd.concat(frame, ignore_index=True)
        frame[["rotation", *frame.columns[:-1]]].to_csv(path, index=False, float_format="%.4g")
    print(f"[score] written to {OUT_DIR.relative_to(REPO)}: {SCORES_FILE.name}, {SEASONS_BY_YEAR_FILE.name}, {MONTHLY_FILE.name}")
    return scores


def mean_cycle(days: pd.DataFrame) -> pd.DataFrame:
    # mean over start years per day of the pass; segments line up across start years (same timeline),
    # only leap years can make a segment one day longer. Dates come from the first start year.
    first = days[days["start_year"] == days["start_year"].min()]
    ref = pd.DataFrame({
        "segment": first["segment"].to_numpy(),
        "segment_day": first["segment_day"].to_numpy(),
        "cycle_day": range(len(first)),
        "month_day": first["date"].dt.strftime("%m-%d").to_numpy(),
        "crop": first["crop"].to_numpy(),
    })
    means = days.groupby(["segment", "segment_day"])[list(DAILY_PARAMS)].mean().reset_index()
    return ref.merge(means, on=["segment", "segment_day"], how="left")


def season_by_year(days: pd.DataFrame) -> pd.DataFrame:
    # one row per season and start year (= weather years of that season)
    out = days[days["segment"] % 2 == 0].groupby(["segment", "start_year"]).agg(
        crop=("crop", "first"),
        sow_date=("date", "min"),
        last_day=("date", "max"),
        season_days=("date", "size"),
        etc_mm=("etc", "sum"),
        precipitation_mm=("precipitation", "sum"),
        irrigation_need_mm=("irrigation_need", "sum"),
        risk_per_crop_day=("daily_score", "mean"),
        frost_days=("frost", "sum"),
        heat_days=("heat", "sum"),
        kill_days=("kill", "sum"),
    ).reset_index()
    out["season"] = out["segment"] // 2
    out["harvest_date"] = out["last_day"] + pd.Timedelta(days=1)  # harvest day is not part of the season
    out["harvest_year"] = out["harvest_date"].dt.year
    out["eta_mm"] = out["etc_mm"] - out["irrigation_need_mm"]  # rain-fed: irrigation need = ETc - ETa
    return out[["season", "crop", "start_year", "sow_date", "harvest_date", "harvest_year", "season_days", "etc_mm",
                "eta_mm", "precipitation_mm", "irrigation_need_mm", "risk_per_crop_day", "frost_days", "heat_days", "kill_days"]]


def season_table(days: pd.DataFrame) -> pd.DataFrame:
    by_year = season_by_year(days)
    first = by_year[by_year["start_year"] == by_year["start_year"].min()].set_index("season")
    means = by_year.groupby("season")[["irrigation_need_mm", "risk_per_crop_day", "frost_days", "heat_days", "kill_days"]].mean()
    out = first[["crop", "sow_date", "harvest_date", "season_days"]].join(means).reset_index()
    out["sow_month_day"] = out["sow_date"].dt.strftime("%m-%d")
    out["harvest_month_day"] = out["harvest_date"].dt.strftime("%m-%d")
    out["sow_cycle_day"] = (out["sow_date"] - out["sow_date"].min()).dt.days
    return out[["season", "crop", "sow_month_day", "harvest_month_day", "sow_cycle_day", "season_days",
                "irrigation_need_mm", "risk_per_crop_day", "frost_days", "heat_days", "kill_days"]]


def monthly_table(days: pd.DataFrame) -> pd.DataFrame:
    # calendar months of the window, mean over start years; year_offset 0 = year of the first sowing.
    # The first and last month are partial (window starts at sowing, ends before harvest).
    first_sow = days.groupby("start_year")["date"].transform("min")
    d = days.assign(year_offset=days["date"].dt.year - first_sow.dt.year, month=days["date"].dt.month)
    keys = ["year_offset", "month"]
    per_year = d.groupby([*keys, "start_year"]).agg(
        window_days=("date", "size"),
        crop_days=("daily_score", "count"),
        et_mm=("etc", "sum"),  # crop ETc, bare soil evaporation on fallow days
        precipitation_mm=("precipitation", "sum"),
        irrigation_need_mm=("irrigation_need", "sum"),
        heat_days=("heat", "sum"),
        frost_days=("frost", "sum"),
        kill_days=("kill", "sum"),
    )
    out = per_year.groupby(keys).mean()
    # share of weather years with at least one stress day in this month (frontend: "share of past years at risk")
    for stress in ["heat", "frost", "kill"]:
        out[f"{stress}_year_share"] = (per_year[f"{stress}_days"] > 0).groupby(keys).mean()
    out["crop"] = d.groupby(keys)["crop"].agg(lambda c: c.mode().iloc[0])  # what stands most days of the month
    return out.reset_index()[[*keys, "crop", *out.columns.drop("crop")]]


def export_top(scores: pd.DataFrame, weights: dict[str, float], current: list[str], top_n: int = TOP_N) -> pd.DataFrame:
    current_key = "-".join(current)
    if current_key not in set(scores["rotation"]):
        scores = pd.concat([scores, normalize(pd.DataFrame([score_rotation(current)]), scores)], ignore_index=True)
    ranked = rank(scores, weights)
    ranked["is_current"] = ranked["rotation"] == current_key
    top = ranked[(ranked["rank"] <= top_n) | ranked["is_current"]]

    seasons, daily = [], []
    for row in top.itertuples():
        days = rotation_days(row.rotation.split("-"))
        seasons.append(season_table(days).assign(rotation=row.rotation, rank=row.rank))
        long = mean_cycle(days).melt(
            id_vars=["cycle_day", "month_day", "crop"], value_vars=list(DAILY_PARAMS), var_name="column"
        ).dropna(subset=["value"])  # fallow days have no risk values
        long["parameter"] = long["column"].map(lambda c: DAILY_PARAMS[c][0])
        long["unit"] = long["column"].map(lambda c: DAILY_PARAMS[c][1])
        daily.append(long.assign(rotation=row.rotation, rank=row.rank))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    top.to_csv(OUT_DIR / "top_rotations.csv", index=False, float_format="%.4g")
    seasons = pd.concat(seasons, ignore_index=True)
    seasons[["rank", "rotation", *seasons.columns[:-2]]].to_csv(OUT_DIR / "top_rotations_seasons.csv", index=False, float_format="%.4g")
    daily = pd.concat(daily, ignore_index=True)
    daily = daily.sort_values(["rank", "parameter", "cycle_day"])
    daily[["rank", "rotation", "cycle_day", "month_day", "crop", "parameter", "value", "unit"]].to_csv(
        OUT_DIR / "top_rotations_daily_long.csv", index=False, float_format="%.4g")
    return top


def main():
    if "--rescore" in sys.argv or not SCORES_FILE.exists():
        scores = score_all()
    else:
        scores = pd.read_csv(SCORES_FILE)
        print(f"[score] using cached {SCORES_FILE.relative_to(REPO)} (--rescore to recompute)")

    ui_input = json.loads(UI_INPUT_FILE.read_text())
    top = export_top(scores, ui_input["weights"], ui_input["current_rotation"])
    print(f"\n[score] weights {ui_input['weights']}, farmer's rotation (mock) {'-'.join(ui_input['current_rotation'])}")
    cols = ["rank", "rotation", "is_current", "total_score", *[f"{n}_score" for n in CRITERIA], *CRITERIA.values()]
    print(top[cols].round(3).to_string(index=False))
    print(f"\n[score] top {TOP_N} + farmer's rotation written to {OUT_DIR.relative_to(REPO)}")


if __name__ == "__main__":
    main()
