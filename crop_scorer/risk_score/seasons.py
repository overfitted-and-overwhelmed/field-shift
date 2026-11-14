"""Season simulation: one season per crop and year, from the middle of the sowing window to the middle of the harvest window."""

import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

from crop_scorer.risk_score.config import (
    CROP_MAPPINGS,
    DEFAULT_DATA_DIR,
    DEFAULT_ECOCROP_PATH,
    DEFAULT_KILL_PENALTY,
    DEFAULT_WINTER_REST_END,
    DEFAULT_WINTER_REST_START,
    CropConfig,
)
from crop_scorer.risk_score.severity import compute_daily_risk

DEFAULT_FAO56_STAGE_PATH = DEFAULT_DATA_DIR / "base-data" / "fao56" / "fao56_table11_stage_lengths.csv"

# crop_key -> (FAO56 crop name, region substring or None = all rows).
# Corn has no Central-USA row in Table 11, so it is not compared against FAO56.
FAO56_REFERENCE: dict[str, tuple[str, str | None] | None] = {
    "winter_wheat": ("Winter Wheat", None),
    "corn": None,
    "sorghum": ("Sorghum", "USA"),
    "soybean": ("Soybeans", "Central USA"),
    "sunflower": ("Sunflower", None),
}

SEASON_COLUMNS = [
    "crop_key",
    "season_year",
    "sow_date",
    "sow_doy",
    "harvest_date",
    "season_days",
    "frost_days",
    "heat_days",
    "kill_days",
    "season_score",
]


def _doy_to_date(year: int, doy: int) -> pd.Timestamp:
    return pd.Timestamp(year=year, month=1, day=1) + pd.Timedelta(days=doy - 1)


def simulate_seasons(
    temps: pd.DataFrame,
    crop: CropConfig,
    kill_penalty: float = DEFAULT_KILL_PENALTY,
    rest_start: tuple[int, int] = DEFAULT_WINTER_REST_START,
    rest_end: tuple[int, int] = DEFAULT_WINTER_REST_END,
) -> pd.DataFrame:
    """Score one season per crop and sowing year (same season definition as ``water_usage``).

    Sowing day = middle of the NASS most-active planting window, harvest day = middle of the
    most-active harvest window (``(start + end) // 2``). The season covers ``season_days =
    (harvest_doy - sow_doy) % 365`` days from the sowing day on; the harvest day itself is not
    scored. If the harvest day lies before the sowing day in the year (winter wheat), the season
    ends in the following year. ``season_year`` is the sowing year. Seasons that are not fully
    covered by ``temps`` are dropped.

    ``season_score`` is the MEAN of the daily scores over all season days (sum / season_days).
    Counters (days): frost_days / heat_days count stress days with frost / heat severity > 0 on
    non-kill days; kill_days counts cold-kill days (there is no heat kill).

    Parameters:
        temps: DataFrame from ``load_temperature_data`` (continuous daily series).
        crop: CropConfig of the crop.
        kill_penalty: Daily score on kill days.
        rest_start: (month, day) start of the dormancy window (winter crops).
        rest_end: (month, day) end of the dormancy window (winter crops).

    Returns:
        DataFrame with the columns in ``SEASON_COLUMNS``, one row per sowing year.
    """
    dates = pd.DatetimeIndex(temps["date"])
    risk = compute_daily_risk(temps, crop, kill_penalty, rest_start, rest_end)

    daily = pd.DataFrame(
        {
            "score": risk["daily_score"],
            "frost": (risk["frost_severity"] > 0) & ~risk["kill"],
            "heat": (risk["heat_severity"] > 0) & ~risk["kill"],
            "kill": risk["kill"],
        }
    ).astype(float)
    # Prefix sum with a leading zero row: sum over [i0, i1] = cum[i1 + 1] - cum[i0]
    cum = np.vstack([np.zeros(daily.shape[1]), daily.to_numpy().cumsum(axis=0)])
    cols = {name: i for i, name in enumerate(daily.columns)}

    sow_doy = (crop.planting_most_active_start + crop.planting_most_active_end) // 2
    harvest_doy = (crop.harvest_most_active_start + crop.harvest_most_active_end) // 2
    season_days = (harvest_doy - sow_doy) % 365

    rows = []
    for year in range(dates[0].year, dates[-1].year + 1):
        sow_date = _doy_to_date(year, sow_doy)
        harvest_date = sow_date + pd.Timedelta(days=season_days)
        if sow_date < dates[0] or harvest_date - pd.Timedelta(days=1) > dates[-1]:
            continue
        i0 = dates.get_loc(sow_date)
        total = cum[i0 + season_days] - cum[i0]
        rows.append(
            {
                "crop_key": crop.crop_key,
                "season_year": year,
                "sow_date": sow_date,
                "sow_doy": sow_doy,
                "harvest_date": harvest_date,
                "season_days": season_days,
                "frost_days": int(total[cols["frost"]]),
                "heat_days": int(total[cols["heat"]]),
                "kill_days": int(total[cols["kill"]]),
                "season_score": total[cols["score"]] / season_days,
            }
        )
    return pd.DataFrame(rows, columns=SEASON_COLUMNS)


