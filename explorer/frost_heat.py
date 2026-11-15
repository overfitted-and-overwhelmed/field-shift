"""WP6 Frost & Heat Adapter: temperature stress per month of a rotation.

Per month we report the share of weather years (in percent) with at least one stress day while a crop
stands. The seasons and the thresholds are the scorer's (``crop_scorer/risk_score``, Ecocrop limits):

* ``heat_years_pct``: from the scorer as it is (Tmax above the crop's optimum).
* ``kill_years_pct``: from the scorer as it is (Tmin below the crop's killing temperature = real frost damage).
* ``cold_stress_years_pct``: computed HERE, stricter than the scorer's "frost". The scorer counts a day as
  soon as Tmin dips below the crop's optimum, which happens on most cool summer nights (corn in July:
  ~90 % of years). We count a day only if the temperature stays below the optimum for at least
  ``COLD_STRESS_MIN_DAY_SHARE`` of the day.

Duration below a threshold from daily values: we only have Tmin and Tmax per day, so we assume the
temperature follows a sine curve between them (the usual assumption for daily data). The share of the
day below a threshold T is then ``arccos((Tmid - T) / A) / pi`` with ``Tmid = (Tmin + Tmax) / 2`` and
``A = (Tmax - Tmin) / 2``. With a minimum share of 0.5 this simply means: Tmid is below T.

Like the scorer: winter wheat has no cold stress during its winter rest, and kill days count as kill,
not as cold stress.
"""

from __future__ import annotations

from functools import cache

import numpy as np
import pandas as pd

from crop_scorer.risk_score import compute_daily_risk, in_winter_rest, load_crop_configs, load_temperature_data
from explorer.field_calendar import load_scorer_monthly, load_scorer_seasons, scorer_rows

# Assumption: a day counts as cold stress when it is below the crop's optimum for at least half the day.
COLD_STRESS_MIN_DAY_SHARE = 0.5


def share_of_day_below(tmin: np.ndarray, tmax: np.ndarray, threshold: float) -> np.ndarray:
    """Share of the day (0-1) with temperature below ``threshold``, for a sine curve from tmin to tmax.

    >>> share_of_day_below(np.array([0.0]), np.array([20.0]), 10.0).round(2).tolist()
    [0.5]
    """
    tmid, amplitude = (tmin + tmax) / 2, (tmax - tmin) / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.where(amplitude > 0, (tmid - threshold) / amplitude, np.sign(tmid - threshold))
    return np.arccos(np.clip(x, -1, 1)) / np.pi


@cache
def _weather() -> pd.DataFrame:
    return load_temperature_data().set_index("date")


@cache
def cold_stress_days(crop: str, min_day_share: float = COLD_STRESS_MIN_DAY_SHARE) -> pd.Series:
    """True on every weather day (1991-2025) that counts as cold stress for ``crop`` (crop on the field)."""
    config = load_crop_configs()[crop]
    temps = load_temperature_data()
    risk = compute_daily_risk(temps, config)  # for the scorer's kill days
    below = share_of_day_below(temps["tmin"].to_numpy(), temps["tmax"].to_numpy(), config.temp_opt_min)
    cold = (below >= min_day_share) & (below > 0) & ~risk["kill"].to_numpy()
    if config.is_winter_crop:
        cold &= ~in_winter_rest(temps["month"], temps["day"]).to_numpy()
    return pd.Series(cold, index=temps["date"].to_numpy())


def monthly_cold_stress(rotation: str, min_day_share: float = COLD_STRESS_MIN_DAY_SHARE) -> pd.Series:
    """Share of weather years (0-1) with at least one cold-stress day, per (year_offset, month) of the window.

    Same counting as the scorer's monthly table: for each scorer run (start year) the window runs from the
    first sowing to the day before the last harvest; only crop days can be stress days.
    """
    seasons = scorer_rows(load_scorer_seasons(), rotation, "seasons table")
    in_window, stressed = [], []
    for _, run in seasons.groupby("start_year"):
        first = run["sow_date"].min()
        window = pd.date_range(first, run["harvest_date"].max() - pd.Timedelta(days=1), freq="D")
        in_window.append({(d.year - first.year, d.month) for d in window})
        hit = set()
        for s in run.itertuples():
            days = pd.date_range(s.sow_date, s.harvest_date - pd.Timedelta(days=1), freq="D")
            cold = cold_stress_days(s.crop, min_day_share).reindex(days, fill_value=False)
            hit |= {(d.year - first.year, d.month) for d in days[cold.to_numpy()]}
        stressed.append(hit)
    keys = sorted(set().union(*in_window))
    return pd.Series(
        {k: sum(k in h for h, w in zip(stressed, in_window) if k in w) / sum(k in w for w in in_window) for k in keys}
    )


def monthly_stress(rotation: str, start_year: int) -> list[dict]:
    """Per month: ``{"m", "heat_years_pct", "cold_stress_years_pct", "kill_years_pct"}`` (0-100)."""
    rows = scorer_rows(load_scorer_monthly(), rotation, "monthly table").sort_values(["year_offset", "month"])
    cold = monthly_cold_stress(rotation)
    return [
        {
            "m": f"{start_year + int(r.year_offset)}-{int(r.month):02d}",
            "heat_years_pct": round(r.heat_year_share * 100, 1),
            "cold_stress_years_pct": round(float(cold.get((int(r.year_offset), int(r.month)), 0.0)) * 100, 1),
            "kill_years_pct": round(r.kill_year_share * 100, 1),
        }
        for r in rows.itertuples()
    ]
