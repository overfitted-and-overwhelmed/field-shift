"""Download crop yields (Kearny County, KS) and Kansas crop prices from USDA NASS Quick Stats.

Needs a free API key (https://quickstats.nass.usda.gov/api) in the file `.env` at the repo root:

    NASS_API_KEY=your-key

`.env` is git-ignored, so the key never ends up in the repo.

Run from the repo root:
    uv run python data/fetch-scripts/quickstats.py

Writes the raw API rows to data/base-data/nass_quickstats/:
- yields_raw.csv  yields for county, agricultural district and state (fallbacks for missing county values)
- prices_raw.csv  Kansas prices received, marketing year
Clean them afterwards with data/cleaning-scripts/nass_quickstats.py.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "base-data" / "nass_quickstats"
API = "https://quickstats.nass.usda.gov/api/api_GET/"

STATE, COUNTY = "KS", "KEARNY"
YIELD_FROM, PRICE_FROM = 2010, 2015
COMMODITIES = ["CORN", "SORGHUM", "WHEAT", "SOYBEANS", "SUNFLOWER"]
KEEP = [
    "year", "source_desc", "agg_level_desc", "state_alpha", "asd_code", "asd_desc", "county_name",
    "commodity_desc", "class_desc", "prodn_practice_desc", "util_practice_desc", "statisticcat_desc",
    "unit_desc", "short_desc", "freq_desc", "reference_period_desc", "Value", "CV (%)",
]


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
        body = e.read().decode(errors="replace")
        if e.code == 401:
            raise SystemExit("Quick Stats rejected the API key (401). Check NASS_API_KEY in .env")
        if e.code == 400:  # Quick Stats answers 400 when a query matches no rows
            print(f"  no rows: {params}")
            return []
        raise SystemExit(f"Quick Stats error {e.code} for {params}: {body[:300]}")


def to_frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    return df[[c for c in KEEP if c in df.columns]] if len(df) else df


def main() -> None:
    key = api_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = {"source_desc": "SURVEY", "statisticcat_desc": "YIELD", "state_alpha": STATE}

    county = []
    for c in COMMODITIES:
        rows = query(key, **base, commodity_desc=c, agg_level_desc="COUNTY", county_name=COUNTY, year__GE=YIELD_FROM)
        print(f"county {c}: {len(rows)} rows")
        county += rows
    # the county's agricultural district is the first fallback; its code comes with the county rows
    asd = next((r["asd_code"] for r in county if r.get("asd_code")), None)

    district, state = [], []
    for c in COMMODITIES:
        if asd:
            rows = query(key, **base, commodity_desc=c, agg_level_desc="AGRICULTURAL DISTRICT", asd_code=asd, year__GE=YIELD_FROM)
            print(f"district {asd} {c}: {len(rows)} rows")
            district += rows
        rows = query(key, **base, commodity_desc=c, agg_level_desc="STATE", year__GE=YIELD_FROM)
        print(f"state {c}: {len(rows)} rows")
        state += rows

    yields = to_frame(county + district + state)
    yields.to_csv(OUT_DIR / "yields_raw.csv", index=False)

    prices = []
    for c in COMMODITIES:
        rows = query(key, source_desc="SURVEY", statisticcat_desc="PRICE RECEIVED", agg_level_desc="STATE",
                     state_alpha=STATE, commodity_desc=c, freq_desc="ANNUAL", year__GE=PRICE_FROM)
        print(f"price {c}: {len(rows)} rows")
        prices += rows
    to_frame(prices).to_csv(OUT_DIR / "prices_raw.csv", index=False)
    print(f"saved {len(yields)} yield rows and {len(prices)} price rows to {OUT_DIR}")


if __name__ == "__main__":
    main()
