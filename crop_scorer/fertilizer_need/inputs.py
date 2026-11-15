"""Cited input tables of the N balance (data/*.csv) and the few constants that are flagged assumptions.

Every number comes from a CSV with citation columns, except the constants under "Assumptions", which say so.
"""

from functools import cache
from pathlib import Path
from typing import Final

import pandas as pd

REPO: Final[Path] = Path(__file__).resolve().parents[2]
DATA: Final[Path] = REPO / "data"
COEFFS_FILE: Final[Path] = DATA / "fertilizer_n_coefficients.csv"
KSU_EQ_FILE: Final[Path] = DATA / "ksu_mf2586_n_recommendations_long.csv"
KSU_PREV_FILE: Final[Path] = DATA / "ksu_mf2586_previous_crop_adjustments.csv"
UNITS_FILE: Final[Path] = DATA / "crop_unit_conversion.csv"
COVER_FILE: Final[Path] = DATA / "cover_crops.csv"
YIELDS_FILE: Final[Path] = DATA / "processed" / "crop_data" / "nass_quickstats" / "yields_clean.csv"
OUT_DIR: Final[Path] = DATA / "processed" / "fertilizer_need"

LB_AC_TO_KG_HA: Final[float] = 1.120851  # exact from the definitions of pound and acre (crop_unit_conversion.csv)

# Season type of the crop for the K-State tables (MF2586 pp. 3-4)
SEASON_TYPE: Final[dict[str, str]] = {
    "winter_wheat": "cool_season",
    "corn": "warm_season",
    "sorghum": "warm_season",
    "soybean": "warm_season",
    "sunflower": "warm_season",
}

# --- Assumptions (no source; kind="assumption") ---------------------------------------------------------------
# SWAT+ names ANION_EXCL (theta_e) but its documentation page gives no default; 0.5 is the middle of the 0-1 range
THETA_E_DEFAULT: Final[float] = 0.5
THETA_E_SENSITIVITY: Final[tuple[float, float]] = (0.2, 0.8)
# standard mineral particle density, used for porosity = 1 - bulk density / particle density
PARTICLE_DENSITY_G_CM3: Final[float] = 2.65
# SARE gives no latest sowing date for cereal rye (only "late summer to mid-fall"); the mean first frost is used
RYE_LATEST_SOW_DOY: Final[int] = 299
# Minimum number of years for a district mean; below that the state mean of all practices is used (team decision)
MIN_YEARS_DISTRICT: Final[int] = 5

# --- Cover crop N effects, lb N/ac, from data/cover_crop_effects.csv (typical ranges come from the `note` column) ---
# positive = the next crop needs more fertilizer. Radish has no number in SARE for a net effect: left at 0, not estimated.
COVER_N_EFFECT_LB: Final[dict[str, dict[str, float]]] = {
    # n_cereal_cover_extra_fert: "N fertilizer for the cash crop may need to rise by 25-30 lb N/ac" (book p. 46)
    "cereal_rye": {"low": 25.0, "mid": 27.5, "high": 30.0},
    # n_legume_contribution: legumes contribute 15-200, typical 50-100 lb N/ac (book p. 47); a legume value, not vetch specific.
    # Credit, so the sign is negative. "low" credit = small effect.
    "hairy_vetch": {"low": -50.0, "mid": -75.0, "high": -100.0},
    "forage_radish": {"low": 0.0, "mid": 0.0, "high": 0.0},
}
# n_rye_scavenge: rye holds 25-50 lb N/ac (typical, up to 100) until spring (book p. 98); only rye has such a number
COVER_RETAINED_LB: Final[dict[str, float]] = {"cereal_rye": 37.5, "hairy_vetch": 0.0, "forage_radish": 0.0}


@cache
def _coefficients() -> pd.Series:
    d = pd.read_csv(COEFFS_FILE)
    sel = d[d["selected"]].set_index(["crop", "crop_part", "parameter"])["value"]
    assert sel.index.is_unique, "two selected rows for the same coefficient"
    return sel


def coef(crop: str, part: str, parameter: str) -> float:
    """Value of the selected row in fertilizer_n_coefficients.csv."""
    return float(_coefficients().loc[(crop, part, parameter)])


