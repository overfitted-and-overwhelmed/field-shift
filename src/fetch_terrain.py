"""Elevation and slope for one point from the USGS 3DEP OpenTopoData (NED 10 m).

Slope = Horn's method on a 3x3 grid of elevations around the point (spacing 30 m).
Usage: uv run python src/fetch_terrain.py --lat 38.025110 --lon -101.126084
"""
import argparse
import json
import math
import time
import urllib.request
from pathlib import Path

import pandas as pd

API = "https://api.opentopodata.org/v1/ned10m"  # USGS 3DEP 1/3 arc-second (~10 m), CONUS
STEP_M = 30.0


def elevations(points, tries=5):
    """All points in a single request; returns elevations in the same order."""
    loc = "|".join(f"{la},{lo}" for la, lo in points)
    url = f"{API}?locations={loc}&interpolation=bilinear"
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return [x["elevation"] for x in json.load(r)["results"]]
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(2 ** attempt)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--out", type=Path, default=Path("data/processed/terrain_long.csv"))
    a = p.parse_args()

    dlat = STEP_M / 111_320
    dlon = STEP_M / (111_320 * math.cos(math.radians(a.lat)))
    pts = [(a.lat + i * dlat, a.lon + j * dlon) for i in (1, 0, -1) for j in (-1, 0, 1)]  # rows N->S
    e = elevations(pts)
    z = [e[0:3], e[3:6], e[6:9]]
    (a1, b1, c1), (d1, e1, f1), (g1, h1, i1) = z
    dzdx = ((c1 + 2 * f1 + i1) - (a1 + 2 * d1 + g1)) / (8 * STEP_M)
    dzdy = ((g1 + 2 * h1 + i1) - (a1 + 2 * b1 + c1)) / (8 * STEP_M)
    slope_pct = math.hypot(dzdx, dzdy) * 100

    df = pd.DataFrame([("elevation", z[1][1], "m"), ("slope", round(slope_pct, 3), "%")],
                      columns=["parameter", "value", "unit"])
    df.insert(0, "lon", a.lon)
    df.insert(0, "lat", a.lat)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    print(df, "\nelevation grid:", z)


if __name__ == "__main__":
    main()
