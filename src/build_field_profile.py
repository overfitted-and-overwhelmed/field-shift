"""Build the static field profile (JSON, schema 0.2 style) from the processed CSVs.

Static data (soil, terrain, location, constraints) lives in the profile; the "variables" block only
*describes* the time series files (unit, freq, source, resolution, start, end) - the values stay in CSV.

Usage: uv run python src/build_field_profile.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

PROC = Path("data/processed")
FIELD_ID = "ks-kearny-01"
STATE, COUNTY, COUNTY_FIPS = "KS", "Kearny", "20093"  # county looked up via FCC census API


def overlap(h, top, bottom):
    """Thickness [cm] of each horizon inside the depth window [top, bottom]."""
    return (np.minimum(h.depth_bottom_cm, bottom) - np.maximum(h.depth_top_cm, top)).clip(lower=0)


def weighted(h, col, top, bottom):
    t = overlap(h, top, bottom)
    return float((h[col] * t).sum() / t.sum())


def soil_block():
    long = pd.read_csv(PROC / "soil_ssurgo_long.csv")
    h = long.pivot_table(index=["depth_top_cm", "depth_bottom_cm"], columns="parameter", values="value").reset_index()
    meta = pd.read_csv(PROC / "soil_ssurgo_meta.csv").set_index("attribute")["value"]
    awc_mm = float((h.available_water_capacity * overlap(h, 0, 100)).sum() * 10)  # cm/cm * cm * 10 = mm
    return {
        "texture": str(meta["texture_0_cm"]).lower(),
        "water_capacity_mm": round(awc_mm),                                    # plant-available water, 0-100 cm
        "organic_matter_pct": round(weighted(h, "organic_matter", 0, 30), 2),  # 0-30 cm, thickness-weighted
        "clay_pct": round(weighted(h, "clay_content", 0, 30), 1),
        "silt_pct": round(weighted(h, "silt_content", 0, 30), 1),
        "sand_pct": round(weighted(h, "sand_content", 0, 30), 1),
        "ph": round(weighted(h, "ph_water", 0, 30), 2),
        "bulk_density_g_cm3": round(weighted(h, "bulk_density", 0, 30), 2),
        "hydrologic_group": str(meta["hydrologic_group"]),
        "drainage_class": str(meta["drainage_class"]).lower(),
        "irrigated_capability_class": int(meta["irrigated_capability_class"]),
        "nonirrigated_capability_class": int(meta["nonirrigated_capability_class"]),
        "source": f"USDA SSURGO, dominant component {meta['component']} ({meta['component_share']}%)",
    }


# description of the time series variables: file -> (freq, source, resolution)
SERIES = {
    "power_daily_long.csv": ("date", "daily", "NASA POWER", "~50 km"),
    "features_daily_long.csv": ("date", "daily", "derived from NASA POWER", "~50 km"),
    "features_annual_long.csv": ("year", "annual", "derived from NASA POWER", "~50 km"),
}


def method_note(name):
    if name == "reference_evapotranspiration":
        return " (FAO-56 Penman-Monteith)"
    if name.endswith("_anomaly"):
        return " (anomaly vs 1991-2020 daily climatology)"
    return ""


def variables_block():
    out = {}
    for fname, (key, freq, source, res) in SERIES.items():
        p = PROC / fname
        if not p.exists():
            continue
        d = pd.read_csv(p).dropna(subset=["value"])
        for name, g in d.groupby("parameter"):
            lo, hi = g[key].min(), g[key].max()
            if key == "year":
                lo, hi = f"{lo}-01-01", f"{hi}-12-31"
            out[name] = {"unit": g["unit"].iloc[0], "freq": freq, "source": source + method_note(name), "resolution": res,
                         "start": str(lo)[:10], "end": str(hi)[:10], "file": fname}
    return out


def fmt(o):
    """Compact JSON in the style of the example: small objects inline, one variable per line."""
    inline = lambda x: json.dumps(x, ensure_ascii=False)
    lines = ["{"]
    items = list(o.items())
    for i, (k, v) in enumerate(items):
        comma = "," if i < len(items) - 1 else ""
        if k == "variables":
            lines.append('')
            lines.append('  "variables": {')
            vs = list(v.items())
            for j, (vk, vv) in enumerate(vs):
                lines.append(f'    {inline(vk)}: {inline(vv)}{"," if j < len(vs) - 1 else ""}')
            lines.append(f"  }}{comma}")
        else:
            lines.append(f"  {inline(k)}: {inline(v)}{comma}")
    lines.append("}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    pw = pd.read_csv(PROC / "power_daily_long.csv", usecols=["lat", "lon"]).iloc[0]
    terr = pd.read_csv(PROC / "terrain_long.csv").set_index("parameter")["value"]
    profile = {
        "schema_version": "0.2",
        "field_id": FIELD_ID,
        "location": {"lat": round(float(pw.lat), 6), "lon": round(float(pw.lon), 6), "area_ha": None,
                     "state": STATE, "county": COUNTY, "county_fips": COUNTY_FIPS},
        "terrain": {"elevation_m": round(float(terr["elevation"])), "slope_pct": round(float(terr["slope"]), 2),
                    "source": "USGS 3DEP/NED 10 m via OpenTopoData"},
        "soil": soil_block(),
        "constraints": {"irrigated": None, "excluded_crops": []},  # irrigated: unknown, needs field knowledge
        "variables": variables_block(),
    }
    out = PROC / "field_profile.json"
    out.write_text(fmt(profile))
    json.loads(out.read_text())  # must be valid JSON
    print(out.read_text())
