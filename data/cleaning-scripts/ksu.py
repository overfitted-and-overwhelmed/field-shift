"""Load the K-State MF2586 (2024) nitrogen tables and save them to processed/crop_data/ksu/.

The files are compiled by hand from the cited sources and already in long format, so they are only passed through.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = DATA_DIR / "base-data" / "ksu"
OUT_DIR = DATA_DIR / "processed" / "crop_data" / SRC_DIR.name

# source file -> cleaned file
FILES = {
    "ksu_mf2586_n_recommendations_long.csv": "ksu_n_recommendations_clean.csv",
    "ksu_mf2586_previous_crop_adjustments.csv": "ksu_previous_crop_adjustments_clean.csv",
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for src, dst in FILES.items():
        df = pd.read_csv(SRC_DIR / src, dtype=str, keep_default_na=False)  # keep values as written (no 5 -> 5.0)
        df.to_csv(OUT_DIR / dst, index=False)
        print(f"ksu: {df.shape}  ({OUT_DIR / dst})")


if __name__ == "__main__":
    main()
