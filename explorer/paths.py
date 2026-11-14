"""Where the explorer reads its input data.

All paths live here, so a restructure of data/ means changing one file, not every module.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

NASS_CALENDAR = DATA_PROCESSED / "crop_data" / "nass" / "kansas_crop_calendar_clean.csv"
