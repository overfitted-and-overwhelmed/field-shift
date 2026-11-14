"""Daily irrigation need of a crop rotation on field ks-kearny-01, replayed on weather 1991-2025.

Every day the crop wants ETc = Kc x ET0 (FAO-56). It draws this from a root zone soil water bucket that
only rain refills (FAO-56 ch. 8, eq. 85, without runoff and capillary rise). Below the stress threshold
the crop only gets ETa = Ks x ETc. The gap ETc - ETa is the daily irrigation need.

Kc curves: FAO-56 Table 11 stage lengths scaled to the Kansas season (NASS crop calendar), Table 12 Kc.
Bucket size: SSURGO available water capacity down to the max root depth of FAO-56 Table 22.
The rotation is started once in every year, so every crop meets every weather year.

Output: daily dataset for the test rotation (data/processed/water_usage) and
rotation_irrigation_need(), the summed need per rotation cycle for the scorer's loss function.
"""

import json
from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
CLIMATE_DIR = REPO / "data/processed/climate_data"
ET0_FILE = CLIMATE_DIR / "features_daily_long.csv"
WEATHER_FILE = CLIMATE_DIR / "power_daily_long.csv"
SOIL_FILE = REPO / "data/base-data/z_processed/soil_ssurgo_long.csv"
NASS_FILE = REPO / "data/base-data/nass/kansas_crop_calendar_long.csv"
FAO_T11_FILE = REPO / "data/base-data/fao56/fao56_table11_stage_lengths.csv"
FAO_T12_FILE = REPO / "data/base-data/fao56/fao56_table12_kc.csv"
FAO_T22_FILE = REPO / "data/base-data/fao56/fao56_table22_root_depletion.csv"
FIELD_FILE = CLIMATE_DIR / "field_profile.json"
OUT_DIR = REPO / "data/processed/water_usage"

ROTATION = ["winter_wheat", "corn", "sorghum"]
FIRST_YEAR, LAST_YEAR = 1991, 2025
STAGES = ["ini", "dev", "mid", "late"]

# ASSUMPTION (no FAO fallow value): bare soil evaporation = kc_ini of corn/sorghum, whose
# initial stage ET is mostly soil evaporation. Overestimates fallow losses once the topsoil is dry.
FALLOW_KC = 0.3

# FAO-56 rows per crop: (Table 11 crop, Table 11 region), (Table 12/22 crop, Table 12 variant)
FAO_ROWS = {
    "corn": (("Maize (grain)", "Idaho, USA"), ("Maize, Field (grain) (field corn)", "")),
    "sorghum": (("Sorghum", "USA, Pakis., Med."), ("Sorghum", "grain")),
    "soybean": (("Soybeans", "Central USA"), ("Soybeans", "")),
    "sunflower": (("Sunflower", "Medit.; California"), ("Sunflower", "")),
    "winter_wheat": (("Winter Wheat", "Idaho, USA"), ("Winter Wheat", "with frozen soils")),
}

# daily export: internal column -> (parameter, unit)
DAILY_PARAMS = {
    "etc": ("crop_evapotranspiration", "mm/day"),
    "precipitation": ("precipitation", "mm/day"),
    "irrigation_need": ("irrigation_need", "mm/day"),
}

# Which end of a FAO range ("a-b") to use
RANGE_PICK = {
    ("corn", "kc_end"): min,  # T12 footnote 11: 0.35 = harvest after field drying (~18 % moisture)
    ("winter_wheat", "kc_end"): min,  # T12 footnote 10: higher value is for hand-harvested crops
    ("sorghum", "kc_mid"): np.mean,
    ("sunflower", "kc_mid"): np.mean,
}
# T22 footnote: larger Zr for modelling soil water stress, soil is well drained without restricting layers
for _crop in FAO_ROWS:
    RANGE_PICK[(_crop, "zr_max_m")] = max


def parse_range(crop: str, column: str, raw: str) -> float:
    values = [float(v) for v in str(raw).split("-")]
    if len(values) == 1:
        return values[0]
    return float(RANGE_PICK[(crop, column)](values))


def parse_stage_lengths(row: pd.Series) -> list[float]:
    # "30/35" lists alternatives; take the one that makes the stages add up to L_total
    options = [[float(v) for v in str(row[f"L_{s}"]).split("/")] for s in STAGES]
    total = float(row["L_total"])
    fixed = sum(o[0] for o in options if len(o) == 1)
    return [min(o, key=lambda v: abs(fixed + v - total)) if len(o) > 1 else o[0] for o in options]


def soil_taw_mm(root_depth_m: float) -> float:
    # sum available water capacity (cm water per cm soil) over all layers within the root zone
    soil = pd.read_csv(SOIL_FILE)
    awc = soil[soil["parameter"] == "available_water_capacity"]
    assert (awc["unit"] == "cm/cm").all()
    depth_cm = root_depth_m * 100
    thickness = (awc["depth_bottom_cm"].clip(upper=depth_cm) - awc["depth_top_cm"]).clip(lower=0)
    return float((awc["value"] * thickness).sum() * 10)