def aggregate_yearly(seasons: pd.DataFrame) -> pd.DataFrame:
    """Condense seasons to one row per crop and sowing year.

    Columns: ``risk_score`` (= ``season_score``) and the counters ``frost_days`` / ``heat_days`` /
    ``kill_days`` of that season.
    """
    if seasons.empty:
        raise ValueError("No seasons to aggregate")

    out = seasons.rename(columns={"season_score": "risk_score"})
    return out[["crop_key", "season_year", "risk_score", "frost_days", "heat_days", "kill_days"]].sort_values(
        ["crop_key", "season_year"], ignore_index=True
    )


def _fao56_l_total(crop_key: str, fao56_path: Path | str) -> str:
    ref = FAO56_REFERENCE.get(crop_key)
    if ref is None:
        return ""
    name, region = ref
    fao = pd.read_csv(fao56_path)
    rows = fao[fao["crop"] == name]
    if region is not None:
        rows = rows[rows["region"].fillna("").str.contains(region, regex=False)]
    values: list[str] = []
    for raw in rows["L_total"].astype(str):
        values.extend(re.findall(r"\d+(?:\.\d+)?", raw))
    return "/".join(sorted(set(values), key=float))


def check_season_lengths(
    seasons: pd.DataFrame,
    ecocrop_path: Path | str = DEFAULT_ECOCROP_PATH,
    fao56_path: Path | str = DEFAULT_FAO56_STAGE_PATH,
) -> pd.DataFrame:
    """Plausibility check: compare NASS-derived season lengths with Ecocrop and FAO56 (warn only).

    Parameters:
        seasons: Output of ``simulate_seasons`` (may contain several crops).
        ecocrop_path: Path to ecocrop_selected_crops.csv (``crop_cycle_min`` / ``crop_cycle_max``).
        fao56_path: Path to fao56_table11_stage_lengths.csv (``L_total``).

    Returns:
        One row per crop: min/mean/max season days, Ecocrop cycle range, FAO56 L_total values
        (as ``"140"`` or ``"180/240/335"``, empty if no reference) and ``within_ecocrop``.
        A ``UserWarning`` is emitted for each crop whose mean season length is outside the
        Ecocrop range.
    """
    eco = pd.read_csv(ecocrop_path).set_index("ecocrop_id")
    rows = []
    for crop_key, grp in seasons.groupby("crop_key"):
        eco_row = eco.loc[int(CROP_MAPPINGS[crop_key]["ecocrop_id"])]
        cycle_min, cycle_max = float(eco_row["crop_cycle_min"]), float(eco_row["crop_cycle_max"])
        mean_days = grp["season_days"].mean()
        within = cycle_min <= mean_days <= cycle_max
        if not within:
            warnings.warn(
                f"{crop_key}: mean season length {mean_days:.0f} d is outside the Ecocrop cycle "
                f"range {cycle_min:.0f}-{cycle_max:.0f} d",
                stacklevel=2,
            )
        rows.append(
            {
                "crop_key": crop_key,
                "season_days_min": int(grp["season_days"].min()),
                "season_days_mean": mean_days,
                "season_days_max": int(grp["season_days"].max()),
                "ecocrop_cycle_min": cycle_min,
                "ecocrop_cycle_max": cycle_max,
                "fao56_l_total": _fao56_l_total(crop_key, fao56_path),
                "within_ecocrop": within,
            }
        )
    return pd.DataFrame(rows)
