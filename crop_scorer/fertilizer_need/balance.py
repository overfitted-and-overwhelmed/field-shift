"""N balance along a rotation: removal, soil supply, fallow leaching, optional cover crop in the fallow.

Units: kg N/ha unless the name says otherwise. The cited inputs live in inputs.py (CSV tables in data/).

Model in short, per crop season (except the first of a run, which has no known previous crop):
    removal       = reference yield (t/ha) x N in grain (kg/t)                                  [NASS, Dryad/IFA]
    fixation      = soybean only: 45 kg N per t grain, covers part of its own removal
    supply        = organic matter credit (K-State, per % OM and year, counted per day) + N carried over from the fallow before
                    + credit of the previous crop (soybean: net fixation, capped at 0)
    cover effect  = + immobilization after cereal rye / - credit after a legume (SARE ranges, kg/ha)
    fertilizer    = max(0, removal / fe - supply + cover effect)   (fe = fertilizer efficiency, K-State MF2586, same structure as its formula)
Fallow: mineralization adds N to a nitrate pool every day; days with drainage (water_usage) remove a share of it
(SWAT+ mixing equation). What is left is carried to the next crop, what is leached is reported separately.
"""

from dataclasses import dataclass
from functools import cache

import numpy as np
import pandas as pd

from crop_scorer.fertilizer_need import inputs as I
from crop_scorer.water_usage.water_usage import SOIL_FILE

# Assumptions of the cover crop rule (no source): sown within this many days before the latest sowing date
COVER_SOW_WINDOW_DAYS = 30
# overwintering covers are terminated in mid May at the latest (NRCS gives only "35 days before planting")
COVER_TERMINATION_LATEST = (5, 15)
# a winterkilled cover (radish) needs about four weeks to establish (SARE: sown 4 weeks before the first freeze)
MIN_COVER_DAYS = 28
# the NRCS termination zone of the county is 1 or 2 (cover_crop_site_facts.csv); zone 1 (35 days) is the cautious choice
SPECIES = ("cereal_rye", "hairy_vetch", "forage_radish")


@dataclass(frozen=True)
class Settings:
    cover: str | None = None  # species put into every fallow where it fits
    mineralization: str = "mid"  # "low", "mid", "high": credit per 1 % OM 14 / 20 / 28 lb N/ac (K-State, UNL)
    theta_e: float = I.THETA_E_DEFAULT  # fraction of porosity from which nitrate is excluded (SWAT+ ANION_EXCL)
    efficiency: str = "default: broadcast, fall-applied pre-plant"  # K-State fe, condition text in the CSV


@cache
def organic_matter_pct() -> float:
    return I.soil_coef("organic_matter_0_23cm")


def mineralization_factor(level: str) -> float:
    """Scale of the K-State credit (20 lb N/ac per % OM): low 14 and high 28 from UNL, derived in the coefficient table."""
    mid = I.soil_coef("n_mineralization_credit_per_pct_om")
    key = {"low": "n_mineralization_credit_per_pct_om_low", "mid": None, "high": "n_mineralization_credit_per_pct_om_high"}[level]
    return 1.0 if key is None else I.soil_coef(key) / mid


@cache
def saturated_water_mm(root_depth_m: float) -> float:
    """Saturated water content of the soil down to the root depth: sum of porosity x thickness, porosity = 1 - bulk density / 2.65."""
    soil = pd.read_csv(SOIL_FILE)
    bd = soil[soil["parameter"] == "bulk_density"]
    assert (bd["unit"] == "g/cm3").all()
    thickness_cm = (bd["depth_bottom_cm"].clip(upper=root_depth_m * 100) - bd["depth_top_cm"]).clip(lower=0)
    porosity = 1 - bd["value"] / I.PARTICLE_DENSITY_G_CM3
    return float((porosity * thickness_cm).sum() * 10)


@cache
def termination_days_before_planting() -> int:
    d = pd.read_csv(I.DATA / "cover_crop_effects.csv").set_index("id")
    return int(d.loc["termination_zone_1", "value_low"])


def cover_plan(prev_harvest: pd.Timestamp, next_sow: pd.Timestamp, species: str) -> dict | None:
    """Sowing and termination date of a cover crop in the fallow, or None if it does not fit."""
    latest = pd.Timestamp(prev_harvest.year, 1, 1) + pd.Timedelta(days=I.cover_sow_latest_doy()[species] - 1)
    sow = max(prev_harvest, latest - pd.Timedelta(days=COVER_SOW_WINDOW_DAYS))
    if sow > latest:
        return None
    if species in I.winterkilled_species():  # dies at the mean first frost, no termination needed
        end = pd.Timestamp(sow.year, 1, 1) + pd.Timedelta(days=I.first_frost_doy_mean() - 1)
    else:
        spring_year = sow.year + 1 if sow.month >= 7 else sow.year
        end = pd.Timestamp(spring_year, *COVER_TERMINATION_LATEST)
    end = min(end, next_sow - pd.Timedelta(days=termination_days_before_planting()))
    if (end - sow).days < MIN_COVER_DAYS:
        return None
    return {"sow": sow, "end": end, "days": (end - sow).days}


def fallow_nitrate(drainage: np.ndarray, daily_min_kg: float, volume_mm: float, retained_kg: float, cover_mask: np.ndarray) -> tuple[float, float, float]:
    """Daily nitrate pool of the fallow: returns (carried to the next crop, leached, mineralized) in kg N/ha.

    Leached share of a day: 1 - exp(-drainage / V), V = (1 - theta_e) x saturated water content (SWAT+ eq. 4:2.1.2 and 4:2.1.8,
    with the pool as NO3_ly and the drainage of water_usage as the mobile water). A cover crop holds up to `retained_kg` of the pool.
    """
    pool = leached = 0.0
    for drain, covered in zip(drainage, cover_mask):
        pool += daily_min_kg
        exposed = max(0.0, pool - retained_kg) if covered else pool
        loss = exposed * (1.0 - np.exp(-drain / volume_mm))
        pool -= loss
        leached += loss
    return pool, leached, daily_min_kg * len(drainage)