@cache
def load_crop_params() -> pd.DataFrame:
    t11 = pd.read_csv(FAO_T11_FILE).fillna({"variant": "", "region": ""})
    t12 = pd.read_csv(FAO_T12_FILE).fillna({"variant": ""})
    t22 = pd.read_csv(FAO_T22_FILE).set_index("crop")
    nass = pd.read_csv(NASS_FILE).pivot(index="crop", columns="parameter", values="value")

    rows = []
    for crop, ((t11_crop, region), (t12_crop, variant)) in FAO_ROWS.items():
        stage_row = t11[(t11["crop"] == t11_crop) & (t11["region"] == region)].squeeze()
        kc_row = t12[(t12["crop"] == t12_crop) & (t12["variant"] == variant)].squeeze()
        lengths = parse_stage_lengths(stage_row)
        root_depth = parse_range(crop, "zr_max_m", t22.loc[t12_crop, "zr_max_m"])

        # season = middle of the NASS "most active" planting window -> middle of harvest window
        sow_doy = int(nass.loc[crop, "planting_most_active_start"] + nass.loc[crop, "planting_most_active_end"]) // 2
        harvest_doy = int(nass.loc[crop, "harvest_most_active_start"] + nass.loc[crop, "harvest_most_active_end"]) // 2
        season_days = (harvest_doy - sow_doy) % 365

        rows.append({
            "crop": crop,
            "sow_doy": sow_doy,
            "season_days": season_days,
            # FAO-56 stage shares, scaled to the local season length (FAO-56 ch. 6: Table 11 is only a guide)
            "stage_ends": np.round(np.cumsum(lengths) / sum(lengths) * season_days).astype(int),
            "kc_ini": parse_range(crop, "kc_ini", kc_row["kc_ini"]),
            "kc_mid": parse_range(crop, "kc_mid", kc_row["kc_mid"]),
            "kc_end": parse_range(crop, "kc_end", kc_row["kc_end"]),
            "root_depth_m": root_depth,
            "taw_mm": round(soil_taw_mm(root_depth), 1),
            "p": float(t22.loc[t12_crop, "p"]),
        })
    return pd.DataFrame(rows).set_index("crop")


@cache
def load_weather() -> pd.DataFrame:
    et0 = pd.read_csv(ET0_FILE, parse_dates=["date"])
    et0 = et0[et0["parameter"] == "reference_evapotranspiration"]
    rain = pd.read_csv(WEATHER_FILE, parse_dates=["date"])
    rain = rain[rain["parameter"] == "precipitation"]
    assert (et0["unit"] == "mm/day").all() and (rain["unit"] == "mm/day").all()
    return pd.DataFrame({
        "et0": et0.set_index("date")["value"],
        "precipitation": rain.set_index("date")["value"],
    }).loc[f"{FIRST_YEAR}":f"{LAST_YEAR}"]


def build_timeline(params: pd.DataFrame, rotation: list[str], start_year: int) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    # each crop goes in at its next sowing date after the previous harvest
    seasons = []
    earliest = pd.Timestamp(start_year, 1, 1)
    end_of_data = pd.Timestamp(LAST_YEAR, 12, 31)
    i = 0
    while True:
        crop = rotation[i % len(rotation)]
        p = params.loc[crop]
        sow = pd.Timestamp(earliest.year, 1, 1) + pd.Timedelta(days=int(p["sow_doy"]) - 1)
        if sow <= earliest:
            sow = pd.Timestamp(earliest.year + 1, 1, 1) + pd.Timedelta(days=int(p["sow_doy"]) - 1)
        harvest = sow + pd.Timedelta(days=int(p["season_days"]))
        if harvest > end_of_data:
            return seasons
        seasons.append((crop, sow, harvest))
        earliest = harvest
        i += 1


