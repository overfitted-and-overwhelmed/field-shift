"""Fetch static soil properties for one point from ISRIC SoilGrids (REST API), long format.

Usage: uv run python src/fetch_soil.py --lat 38.025110 --lon -101.126084
"""
import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
RENAME = {
    "sand": "sand_content", "silt": "silt_content", "clay": "clay_content",
    "soc": "soil_organic_carbon", "phh2o": "ph_water", "bdod": "bulk_density",
    "cec": "cation_exchange_capacity", "nitrogen": "nitrogen",
}
DEPTHS = ["0-5cm", "5-15cm", "15-30cm", "30-60cm", "60-100cm", "100-200cm"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--out", type=Path, default=Path("data/processed/soil_long.csv"))
    a = p.parse_args()

    q = [("lat", a.lat), ("lon", a.lon), ("value", "mean")]
    q += [("property", k) for k in RENAME] + [("depth", d) for d in DEPTHS]
    with urllib.request.urlopen(f"{URL}?{urllib.parse.urlencode(q)}", timeout=120) as r:
        layers = json.load(r)["properties"]["layers"]

    rows = []
    for layer in layers:
        um = layer["unit_measure"]
        for d in layer["depths"]:
            v = d["values"]["mean"]
            rows.append({
                "lat": a.lat, "lon": a.lon,
                "depth_top_cm": d["range"]["top_depth"],
                "depth_bottom_cm": d["range"]["bottom_depth"],
                "parameter": RENAME[layer["name"]],
                "value": None if v is None else v / um["d_factor"],  # mapped -> conventional units
                "unit": um["target_units"],
            })
    df = pd.DataFrame(rows).sort_values(["parameter", "depth_top_cm"]).reset_index(drop=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} rows -> {a.out}")
    print(df.pivot(index="parameter", columns="depth_top_cm", values="value").round(2))


if __name__ == "__main__":
    main()