def ksu_need_kg(crop: str, prev_crop: str, ey_unit_per_ac: float, mineralization: float) -> float:
    """Fertilizer N by the K-State MF2586 formula as a cross-check, kg N/ha. No formula exists for soybean (returns NaN).

    N = (ie/fe) x EY - se x ProfileN - SOM x credit + PreviousCropAdj  (lb N/ac); no profile N sample, no manure.
    EY = 1.05 x mean yield (K-State rule). Not floored at the 30 lb minimum.
    """
    if crop == "soybean":
        return float("nan")
    season = I.SEASON_TYPE[crop]
    fe = I.ksu("all", "fe", "default: broadcast, fall-applied pre-plant")
    se = I.ksu("all", "se", "low N-loss risk: medium texture or western KS")
    profile_n = I.ksu("all", "profile_n_default")
    credit = I.ksu(season, "som_credit") * organic_matter_pct() * mineralization
    ey = I.ksu("all", "expected_yield_rule") * ey_unit_per_ac
    prev = I.previous_crop_adjustment_lb(season, prev_crop)
    if crop == "sunflower":
        n = ey * I.ksu("sunflower", "yield_factor") - credit - profile_n + prev
    else:
        ie = I.ksu(crop, "ie", "non-irrigated" if crop == "corn" else None)
        n = ie / fe * ey - se * profile_n - credit + prev
    return max(0.0, n) * I.LB_AC_TO_KG_HA


def run_balance(daily: pd.DataFrame, seasons: list, params: pd.DataFrame, settings: Settings) -> pd.DataFrame:
    """One row per crop season from the second one on. `daily` must hold the `drainage` column of water_usage."""
    yields = I.reference_yields()
    om = organic_matter_pct()
    mf = mineralization_factor(settings.mineralization)
    fe = I.ksu("all", "fe", settings.efficiency)
    # fallow: the K-State credit of a warm season crop (20 lb N/ac per % OM) per year, spread over 365 days (assumption)
    fallow_rate = I.ksu("warm_season", "som_credit") * om * I.LB_AC_TO_KG_HA * mf / 365  # kg N/ha/day
    rows = []
    for (prev_crop, _, prev_harvest), (crop, sow, harvest) in zip(seasons, seasons[1:]):
        fallow = pd.date_range(prev_harvest, sow - pd.Timedelta(days=1))
        drainage = daily.loc[fallow, "drainage"].to_numpy() if len(fallow) else np.zeros(0)
        cover_mask = np.zeros(len(fallow), dtype=bool)
        cover = cover_plan(prev_harvest, sow, settings.cover) if settings.cover else None
        if cover:
            cover_mask = (fallow >= cover["sow"]) & (fallow <= cover["end"])
        retained_kg = I.COVER_RETAINED_LB.get(settings.cover, 0.0) * I.LB_AC_TO_KG_HA if cover else 0.0
        volume = (1 - settings.theta_e) * saturated_water_mm(float(params.loc[crop, "root_depth_m"]))
        carried, leached, fallow_min = fallow_nitrate(drainage, fallow_rate, volume, retained_kg, cover_mask)

        yield_t_ha = float(yields.loc[crop, "yield_t_ha"])
        removal = yield_t_ha * I.coef(crop, "grain", "n_removal_grain")
        # the K-State credit is a yearly figure: counted per day over the season (own crop type) and over the fallow (warm season rate)
        season_min = I.ksu(I.SEASON_TYPE[crop], "som_credit") * om * mf * I.LB_AC_TO_KG_HA * (harvest - sow).days / 365
        prev_credit = 0.0
        if prev_crop == "soybean":  # net fixation per t grain, already capped at 0 in the coefficient table
            prev_credit = I.coef("soybean", "grain", "n_credit_applied") * float(yields.loc["soybean", "yield_t_ha"])
        cover_effect = I.COVER_N_EFFECT_LB[settings.cover][settings.mineralization] * I.LB_AC_TO_KG_HA if cover else 0.0
        # soybean covers part of its own removal by fixation (gross, per t grain); other crops fix nothing
        fixation = I.coef("soybean", "grain", "n_fixed_gross") * yield_t_ha if crop == "soybean" else 0.0
        # K-State structure: the crop needs removal / fe in fertilizer N, soil supply and credits are subtracted as they are
        balance = max(0.0, removal - fixation) / fe - season_min - carried - prev_credit + cover_effect
        need = max(0.0, balance)
        need_no_leaching = max(0.0, balance - leached)
        ey_unit = float(yields.loc[crop, "mean_yield"])
        rows.append({
            "crop": crop,
            "harvest_year": harvest.year,
            "previous_crop": prev_crop,
            "fallow_days": len(fallow),
            "cover_days": int(cover["days"]) if cover else 0,
            "yield_t_ha": yield_t_ha,
            "removal": removal,
            "fixation": fixation,
            "mineralization_season": season_min,
            "mineralization_fallow": fallow_min,
            "leaching_fallow": leached,
            "carried_from_fallow": carried,
            "previous_crop_credit": prev_credit,
            "cover_effect": cover_effect,
            "balance_unfloored": balance,
            "leaching_charged": need - need_no_leaching,
            "fertilizer_need": need,
            "ksu_fertilizer_need": ksu_need_kg(crop, prev_crop, ey_unit, mf),
        })
    return pd.DataFrame(rows)
