"""Fetch daily NASA POWER data for a single point (the "field") and store it in long format.

Usage:
    uv run python src/fetch_power.py --lat 52.52 --lon 13.40 --start 1991 --end 2025
"""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
# Agro standard set
PARAMETERS = [
    "T2M", "T2M_MAX", "T2M_MIN",      # air temperature [°C]
    "PRECTOTCORR",                     # precipitation [mm/day]
    "RH2M",                            # relative humidity [%]
    "WS2M",                            # wind speed at 2 m [m/s]
    "ALLSKY_SFC_SW_DWN",               # shortwave radiation [MJ/m²/day]
    "GWETROOT", "GWETTOP",             # soil wetness root zone / surface [0-1]
    "EVPTRNS",                         # evapotranspiration [mm/day]
]
FILL_VALUE = -999.0


def fetch(lat: float, lon: float, start: int, end: int, parameters=PARAMETERS) -> dict:
    query = urllib.parse.urlencode({
        "parameters": ",".join(parameters),
        "community": "AG",
        "longitude": lon,
        "latitude": lat,
        "start": f"{start}0101",
        "end": f"{end}1231",
        "format": "JSON",
    })
    with urllib.request.urlopen(f"{URL}?{query}", timeout=300) as resp:
        return json.load(resp)


def to_long(payload: dict) -> pd.DataFrame:
    """Convert POWER JSON into long format: date, parameter, value, unit."""
    data = payload["properties"]["parameter"]
    units = {k: v.get("units", "") for k, v in payload["parameters"].items()}
    wide = pd.DataFrame(data)  # index = YYYYMMDD, columns = parameters
    wide.index = pd.to_datetime(wide.index, format="%Y%m%d")
    wide.index.name = "date"
    long = wide.reset_index().melt(id_vars="date", var_name="parameter", value_name="value")
    long["value"] = long["value"].where(long["value"] != FILL_VALUE)  # -999 -> NaN
    long["unit"] = long["parameter"].map(units)
    return long.sort_values(["parameter", "date"]).reset_index(drop=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--start", type=int, default=1991)
    p.add_argument("--end", type=int, default=2025)
    p.add_argument("--out", type=Path, default=Path("data/raw/power_daily_long.csv"))
    a = p.parse_args()

    payload = fetch(a.lat, a.lon, a.start, a.end)
    long = to_long(payload)
    long.insert(0, "lon", a.lon)
    long.insert(0, "lat", a.lat)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    long.to_csv(a.out, index=False)
    print(f"{len(long)} rows, {long['value'].isna().sum()} missing -> {a.out}")


if __name__ == "__main__":
    main()
