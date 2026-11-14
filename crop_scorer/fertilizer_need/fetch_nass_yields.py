"""Reference yields for the fertilizer-need model (plan: crop_scorer/fertilizer-need-plan.md, Sub-Task 1).

Downloads Kansas (state level) survey yields from USDA NASS Quick Stats for 1991-2025 and averages them per crop and production practice.
Needs a free API key (https://quickstats.nass.usda.gov/api) as a line  NASS_API_KEY=<key>  in `.env` at the repo root (git-ignored).

Run from the repo root:
    uv run python crop_scorer/fertilizer_need/fetch_nass_yields.py                 # fetch and write both files
    uv run python crop_scorer/fertilizer_need/fetch_nass_yields.py --from-csv FILE # only the averaging step, on a saved raw file (no key)

Writes to data/:
    nass_yields_kansas_raw.csv        every downloaded annual yield row (final estimates only, no forecasts)
    nass_reference_yields.csv         per crop and practice: mean, number of years, first/last year, t/ha, query parameters, date
The plan asks for NON-IRRIGATED. The other practices are kept so the team can decide on a fallback where years or a crop are missing
(plan, open question 1). Nothing is estimated here: if a crop has no non-irrigated years, its row says so.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "nass_yields_kansas_raw.csv"
REF = ROOT / "data" / "nass_reference_yields.csv"
UNITS = ROOT / "data" / "crop_unit_conversion.csv"
API = "https://quickstats.nass.usda.gov/api/api_GET/"
STATE, YEAR_FROM, YEAR_TO = "KS", 1991, 2025
PRACTICES = ["NON-IRRIGATED", "IRRIGATED", "ALL PRODUCTION PRACTICES"]
# scorer crop -> Quick Stats selection. Grain yields only (corn/sorghum also publish silage in tons per acre).
CROPS = {
    "corn": {"commodity_desc": "CORN", "class_desc": "ALL CLASSES", "unit_desc": "BU / ACRE"},
    "sorghum": {"commodity_desc": "SORGHUM", "class_desc": "ALL CLASSES", "unit_desc": "BU / ACRE"},
    "soybean": {"commodity_desc": "SOYBEANS", "class_desc": "ALL CLASSES", "unit_desc": "BU / ACRE"},
    "sunflower": {"commodity_desc": "SUNFLOWER", "class_desc": "ALL CLASSES", "unit_desc": "LB / ACRE"},
    "winter_wheat": {"commodity_desc": "WHEAT", "class_desc": "WINTER", "unit_desc": "BU / ACRE"},
}
KEEP = ["year", "source_desc", "agg_level_desc", "state_alpha", "commodity_desc", "class_desc", "prodn_practice_desc", "util_practice_desc",
        "statisticcat_desc", "unit_desc", "short_desc", "freq_desc", "reference_period_desc", "Value"]


def api_key() -> str:
    key = os.environ.get("NASS_API_KEY", "")
    env = ROOT / ".env"
    if not key and env.is_file():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "NASS_API_KEY":
                key = value.strip().strip("'\"")
    if not key:
        raise SystemExit("NASS_API_KEY missing: add the line  NASS_API_KEY=<your key>  to .env in the repo root")
    return key


def query(key: str, **params) -> list[dict]:
    url = API + "?" + urllib.parse.urlencode({"key": key, "format": "JSON", **params})
    try:
        with urllib.request.urlopen(url, timeout=120) as r:
            return json.load(r)["data"]
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise SystemExit("Quick Stats rejected the API key (401). Check NASS_API_KEY in .env")
        if e.code == 400:  # Quick Stats answers 400 when a query matches no rows
            print(f"  no rows: {params}")
            return []
        raise SystemExit(f"Quick Stats error {e.code} for {params}: {e.read().decode(errors='replace')[:300]}")


def fetch() -> pd.DataFrame:
    key = api_key()
    rows = []
    for crop, sel in CROPS.items():
        for practice in PRACTICES:
            got = query(key, source_desc="SURVEY", statisticcat_desc="YIELD", agg_level_desc="STATE", state_alpha=STATE, freq_desc="ANNUAL",
                        reference_period_desc="YEAR", prodn_practice_desc=practice, year__GE=YEAR_FROM, year__LE=YEAR_TO, **sel)
            print(f"{crop:13s} {practice:26s} {len(got)} rows")
            rows += got
    df = pd.DataFrame(rows)
    return df[[c for c in KEEP if c in df.columns]] if len(df) else df


def aggregate(raw: pd.DataFrame) -> pd.DataFrame:
    """Mean yield per crop and practice over the years that have a value. Withheld values ('(D)') are not years."""
    units = pd.read_csv(UNITS).set_index("crop") if UNITS.exists() else None
    raw = raw.copy()
    raw["value_num"] = pd.to_numeric(raw["Value"].astype(str).str.replace(",", ""), errors="coerce")
    raw = raw[raw["year"].between(YEAR_FROM, YEAR_TO)]  # only the requested period
    today = date.today().isoformat()
    out = []
    for crop, sel in CROPS.items():
        for practice in PRACTICES:
            s = raw[(raw["commodity_desc"] == sel["commodity_desc"]) & (raw["class_desc"] == sel["class_desc"]) & (raw["unit_desc"] == sel["unit_desc"])
                    & (raw["prodn_practice_desc"] == practice) & (raw["agg_level_desc"] == "STATE") & (raw["reference_period_desc"] == "YEAR")]
            s = s.dropna(subset=["value_num"]).drop_duplicates("year")
            n = len(s)
            mean = round(s["value_num"].mean(), 2) if n else None
            row = {"crop": crop, "state": STATE, "practice": practice, "n_years": n,
                   "year_first": int(s["year"].min()) if n else None, "year_last": int(s["year"].max()) if n else None,
                   "years_requested": f"{YEAR_FROM}-{YEAR_TO}", "mean_yield": mean, "unit": sel["unit_desc"],
                   "mean_yield_t_per_ha": round(mean * units.loc[crop, "t_per_ha_per_yield_unit"], 3) if (n and units is not None) else None,
                   "moisture_basis_pct": units.loc[crop, "moisture_basis_pct"] if units is not None else None,
                   "source": "USDA NASS Quick Stats (survey), https://quickstats.nass.usda.gov/api",
                   "query": "source_desc=SURVEY; statisticcat_desc=YIELD; agg_level_desc=STATE; state_alpha=KS; freq_desc=ANNUAL; reference_period_desc=YEAR; "
                            + "; ".join(f"{k}={v}" for k, v in sel.items()) + f"; prodn_practice_desc={practice}; year={YEAR_FROM}..{YEAR_TO}",
                   "retrieved": today, "kind": "data",
                   "note": "" if n else "no values: decide a fallback with the team (plan, open question 1). Not estimated here."}
            out.append(row)
    df = pd.DataFrame(out)
    for c in ("year_first", "year_last"):
        df[c] = df[c].astype("Int64")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-csv", help="average a saved raw file instead of calling the API (writes only the reference table to stdout)")
    a = ap.parse_args()
    if a.from_csv:
        print(aggregate(pd.read_csv(a.from_csv)).drop(columns=["source", "query", "retrieved"]).to_string())
        return
    raw = fetch()
    if raw.empty:
        sys.exit("No rows returned.")
    raw.to_csv(RAW, index=False)
    ref = aggregate(raw)
    ref.to_csv(REF, index=False)
    print(f"wrote {len(raw)} rows to {RAW} and {len(ref)} rows to {REF}")


if __name__ == "__main__":
    main()
