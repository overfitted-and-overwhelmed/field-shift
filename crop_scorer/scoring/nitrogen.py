"""Nitrogen fertilizer need of a crop season after K-State MF2586 (Ruiz Diaz, Jan 2024), in kg N/ha.

corn, sorghum, winter wheat:  N = ie / fe x EY - se x ProfileN - SOM x credit + PreviousCropAdj
sunflower:                    N = 0.075 x EY - SOM x 20 - ProfileN + PreviousCropAdj
then limited to the K-State minimum (and maximum for corn). No manure, no other N sources.
After a cereal cover crop (triticale) the next crop needs COVER_N_LB more (residue ties up N).

All factors come from the cleaned K-State tables (data/processed/crop_data/ksu). EY = expected yield from NASS,
practice "all" at the most local level with 5 years (1.05 x mean, K-State rule; nass_quickstats/expected_yield_clean.csv).
SOM = organic matter of the top SSURGO layer (0-23 cm), ProfileN = K-State default (no soil sample).
"""

from functools import cache

import pandas as pd

from crop_scorer.water_usage.water_usage import REPO, SOIL_FILE

KSU_FILE = REPO / "data/processed/crop_data/ksu/ksu_n_recommendations_clean.csv"
PREVIOUS_CROP_FILE = REPO / "data/processed/crop_data/ksu/ksu_previous_crop_adjustments_clean.csv"
EXPECTED_YIELD_FILE = REPO / "data/processed/crop_data/nass_quickstats/expected_yield_clean.csv"
LB_PER_AC_TO_KG_PER_HA = 0.45359237 / 0.40468564224

SEASON_TYPE = {
    "winter_wheat": "cool_season",
    "corn": "warm_season",
    "sorghum": "warm_season",
    "soybean": "warm_season",
    "sunflower": "warm_season",
}
FE_CONDITION = "default: broadcast, fall-applied pre-plant"
SE_CONDITION = "low N-loss risk: medium texture or western KS"
# ASSUMPTION: corn ie and max N of irrigated fields; the Kearny County corn yield (all practices, ~170 bu/ac)
# is close to the irrigated level (213), far above dryland (85)
CORN_CONDITION = "irrigated"
# ASSUMPTION: MF2586 has no N recommendation for soybean; as a legume it fixes its own N, so no fertilizer
NO_FORMULA_KG = {"soybean": 0.0}
# Clark (ed.) 2007, Managing Cover Crops Profitably, 3rd ed., SARE, p. 46: after a high-residue cereal cover the cash
# crop may need 25-30 lb N/ac more; middle of the range (cited in data/cover_crop_effects.csv on feat/fertilizer-need)
COVER_N_LB = 27.5


@cache
def _ksu_table() -> pd.DataFrame:
    return pd.read_csv(KSU_FILE)


def ksu(scope: str, parameter: str, condition: str | None = None) -> float:
    d = _ksu_table()
    d = d[(d["scope"] == scope) & (d["parameter"] == parameter)]
    if condition is not None:
        d = d[d["condition"] == condition]
    assert len(d) == 1, f"K-State {scope}/{parameter}/{condition}: {len(d)} rows"
    return float(d["value"].iloc[0])


@cache
def expected_yield(crop: str) -> float:
    y = pd.read_csv(EXPECTED_YIELD_FILE)
    row = y[(y["crop"] == crop) & (y["practice"] == "all")]
    assert len(row) == 1, f"expected yield {crop}: {len(row)} rows"
    return float(row["expected_yield"].iloc[0])


@cache
def organic_matter_pct() -> float:
    soil = pd.read_csv(SOIL_FILE)
    om = soil[(soil["parameter"] == "organic_matter") & (soil["depth_top_cm"] == 0)]
    assert len(om) == 1 and (om["unit"] == "%").all()
    return float(om["value"].iloc[0])


@cache
def _previous_crop_table() -> pd.DataFrame:
    d = pd.read_csv(PREVIOUS_CROP_FILE)
    return d[d["condition"].isna()]


def previous_crop_adjustment_lb(crop: str, previous: str | None) -> float:
    # the first season of a rotation has no previous crop inside the window: no adjustment
    if previous is None:
        return 0.0
    d = _previous_crop_table()
    d = d[(d["season_type"] == SEASON_TYPE[crop]) & (d["previous_crop"] == previous)]
    assert len(d) == 1, f"previous crop adjustment {crop} after {previous}: {len(d)} rows"
    return float(d["n_adjustment_lb_a"].iloc[0])


@cache
def season_n_need_kg(crop: str, previous: str | None, after_cover: bool = False) -> float:
    if crop in NO_FORMULA_KG:
        return NO_FORMULA_KG[crop]
    season = SEASON_TYPE[crop]
    ey = expected_yield(crop)
    som_credit = organic_matter_pct() * ksu(season, "som_credit")
    profile_n = ksu("all", "profile_n_default")
    previous_adj = previous_crop_adjustment_lb(crop, previous) + (COVER_N_LB if after_cover else 0.0)
    if crop == "sunflower":
        n = ey * ksu("sunflower", "yield_factor") - som_credit - profile_n + previous_adj
    else:
        ie = ksu(crop, "ie", CORN_CONDITION if crop == "corn" else None)
        fe = ksu("all", "fe", FE_CONDITION)
        se = ksu("all", "se", SE_CONDITION)
        n = ie / fe * ey - se * profile_n - som_credit + previous_adj
    n = max(n, ksu(crop, "min_n"))
    if crop == "corn":
        n = min(n, ksu("corn", "max_n", CORN_CONDITION))
    return n * LB_PER_AC_TO_KG_PER_HA


def rotation_n_need_kg(rotation: list[str], after_cover: list[bool] | None = None) -> list[float]:
    # one value per season of one pass; the previous crop is the one before it in the rotation,
    # after_cover[i]: a cover crop stood in the gap before season i
    after_cover = after_cover or [False] * len(rotation)
    return [season_n_need_kg(crop, rotation[i - 1] if i else None, after_cover[i]) for i, crop in enumerate(rotation)]
