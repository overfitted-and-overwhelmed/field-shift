"""WP2 Water Adapter: irrigation per season and water per month, from the scorer's water balance.

The scorer computes the rain-fed irrigation need (ETc - ETa, FAO-56 bucket) for every season and
weather year. We only convert it to inches and apply the irrigation level of the season:

* ``full``: the whole need is irrigated
* ``reduced``: half of it (assumption, the same 50 % as in WP3 Yield)
* ``none``: rain-fed, no irrigation

Season values are the MEAN over the weather years with 10th / 90th percentile, so the monthly
values (also means) add up to the season.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Sequence

import numpy as np

from explorer.field_calendar import PlacedSeason, scorer_rows, load_scorer_monthly, load_scorer_seasons
from explorer.schema import Irrigation, Spread

MM_PER_IN = 25.4
IRRIGATED_SHARE: dict[str, float] = {"full": 1.0, "reduced": 0.5, "none": 0.0}


def season_irrigation(rotation: str, irrigation: Sequence[Irrigation]) -> list[Spread]:
    """Irrigation per season in inches: mean, P10, P90 over the weather years."""
    rows = scorer_rows(load_scorer_seasons(), rotation, "seasons table")
    seasons = sorted(rows["season"].unique())
    if len(seasons) != len(irrigation):
        raise ValueError(f"rotation '{rotation}': {len(seasons)} seasons, but {len(irrigation)} irrigation levels")
    out = []
    for season, level in zip(seasons, irrigation):
        need_in = rows.loc[rows["season"] == season, "irrigation_need_mm"].to_numpy() / MM_PER_IN
        applied = need_in * IRRIGATED_SHARE[level]
        v = float(applied.mean())
        p10, p90 = (float(x) for x in np.percentile(applied, [10, 90]))
        # a very skewed spread can put the mean outside P10..P90; the contract wants p10 <= v <= p90
        out.append(Spread(v=round(v, 2), p10=round(min(p10, v), 2), p90=round(max(p90, v), 2)))
    return out


def _season_of_month(month: str, seasons: Sequence[PlacedSeason]) -> int | None:
    """Index of the season that covers most days of ``month`` ("YYYY-MM"), None if no season touches it."""
    year, m = (int(x) for x in month.split("-"))
    first = date(year, m, 1)
    last = date(year + m // 12, m % 12 + 1, 1) - timedelta(days=1)
    best, best_days = None, 0
    for s in seasons:
        days = (min(last, s.harvest_date - timedelta(days=1)) - max(first, s.plant_date)).days + 1
        if days > best_days:
            best, best_days = s.index, days
    return best


def monthly_water(
    rotation: str, start_year: int, seasons: Sequence[PlacedSeason], irrigation: Sequence[Irrigation]
) -> list[dict]:
    """Water per month of the window, in inches: ``{"m", "et_in", "rain_in", "irr_in"}``.

    ``irr_in`` uses the irrigation level of the season that covers most days of the month. In a month
    where two seasons with different levels meet (double crop), this is a small approximation.
    """
    rows = scorer_rows(load_scorer_monthly(), rotation, "monthly table").sort_values(["year_offset", "month"])
    out = []
    for r in rows.itertuples():
        m = f"{start_year + int(r.year_offset)}-{int(r.month):02d}"
        season = _season_of_month(m, seasons)
        share = IRRIGATED_SHARE[irrigation[season]] if season is not None else 0.0
        out.append({
            "m": m,
            "et_in": round(r.et_mm / MM_PER_IN, 2),
            "rain_in": round(r.precipitation_mm / MM_PER_IN, 2),
            "irr_in": round(r.irrigation_need_mm * share / MM_PER_IN, 2),
        })
    return out
