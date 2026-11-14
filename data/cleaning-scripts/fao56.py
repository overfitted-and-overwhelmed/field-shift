"""Clean FAO-56 Table 11 (stage lengths) and Table 12 (Kc values).

Raw cells mix numbers with ranges ("0.70-0.90"), alternatives ("50/30")
and placeholders ("var", "--"). Each such column is split into
`<col>_min`, `<col>_max` and `<col>` (midpoint), all numeric.

- Both tables: drop the `footnotes` column.
- Table 11: keep only rows whose `region` refers to the USA
  (incl. US states such as "Calif." or "Idaho").
- Both tables are reshaped to long format (id columns + variable, value):
  Table 11: group, crop, variant, plant_date, region
  Table 12: group, crop, variant, kc_ini_source
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = DATA_DIR / "base-data" / "fao56"
OUT_DIR = DATA_DIR / "processed" / "crop_data" / SRC_DIR.name

MISSING = {"var", "--", "-", ""}

# region entries that mention the USA or a US state
US_REGION_PATTERN = r"USA|Central USA|Calif|Texas|Arizona|Idaho|Utah|Florida|Hawaii"


def split_range(s: pd.Series) -> pd.DataFrame:
    """'0.70-0.90' / '50/30' / '40' / 'var' -> min, max, mid (floats)."""
    s = s.astype("string").str.strip()
    s = s.mask(s.isin(MISSING))
    parts = s.str.split(r"\s*[-/]\s*", expand=True, regex=True)
    nums = parts.apply(pd.to_numeric, errors="coerce")
    lo, hi = nums.min(axis=1), nums.max(axis=1)
    return pd.DataFrame({"min": lo, "max": hi, "mid": (lo + hi) / 2})


def expand_numeric(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for col in cols:
        r = split_range(df[col])
        pos = df.columns.get_loc(col)
        df = df.drop(columns=col)
        df.insert(pos, f"{col}_max", r["max"])
        df.insert(pos, f"{col}_min", r["min"])
        df.insert(pos, col, r["mid"])
    return df


def clean_common(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop(columns="footnotes")
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    df[text_cols] = df[text_cols].apply(
        lambda s: s.str.strip().str.replace(r"\s+", " ", regex=True)
        .str.replace(r"\s+,", ",", regex=True).replace("", pd.NA)
    )
    return df.drop_duplicates().reset_index(drop=True)


def clean_stage_lengths(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_common(df)
    df = df[df["region"].str.contains(US_REGION_PATTERN, na=False)]
    df = expand_numeric(df, ["L_ini", "L_dev", "L_mid", "L_late", "L_total"])
    id_cols = ["group", "crop", "variant", "plant_date", "region"]
    long = df.melt(id_vars=id_cols, var_name="variable", value_name="value")
    long = long.dropna(subset=["value"])
    return long.sort_values(["group", "crop", "region", "plant_date", "variable"]).reset_index(drop=True)


def clean_kc(df: pd.DataFrame) -> pd.DataFrame:
    df = clean_common(df)
    df = expand_numeric(df, ["kc_ini", "kc_mid", "kc_end", "max_height_m"])
    id_cols = ["group", "crop", "variant", "kc_ini_source"]
    long = df.melt(id_vars=id_cols, var_name="variable", value_name="value")
    long = long.dropna(subset=["value"])
    return long.sort_values(["group", "crop", "variant", "variable"]).reset_index(drop=True)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = {
        "fao56_table11_stage_lengths": clean_stage_lengths,
        "fao56_table12_kc": clean_kc,
    }
    for name, fn in jobs.items():
        raw = pd.read_csv(SRC_DIR / f"{name}.csv")
        df = fn(raw)
        out = OUT_DIR / f"{name}_clean.csv"
        df.to_csv(out, index=False)
        print(f"fao56 {name}: {raw.shape} -> {df.shape}  ({out})")


if __name__ == "__main__":
    main()
