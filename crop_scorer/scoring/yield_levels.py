"""Mean NASS yield per crop with full irrigation and rain-fed, in NASS units (bu/acre, sunflower lb/acre).

One source for the N need (scorer, K-State expected yield) and the yields shown by the explorer (explorer/yields.py),
so both refer to the same yield level. Corn, winter wheat, soybean: NASS irrigated / non-irrigated means
(expected_yield_clean.csv). Sorghum and sunflower have no NASS split by irrigation, so their levels are derived.
"""

from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd

from crop_scorer.water_usage.water_usage import REPO

EXPECTED_YIELD_FILE = REPO / "data/processed/crop_data/nass_quickstats/expected_yield_clean.csv"

# NASS splits sorghum by irrigation only until 2009 and sunflower never.
# shortcut: SW Kansas sorghum, Quick Stats district SOUTHWEST, 2004-2007 and 2009 (2008 not published),
# fetched 2026-11-15 outside the data pipeline. Move into nass_quickstats when the fetch covers years < 2010.
SORGHUM_SW_2004_2009 = {
    "irrigated": [108, 99, 89, 101, 105],
    "non_irrigated": [51, 70, 43, 62, 79],
    "all": [61, 75, 51, 67, 83],
}


@cache
def yield_levels(path: Path = EXPECTED_YIELD_FILE) -> dict[str, tuple[float, float, bool]]:
    """crop -> (mean yield full irrigation, mean yield rain-fed, derived); derived = not a NASS value of that practice."""
    nass = pd.read_csv(path).set_index(["crop", "practice"])

    def mean_yield(crop: str, practice: str) -> float:
        return float(nass.loc[(crop, practice), "mean_yield"])

    levels = {crop: (mean_yield(crop, "irrigated"), mean_yield(crop, "non_irrigated"), False)
              for crop in ("corn", "winter_wheat", "soybean")}
    sw = {k: float(np.mean(v)) for k, v in SORGHUM_SW_2004_2009.items()}
    sorghum_none = mean_yield("sorghum", "all") / (sw["all"] / sw["non_irrigated"])
    sorghum_gain = sw["irrigated"] / sw["non_irrigated"]
    levels["sorghum"] = (sorghum_none * sorghum_gain, sorghum_none, True)
    # assumption: Kansas sunflower 'all practices' counts as rain-fed, and it gains from water like sorghum
    sunflower_none = mean_yield("sunflower", "all")
    levels["sunflower"] = (sunflower_none * sorghum_gain, sunflower_none, True)
    return levels
