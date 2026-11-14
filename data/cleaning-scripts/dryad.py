"""Clean the Dryad crop nutrient dataset (Combined_crop_data.csv).

Steps:
- drop empty columns (e.g. hs_code) and exact duplicate rows
- strip whitespace / collapse double spaces in text columns
- fill missing `item` from `original_crop`, then drop `original_crop`
- keep only US rows (country_iso3c == "United States"), drop unneeded columns (DROP_COLS)
- drop rows without a value, split `variable` into nutrient + unit
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC = DATA_DIR / "base-data" / "dryad" / "Combined_crop_data.csv"
OUT_DIR = DATA_DIR / "processed" / SRC.parent.name

COUNTRY = "United States"
DROP_COLS = [
    "reference_where_data_were_collated",
    "website_of_source_of_collated_data",
    "un_region_name",
    "un_sub_region_name",
    "un_intermediate_region_name",
    "primary_reference_of_dataset",
    "factor",
    "hs07_code",
    "hs12_code",
    "cpc_code",
    "latitude",
    "longitude",
    "original_crop_component",
    "item_code",
    "item_group_code",
    "item_group",
    "original_region",
]


def clean_text(s: pd.Series) -> pd.Series:
    return s.str.strip().str.replace(r"\s+", " ", regex=True).replace("", pd.NA)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all").drop_duplicates()
    df = df.drop(columns=DROP_COLS)

    text_cols = df.select_dtypes(include=["object", "string"]).columns
    df[text_cols] = df[text_cols].apply(clean_text)

    # use the harmonised FAO item name, fall back to the original crop name
    df["item"] = df["item"].fillna(df["original_crop"])
    df = df.drop(columns="original_crop")

    df = df[df["country_iso3c"] == COUNTRY]
    df = df.dropna(subset=["value"])
    df = df[df["value"] >= 0]

    # e.g. "N_pc_fresh" -> nutrient "N", unit "pc_fresh"
    parts = df["variable"].str.split("_", n=1, expand=True)
    df.insert(df.columns.get_loc("variable") + 1, "nutrient", parts[0])
    df.insert(df.columns.get_loc("nutrient") + 1, "unit", parts[1])

    return df.drop_duplicates().reset_index(drop=True)


def main() -> None:
    raw = pd.read_csv(SRC, low_memory=False)
    df = clean(raw)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "crop_nutrients_clean.csv"
    df.to_csv(out, index=False)
    print(f"dryad: {raw.shape} -> {df.shape}  ({out})")


if __name__ == "__main__":
    main()
