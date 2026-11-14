"""Clean the raw NASA POWER long file: readable parameter names, basic checks.

Usage: uv run python src/clean_power.py
"""
from pathlib import Path

import pandas as pd

RAW = Path("data/raw/power_daily_long.csv")
OUT = Path("data/processed/power_daily_long.csv")

RENAME = {
    "T2M": "air_temperature_mean",
    "T2M_MAX": "air_temperature_max",
    "T2M_MIN": "air_temperature_min",
    "PRECTOTCORR": "precipitation",
    "RH2M": "relative_humidity",
    "WS2M": "wind_speed",
    "ALLSKY_SFC_SW_DWN": "solar_radiation",
    "GWETROOT": "soil_wetness_root_zone",
    "GWETTOP": "soil_wetness_surface",
    "EVPTRNS": "evapotranspiration",
}

df = pd.read_csv(RAW, parse_dates=["date"])
unknown = set(df["parameter"]) - set(RENAME)
assert not unknown, f"unmapped parameters: {unknown}"
df["parameter"] = df["parameter"].map(RENAME)
df["unit"] = df["unit"].str.replace("^", "", regex=False)  # m^2 -> m2

assert not df.duplicated(["date", "parameter"]).any(), "duplicate date/parameter rows"
df = df.sort_values(["parameter", "date"]).reset_index(drop=True)

OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)
print(f"{len(df)} rows, {df['value'].isna().sum()} missing, "
      f"{df['date'].min().date()} to {df['date'].max().date()} -> {OUT}")
print(df.groupby("parameter").agg(unit=("unit", "first"), mean=("value", "mean")).round(2))
