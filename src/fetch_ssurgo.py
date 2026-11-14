"""Fetch USDA SSURGO soil data for one point (Soil Data Access REST API), long format.

Dominant component of the map unit at the point; horizon properties by depth.
Usage: uv run python src/fetch_ssurgo.py --lat 38.025110 --lon -101.126084
"""
import argparse
import json
import urllib.request
from pathlib import Path

import pandas as pd

URL = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"


def sda(query: str) -> pd.DataFrame:
    body = json.dumps({"format": "JSON+COLUMNNAME", "query": query}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        table = json.load(r).get("Table")
    if not table:  # SDA returns no "Table" key for an empty result
        return pd.DataFrame()
    return pd.DataFrame(table[1:], columns=table[0])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lon", type=float, required=True)
    p.add_argument("--out", type=Path, default=Path("data/processed/soil_ssurgo_long.csv"))
    a = p.parse_args()
    mu = f"SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({a.lon} {a.lat})')"

    comp = sda(f"""SELECT c.cokey, c.compname, c.comppct_r, c.slope_r, c.hydgrp, c.drainagecl,
        c.irrcapcl, c.nirrcapcl, c.taxclname FROM component c
        WHERE c.mukey IN ({mu}) ORDER BY c.comppct_r DESC""")
    print(comp.to_string())
    top = comp.iloc[0]

    hz = sda(f"""SELECT h.hzname, h.hzdept_r, h.hzdepb_r, h.sandtotal_r, h.silttotal_r, h.claytotal_r,
        h.ph1to1h2o_r, h.om_r, h.awc_r, h.ksat_r, h.dbthirdbar_r, h.cec7_r, h.caco3_r, h.ec_r
        FROM chorizon h WHERE h.cokey = {top.cokey} ORDER BY h.hzdept_r""")
    tex = sda(f"""SELECT h.hzdept_r, g.texdesc FROM chorizon h
        JOIN chtexturegrp g ON g.chkey = h.chkey AND g.rvindicator = 'Yes'
        WHERE h.cokey = {top.cokey}""")
    res = sda(f"SELECT reskind, resdept_r FROM corestrictions WHERE cokey = {top.cokey}")
    print(hz.to_string(), tex.to_string(), res.to_string(), sep="\n")

    names = {"sandtotal_r": ("sand_content", "%"), "silttotal_r": ("silt_content", "%"),
             "claytotal_r": ("clay_content", "%"), "ph1to1h2o_r": ("ph_water", "-"),
             "om_r": ("organic_matter", "%"), "awc_r": ("available_water_capacity", "cm/cm"),
             "ksat_r": ("saturated_conductivity", "um/s"), "dbthirdbar_r": ("bulk_density", "g/cm3"),
             "cec7_r": ("cation_exchange_capacity", "meq/100g"), "caco3_r": ("calcium_carbonate", "%"),
             "ec_r": ("electrical_conductivity", "dS/m")}
    rows = []
    for _, h in hz.iterrows():
        for col, (name, unit) in names.items():
            rows.append((h.hzdept_r, h.hzdepb_r, name, h[col], unit))
    df = pd.DataFrame(rows, columns=["depth_top_cm", "depth_bottom_cm", "parameter", "value", "unit"])
    df["value"] = pd.to_numeric(df["value"])
    df.insert(0, "lon", a.lon)
    df.insert(0, "lat", a.lat)
    df["component"] = top.compname
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(a.out, index=False)
    print(f"{len(df)} rows -> {a.out}")

    # categorical attributes (not numeric -> separate small file)
    meta = [("component", top.compname, ""), ("component_share", top.comppct_r, "%"),
            ("taxonomic_class", top.taxclname, ""), ("hydrologic_group", top.hydgrp, ""),
            ("drainage_class", top.drainagecl, ""),
            ("irrigated_capability_class", top.irrcapcl, "1-8"),
            ("nonirrigated_capability_class", top.nirrcapcl, "1-8"),
            ("restrictive_layer_depth_cm", res["resdept_r"].min() if len(res) else "none_within_200", "cm")]
    meta += [(f"texture_{int(r.hzdept_r)}_cm", r.texdesc, "") for r in tex.itertuples()]
    mdf = pd.DataFrame(meta, columns=["attribute", "value", "unit"])
    mdf.insert(0, "lon", a.lon)
    mdf.insert(0, "lat", a.lat)
    mdf.to_csv(a.out.with_name("soil_ssurgo_meta.csv"), index=False)


if __name__ == "__main__":
    main()
