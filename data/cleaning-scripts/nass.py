"""Load the USDA NASS Kansas crop calendar and save it to processed/.

The file is already clean and in long format, so it is only passed through.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[1]
SRC = DATA_DIR / "base-data" / "nass" / "kansas_crop_calendar_long.csv"
OUT_DIR = DATA_DIR / "processed" / "crop_data" / SRC.parent.name


def main() -> None:
    df = pd.read_csv(SRC)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "kansas_crop_calendar_clean.csv"
    df.to_csv(out, index=False)
    print(f"nass: {df.shape}  ({out})")


if __name__ == "__main__":
    main()
