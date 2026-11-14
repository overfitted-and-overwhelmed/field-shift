"""Clean the USDA NASS Quick Stats download (yields, prices) and derive expected yields.

Input:  base-data/nass_quickstats/yields_raw.csv, prices_raw.csv (from data/fetch-scripts/quickstats.py)
Output: processed/crop_data/nass_quickstats/
- yields_clean.csv          crop, practice, level, area, year, value, unit
- expected_yield_clean.csv  per crop and practice: 1.05 x mean of the last 5 available years (K-State MF2586),
                            taken from the most local level that has at least 3 of the last 10 years
- prices_clean.csv          Kansas prices received, marketing year

Steps:
- keep grain yields of our crops; withheld values like "(D)" become empty
- crop IDs follow the NASS calendar: corn, sorghum, winter_wheat, soybean, sunflower
- practices: irrigated, non_irrigated, all (other NASS practice splits are dropped)
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = DATA_DIR / "base-data" / "nass_quickstats"
OUT_DIR = DATA_DIR / "processed" / "crop_data" / SRC_DIR.name

PRACTICE = {"IRRIGATED": "irrigated", "NON-IRRIGATED": "non_irrigated", "ALL PRODUCTION PRACTICES": "all"}
LEVEL = {"COUNTY": "county", "AGRICULTURAL DISTRICT": "district", "STATE": "state"}
LEVEL_ORDER = ["county", "district", "state"]


def crop_id(r: pd.Series) -> str | None:
    c, cls, util = r["commodity_desc"], r.get("class_desc"), r.get("util_practice_desc")
    if c == "CORN" and util == "GRAIN":
        return "corn"
    if c == "SORGHUM" and util == "GRAIN":
        return "sorghum"
    if c == "WHEAT" and cls == "WINTER":
        return "winter_wheat"
    if c == "SOYBEANS":
        return "soybean"
    if c == "SUNFLOWER" and cls == "ALL CLASSES":
        return "sunflower"
    return None


def to_number(s: pd.Series) -> pd.Series:
    # "(D)" withheld, "(Z)" less than half the unit, "(NA)" not available -> empty
    return pd.to_numeric(s.astype(str).str.replace(",", "").str.strip(), errors="coerce")


def clean_yields(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["crop"] = df.apply(crop_id, axis=1)
    df["practice"] = df["prodn_practice_desc"].map(PRACTICE)
    df["level"] = df["agg_level_desc"].map(LEVEL)
    df = df[df["crop"].notna() & df["practice"].notna() & df["level"].notna()]
    df = df[df["unit_desc"].isin(["BU / ACRE", "LB / ACRE"])]
    df["area"] = df["county_name"].where(df["level"] == "county", df["asd_desc"].where(df["level"] == "district", df["state_alpha"]))
    df["value"] = to_number(df["Value"])
    out = df[["crop", "practice", "level", "area", "year", "value", "unit_desc"]].rename(columns={"unit_desc": "unit"})
    return out.drop_duplicates().sort_values(["crop", "practice", "level", "year"]).reset_index(drop=True)


def expected_yields(y: pd.DataFrame) -> pd.DataFrame:
    rows = []
    last = y["year"].max()
    for (crop, practice), g in y.dropna(subset=["value"]).groupby(["crop", "practice"]):
        for level in LEVEL_ORDER:
            recent = g[(g["level"] == level) & (g["year"] > last - 10)].sort_values("year")
            if len(recent) >= 3:
                use = recent.tail(5)
                mean = use["value"].mean()
                rows.append({
                    "crop": crop, "practice": practice, "level_used": level, "area": use["area"].iloc[0],
                    "years": f"{use['year'].min()}-{use['year'].max()}", "n_years": len(use),
                    "mean_yield": round(mean, 1), "expected_yield": round(1.05 * mean, 1), "unit": use["unit"].iloc[0],
                    "method": "1.05 x mean of last 5 available years (K-State MF2586)",
                })
                break
    return pd.DataFrame(rows)


def clean_prices(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df = df[df["reference_period_desc"] == "MARKETING YEAR"]
    df["crop"] = df["commodity_desc"].map({"CORN": "corn", "SORGHUM": "sorghum", "WHEAT": "winter_wheat", "SOYBEANS": "soybean", "SUNFLOWER": "sunflower"})
    df = df[df["crop"].notna() & df["class_desc"].isin(["ALL CLASSES", "WINTER"])]
    # winter wheat: prefer the WINTER class price, otherwise all classes
    df = df.assign(_pref=(df["class_desc"] != "WINTER").astype(int)).sort_values(["crop", "year", "_pref"])
    df = df.drop_duplicates(["crop", "year"])
    df["value"] = to_number(df["Value"])
    out = df[["crop", "year", "value", "unit_desc", "class_desc"]].rename(columns={"unit_desc": "unit", "class_desc": "class"})
    return out.sort_values(["crop", "year"]).reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    y = clean_yields(pd.read_csv(SRC_DIR / "yields_raw.csv"))
    y.to_csv(OUT_DIR / "yields_clean.csv", index=False)
    ey = expected_yields(y)
    ey.to_csv(OUT_DIR / "expected_yield_clean.csv", index=False)
    p = clean_prices(pd.read_csv(SRC_DIR / "prices_raw.csv"))
    p.to_csv(OUT_DIR / "prices_clean.csv", index=False)
    print(f"nass_quickstats: {len(y)} yields, {len(ey)} expected yields, {len(p)} prices ({OUT_DIR})")
    print(ey[["crop", "practice", "level_used", "years", "expected_yield", "unit"]].to_string(index=False))


if __name__ == "__main__":
    main()
