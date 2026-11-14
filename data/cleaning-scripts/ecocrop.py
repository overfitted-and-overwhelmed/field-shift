"""Clean the ECOCROP extract (ecocrop_selected_crops.csv).

Steps:
- drop columns that are empty for all crops
- strip whitespace, fix stray characters (e.g. "high (>10 dS/m))")
- add an English crop name (crop_en), drop IDs/taxonomy/German name (DROP_COLS)
- ensure numeric parameter columns are numeric
- reshape to long format (crop_en, variable, value), dropping empty values
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC = DATA_DIR / "base-data" / "ecocrop" / "ecocrop_selected_crops.csv"
OUT_DIR = DATA_DIR / "processed" / SRC.parent.name

CROP_EN = {
    "Glycine max": "Soybean",
    "Helianthus annuus": "Sunflower",
    "Secale cereale": "Rye",
    "Sorghum bicolor": "Sorghum",
    "Triticum aestivum": "Winter wheat",
    "Zea mays": "Maize",
}

DROP_COLS = [
    "crop_de",
    "ecocrop_id",
    "scientific_name",
    "authority",
    "family",
    "ecocrop_code",
    "synonyms",
    "common_names",
    "notes",
    "sources",
]

NUMERIC_PREFIXES = (
    "temp_", "rain_", "latitude_", "altitude_", "soil_ph_",
    "killing_temp_", "crop_cycle_",
)


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(axis=1, how="all").drop_duplicates()

    text_cols = df.select_dtypes(include=["object", "string"]).columns
    df[text_cols] = df[text_cols].apply(
        lambda s: s.str.strip()
        .str.replace(r"\s+", " ", regex=True)
        .str.replace("))", ")", regex=False)
        .replace("", pd.NA)
    )

    # crop_en is derived from scientific_name, so add it before dropping
    df.insert(0, "crop_en", df["scientific_name"].map(CROP_EN))
    df = df.drop(columns=DROP_COLS)

    for col in df.columns:
        if col.startswith(NUMERIC_PREFIXES):
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.reset_index(drop=True)


def to_long(df: pd.DataFrame) -> pd.DataFrame:
    """One row per crop and parameter: crop_en, variable, value."""
    long = df.melt(id_vars="crop_en", var_name="variable", value_name="value")
    long = long.dropna(subset=["value"])
    return long.sort_values(["crop_en", "variable"]).reset_index(drop=True)


def main() -> None:
    raw = pd.read_csv(SRC)
    df = to_long(clean(raw))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "ecocrop_clean.csv"
    df.to_csv(out, index=False)
    print(f"ecocrop: {raw.shape} -> {df.shape}  ({out})")


if __name__ == "__main__":
    main()