def soil_coef(parameter: str) -> float:
    """Value of a `crop == "soil"` row, selected or not (the low/high mineralization rows are not selected)."""
    d = pd.read_csv(COEFFS_FILE)
    d = d[(d["crop"] == "soil") & (d["parameter"] == parameter)]
    assert len(d) == 1, f"soil/{parameter}: {len(d)} rows"
    return float(d["value"].iloc[0])


@cache
def _ksu() -> pd.DataFrame:
    return pd.read_csv(KSU_EQ_FILE)


def ksu(scope: str, parameter: str, condition: str | None = None) -> float:
    """Value from ksu_mf2586_n_recommendations_long.csv. `condition` must match exactly if given."""
    d = _ksu()
    d = d[(d["scope"] == scope) & (d["parameter"] == parameter)]
    if condition is not None:
        d = d[d["condition"] == condition]
    assert len(d) == 1, f"{scope}/{parameter}/{condition}: {len(d)} rows"
    return float(d["value"].iloc[0])


def previous_crop_adjustment_lb(season_type: str, previous_crop: str, condition: str | None = None) -> float:
    """K-State previous crop adjustment in lb N/ac (negative = credit). `condition` None means the row has no condition."""
    d = pd.read_csv(KSU_PREV_FILE)
    d = d[(d["season_type"] == season_type) & (d["previous_crop"] == previous_crop)]
    d = d[d["condition"].isna()] if condition is None else d[d["condition"] == condition]
    assert len(d) == 1, f"{season_type}/{previous_crop}: {len(d)} rows"
    return float(d["n_adjustment_lb_a"].iloc[0])


@cache
def cover_sow_latest_doy() -> dict[str, int]:
    """Latest sowing day of year per cover crop (mean first frost based, cover_crops.csv)."""
    d = pd.read_csv(COVER_FILE).set_index("species")["sow_latest_doy_mean_frost"]
    out = {name: int(d.loc[name]) for name in COVER_N_EFFECT_LB if name != "cereal_rye"}
    out["cereal_rye"] = RYE_LATEST_SOW_DOY
    return out


@cache
def _cover_table() -> pd.DataFrame:
    return pd.read_csv(COVER_FILE).set_index("species")


def winterkilled_species() -> set[str]:
    """Cover crops that die over winter at the site (cover_crops.csv, winter_fate_at_site == winterkills)."""
    t = _cover_table()
    return {s for s in COVER_N_EFFECT_LB if t.loc[s, "winter_fate_at_site"] == "winterkills"}


def first_frost_doy_mean() -> int:
    """Mean first fall frost (day of year) from cover_crop_site_facts.csv."""
    d = pd.read_csv(DATA / "cover_crop_site_facts.csv").set_index("key")
    return int(round(float(d.loc["first_fall_frost_doy_mean", "value"])))


@cache
def reference_yields() -> pd.DataFrame:
    """Mean NASS yield per crop: district Southwest non-irrigated if >= MIN_YEARS_DISTRICT years, else Kansas all practices.

    Returns one row per crop with the level used, the years, the mean in NASS units (bu/acre or lb/acre) and in t/ha.
    """
    y = pd.read_csv(YIELDS_FILE)
    units = pd.read_csv(UNITS_FILE).set_index("crop")
    rows = []
    for crop in SEASON_TYPE:
        district = y[(y["crop"] == crop) & (y["level"] == "district") & (y["area"] == "SOUTHWEST") & (y["practice"] == "non_irrigated")]
        if district["year"].nunique() >= MIN_YEARS_DISTRICT:
            pick, rule = district, "district SOUTHWEST, non-irrigated"
        else:
            pick = y[(y["crop"] == crop) & (y["level"] == "state") & (y["area"] == "KS") & (y["practice"] == "all")]
            rule = f"state KS, all practices (district non-irrigated has {district['year'].nunique()} years)"
        mean = float(pick["value"].mean())
        rows.append({
            "crop": crop,
            "rule": rule,
            "years": f"{pick['year'].min()}-{pick['year'].max()}",
            "n_years": int(pick["year"].nunique()),
            "mean_yield": mean,
            "yield_unit": pick["unit"].iloc[0],
            "yield_t_ha": mean * float(units.loc[crop, "t_per_ha_per_yield_unit"]),
        })
    return pd.DataFrame(rows).set_index("crop")
