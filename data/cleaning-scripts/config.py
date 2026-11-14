"""Central configuration for all cleaning scripts.

Edit DATASETS to change which files end up in which output folder. Nothing else needs to change.

RULE: SOURCE_DIR (z_processed) is READ-ONLY. No script may write, move, rename or delete anything in it.
Outputs are always per-file copies below OUTPUT_ROOT.
"""
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1]            # .../data
SOURCE_DIR = DATA_DIR / "base-data" / "z_processed"        # READ-ONLY input
OUTPUT_ROOT = DATA_DIR / "processed"                       # outputs go to OUTPUT_ROOT/<dataset name>/

# dataset name (= output folder) -> files taken from SOURCE_DIR.
# Add or remove file names here; to switch a file off, comment its line out.
DATASETS = {
    "climate_data": [
        "power_daily_long.csv",       # cleaned NASA POWER time series
        "features_daily_long.csv",    # daily features (ET0, balances, rolling sums, anomalies)
        "features_annual_long.csv",   # annual agro-climate indicators
        "field_profile.json",         # static field profile
        # "soil_ssurgo_long.csv",
        # "soil_ssurgo_meta.csv",
        # "terrain_long.csv",
    ],
}
