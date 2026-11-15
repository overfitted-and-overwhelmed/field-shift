"""Clean the NRCS/KSSL soil lab export (soil-data/).

The export is split into many thematic tables keyed by pedon_key/layer_key,
each with a *_dict.csv describing its cryptic method-code columns.

Steps:
- skip empty tables and drop all-empty columns
- merge all layer tables into one wide table (one row per layer)
- join pedon + site info (location, county) onto each layer
- write a column dictionary (code -> analyte name, unit, source table)
"""

import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = DATA_DIR / "base-data" / "soil-data"
OUT_DIR = DATA_DIR / "processed" / SRC_DIR.name

LAYER_KEYS = ["pedon_key", "layer_key"]
LAYER_META = [
    "layer_sequence", "layer_field_label_1", "layer_field_label_2",
    "layer_field_label_3", "hzn_top", "hzn_bot", "hzn_desgn", "texture_description",
]


def read(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"pedon_key": "string", "layer_key": "string"})
    text_cols = df.select_dtypes(include=["object", "string"]).columns
    df[text_cols] = df[text_cols].apply(lambda s: s.str.strip().replace("", pd.NA))
    return df.dropna(axis=1, how="all")


def load_layer_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    merged: pd.DataFrame | None = None
    dict_rows = []
    for path in sorted(SRC_DIR.glob("*.csv")):
        if path.stem.endswith("_dict") or path.stem in {"site", "pedon"}:
            continue
        df = read(path)
        if df.empty or "layer_key" not in df:
            continue
        value_cols = [c for c in df.columns if c not in LAYER_KEYS + LAYER_META]
        if not value_cols:
            continue

        dict_path = SRC_DIR / f"{path.stem}_dict.csv"
        if dict_path.exists():
            d = pd.read_csv(dict_path).rename(columns={"method code (column header)": "column"})
            d = d[d["column"].isin(value_cols)].assign(source_table=path.stem)
            dict_rows.append(d)

        if merged is None:
            merged = df
        else:
            keep = LAYER_KEYS + [c for c in df.columns if c not in merged.columns]
            meta = [c for c in LAYER_META if c in df.columns and c not in merged.columns]
            merged = merged.merge(df[keep + meta], on=LAYER_KEYS, how="outer")

    col_dict = pd.concat(dict_rows, ignore_index=True) if dict_rows else pd.DataFrame()
    return merged, col_dict


# --- readable column names ---------------------------------------------------

# identifier / metadata columns without a *_dict.csv entry
FIXED_NAMES = {
    "user_site_id": "site_id",
    "user_pedon_id": "pedon_id",
    "cntrl_depth_to_top": "control_section_top_cm",
    "cntrl_depth_to_bot": "control_section_bottom_cm",
    "clyavg_d-1": "clay_avg_control_section_pct_wt",
    "wa0175_d-1_S": "weighted_avg_0p1_75mm_control_section_pct_wt",
    "wacltot_d-1_S": "weighted_avg_clay_control_section_pct_wt",
    "wavfg2_d-1_S": "weighted_avg_gt2mm_control_section_pct_vol",
    "state_admin_div": "state",
    "ssa": "soil_survey_area",
    "mlra": "major_land_resource_area",
    "hzn_top": "horizon_top_cm",
    "hzn_bot": "horizon_bottom_cm",
    "hzn_desgn": "horizon_designation",
}

UNIT_SUFFIX = {
    "% wt": "pct_wt",
    "% vol": "pct_vol",
    "%": "pct",
    "meq/100g": "meq_100g",
    "cmol(+)/kg": "cmol_kg",
    "g/cc": "g_cm3",
    "dS/m": "ds_m",
    "mm": "mm",
}


def snake(text: str) -> str:
    text = text.lower()
    text = re.sub(r",?\s*n prep\b", "", text)  # prep method goes into the suffix
    text = re.sub(r"(\d)\.(\d)", r"\1p\2", text)  # 0.1 -> 0p1
    text = text.replace("<", " lt ").replace(">", " gt ").replace("%", " pct ")
    text = text.replace("@", " at ").replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def readable_names(col_dict: pd.DataFrame) -> dict[str, str]:
    """Map method-code headers to snake_case '<analyte>_<unit>' names.

    The same analyte is often measured twice: by the new lab system (SSL)
    and the old one (CMS) -> suffix `_ssl` / `_cms`. If names still clash
    (e.g. two CEC runs), the run number from the code is appended.
    """
    d = col_dict.copy()
    d["base"] = [
        "_".join(filter(None, [snake(a), UNIT_SUFFIX.get(u, "")]))
        for a, u in zip(d["analyte_name"], d["unit_of_measure"])
    ]
    d["system"] = d["source_system"].str.contains("CMS").map({True: "cms", False: "ssl"})
    d["name"] = d["base"]

    clash = d["name"].duplicated(keep=False)
    d.loc[clash, "name"] = d["base"] + "_" + d["system"]

    clash = d["name"].duplicated(keep=False)
    run = d["column"].str.extract(r"_(\d+)_(?:SSL|CMS)_", expand=False)
    d.loc[clash, "name"] = d["name"] + "_run" + run

    return dict(zip(d["column"], d["name"]))


def main() -> None:
    layers, col_dict = load_layer_tables()

    for col in ["layer_sequence", "hzn_top", "hzn_bot"]:
        if col in layers:
            layers[col] = pd.to_numeric(layers[col], errors="coerce")
    layers = layers.dropna(axis=1, how="all")

    site = read(SRC_DIR / "site.csv").rename(
        columns={"latitude_decimal_degrees": "latitude", "longitude_decimal_degrees": "longitude"}
    )
    pedon = read(SRC_DIR / "pedon.csv")
    pedon_site = pedon.merge(site, on="user_site_id", how="left")

    df = pedon_site.merge(layers, on="pedon_key", how="right")
    df = df.sort_values(["pedon_key", "hzn_top"]).drop_duplicates().reset_index(drop=True)

    col_dict = col_dict[col_dict["column"].isin(df.columns)].drop_duplicates("column")

    names = {**readable_names(col_dict), **FIXED_NAMES}
    col_dict.insert(0, "name", col_dict["column"].map(names))
    df = df.rename(columns=names)
    pedon_site = pedon_site.rename(columns=names)
    assert df.columns.is_unique, df.columns[df.columns.duplicated()].tolist()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "soil_layers_clean.csv", index=False)
    pedon_site.to_csv(OUT_DIR / "soil_pedons_clean.csv", index=False)
    col_dict.to_csv(OUT_DIR / "soil_column_dict.csv", index=False)
    print(f"soil: {len(pedon_site)} pedons, layers {df.shape}, {len(col_dict)} documented columns ({OUT_DIR})")


if __name__ == "__main__":
    main()
