"""Load the literature tables (previous-crop effects, crop units, cover crop effects) and save them to processed/crop_data/literature/.

The files are compiled by hand from the cited sources and already in long format, so they are only passed through.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = DATA_DIR / "base-data" / "literature"
OUT_DIR = DATA_DIR / "processed" / "crop_data" / SRC_DIR.name

# source file -> cleaned file
FILES = {
    "rotation_effects_long.csv": "rotation_effects_clean.csv",
    "crop_units.csv": "crop_units_clean.csv",
    "cover_crop_effects.csv": "cover_crop_effects_clean.csv",
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for src, dst in FILES.items():
        df = pd.read_csv(SRC_DIR / src, dtype=str, keep_default_na=False)  # keep values as written (no 5 -> 5.0)
        df.to_csv(OUT_DIR / dst, index=False)
        print(f"literature: {df.shape}  ({OUT_DIR / dst})")


if __name__ == "__main__":
    main()