def kc_curve(p: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    # FAO-56 piecewise linear Kc: flat ini, rise during dev, flat mid, decline during late
    ini_end, dev_end, mid_end, season_end = p["stage_ends"]
    days = np.arange(season_end)
    kc = np.interp(
        days,
        [0, ini_end, dev_end, mid_end, season_end],
        [p["kc_ini"], p["kc_ini"], p["kc_mid"], p["kc_mid"], p["kc_end"]],
    )
    stage = np.array(STAGES)[np.searchsorted(p["stage_ends"], days, side="right")]
    return kc, stage


def crop_calendar(params: pd.DataFrame, weather: pd.DataFrame, seasons: list) -> pd.DataFrame:
    daily = weather.assign(crop="fallow", harvest_year=0, stage="", kc=FALLOW_KC)
    for crop, sow, harvest in seasons:
        kc, stage = kc_curve(params.loc[crop])
        dates = pd.date_range(sow, periods=len(kc))
        daily.loc[dates, "crop"] = crop
        daily.loc[dates, "harvest_year"] = harvest.year
        daily.loc[dates, "stage"] = stage
        daily.loc[dates, "kc"] = kc

    # during fallow the bucket already has the size of the next crop's root zone (it stores water for it)
    bucket_crop = daily["crop"].where(daily["crop"] != "fallow").bfill().ffill()
    daily["taw_mm"] = bucket_crop.map(params["taw_mm"])
    daily["p_table"] = bucket_crop.map(params["p"])
    daily["etc"] = daily["kc"] * daily["et0"]
    return daily


def soil_water_balance(daily: pd.DataFrame) -> pd.DataFrame:
    n = len(daily)
    etc, rain, taw = daily["etc"].to_numpy(), daily["precipitation"].to_numpy(), daily["taw_mm"].to_numpy()
    # FAO-56 Table 22 note: p rises when ETc is low, falls when ETc is high;
    # 7-day mean ETc so the threshold does not jump with single hot days
    etc_week = daily["etc"].rolling(7, min_periods=1).mean().to_numpy()
    p = np.clip(daily["p_table"].to_numpy() + 0.04 * (5 - etc_week), 0.1, 0.8)
    raw = p * taw

    eta = np.zeros(n)
    depletion = 0.0  # bucket full at the start of the replay
    for i in range(n):
        if i > 0 and taw[i] != taw[i - 1]:
            depletion *= taw[i] / taw[i - 1]  # keep the fill level when the root zone changes
        depletion = max(0.0, depletion - rain[i])  # rain above field capacity percolates
        # FAO-56 eq. 84: below the threshold the crop gets only a share Ks of ETc
        ks = 1.0 if depletion <= raw[i] else max(0.0, (taw[i] - depletion) / ((1 - p[i]) * taw[i]))
        eta[i] = ks * etc[i]
        depletion += eta[i]

    in_crop = daily["crop"] != "fallow"
    return daily.assign(eta=eta, irrigation_need=np.where(in_crop, daily["etc"] - eta, 0.0))


def simulate(rotation: list[str], start_year: int) -> tuple[pd.DataFrame, list]:
    params = load_crop_params()
    seasons = build_timeline(params, rotation, start_year)
    calendar = crop_calendar(params, load_weather().loc[f"{start_year}":], seasons)
    return soil_water_balance(calendar), seasons


def rotation_irrigation_need(rotation: list[str]) -> pd.DataFrame:
    # one row per start year: irrigation need summed over one full cycle of the rotation
    rows = []
    for start_year in range(FIRST_YEAR, LAST_YEAR + 1):
        daily, seasons = simulate(rotation, start_year)
        if len(seasons) < len(rotation):
            continue
        first_sow, last_harvest = seasons[0][1], seasons[len(rotation) - 1][2]
        rows.append({
            "start_year": start_year,
            "first_sow": first_sow.date(),
            "last_harvest": last_harvest.date(),
            "cycle_years": round((last_harvest - first_sow).days / 365.25, 1),
            "irrigation_need_mm": round(daily.loc[first_sow:last_harvest - pd.Timedelta(days=1), "irrigation_need"].sum(), 1),
        })
    return pd.DataFrame(rows)


def to_long(df: pd.DataFrame, ids: list[str], params: dict, lat: float, lon: float) -> pd.DataFrame:
    long = df.melt(id_vars=ids, value_vars=list(params), var_name="column")
    long["parameter"] = long["column"].map(lambda c: params[c][0])
    long["unit"] = long["column"].map(lambda c: params[c][1])
    long["value"] = long["value"].round(2)
    return long.assign(lat=lat, lon=lon)[["lat", "lon", *ids, "parameter", "value", "unit"]]


def main():
    print("[water] crop parameters:")
    print(load_crop_params().loc[ROTATION].to_string())

    runs = []
    for start_year in range(FIRST_YEAR, LAST_YEAR + 1):
        daily, seasons = simulate(ROTATION, start_year)
        if seasons:
            runs.append(daily[daily["crop"] != "fallow"])

    # runs differ only in their history (start state of the bucket), so average them per crop season
    daily_mean = (
        pd.concat(runs).rename_axis("date").reset_index()
        .groupby(["crop", "harvest_year", "date", "stage"])[list(DAILY_PARAMS)].mean().reset_index()
    )
    location = json.loads(FIELD_FILE.read_text())["location"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    to_long(daily_mean, ["date", "crop", "harvest_year", "stage"], DAILY_PARAMS, location["lat"], location["lon"]).to_csv(
        OUT_DIR / "irrigation_need_daily_long.csv", index=False)

    per_season = daily_mean.groupby(["harvest_year", "crop"])["irrigation_need"].sum().unstack()
    print(f"\n[water] irrigation need per season (mm), mean over {len(runs)} start years")
    print(per_season.round(0).to_string())
    print(per_season.describe().loc[["mean", "min", "max"]].round(0).to_string())

    cycles = rotation_irrigation_need(ROTATION)
    print(f"\n[water] rotation {' -> '.join(ROTATION)}: irrigation need per cycle (mm)")
    print(cycles.to_string(index=False))
    print(cycles["irrigation_need_mm"].describe()[["mean", "min", "max"]].round(0).to_string())
    print(f"\n[water] written to {(OUT_DIR / 'irrigation_need_daily_long.csv').relative_to(REPO)}")


if __name__ == "__main__":
    main()
