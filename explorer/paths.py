"""Where the explorer reads its input data.

All paths live here, so a restructure of data/ means changing one file, not every module.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"

NASS_CALENDAR = DATA_PROCESSED / "crop_data" / "nass" / "kansas_crop_calendar_clean.csv"
FIELD_PROFILE = DATA_PROCESSED / "climate_data" / "field_profile.json"
CLIMATE_ANNUAL = DATA_PROCESSED / "climate_data" / "features_annual_long.csv"
CDL_HISTORY = DATA_PROCESSED / "field_data" / "cdl" / "cdl_history_clean.csv"
NASS_EXPECTED_YIELD = DATA_PROCESSED / "crop_data" / "nass_quickstats" / "expected_yield_clean.csv"
NASS_YIELDS = DATA_PROCESSED / "crop_data" / "nass_quickstats" / "yields_clean.csv"
ROTATION_EFFECTS = DATA_PROCESSED / "crop_data" / "literature" / "rotation_effects_clean.csv"
# written by the scorer (crop_scorer/scoring/score_rotations.py); arrives with the scorer's merge into main
SCORER_SEASONS_BY_YEAR = DATA_PROCESSED / "rotation_scores" / "rotation_seasons_by_year.csv"
