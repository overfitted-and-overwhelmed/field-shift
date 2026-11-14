"""WP5 Field Calendar: what is on the field, and when.

Step 1 (this file so far): planting and harvest date per season, from the USDA NASS
crop progress calendar for Kansas.

Rules:
* Target date = middle of NASS's "most active" window, i.e. roughly the date by which half of
  Kansas farmers have planted (or harvested). A typical date, not an extreme one.
* A season's ``year`` is its harvest year. Winter wheat for 2029 is planted in autumn 2028.
  We detect this from the data: if harvest comes earlier in the year than planting, the crop
  must cross New Year.
* We also keep the FULL window (first to last planting/harvest in Kansas). Step 2 needs it:
  after soybean or sunflower, the target date for winter wheat is too early (the field is still
  occupied), so planting moves later, but only as long as it stays inside the full window.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from explorer.paths import NASS_CALENDAR
from explorer.schema import SequenceStep


# frozen = read-only after creation, so nobody changes a window by accident.
@dataclass(frozen=True)
class DayWindow:
    """A range of days of the year, ``first`` to ``last`` (inclusive)."""

    first: int
    last: int

    @property
    def mid(self) -> int:
        return (self.first + self.last) // 2


@dataclass(frozen=True)
class CropWindow:
    """NASS planting and harvest windows of one crop, as day of year."""

    planting: DayWindow  # "most active" window
    planting_full: DayWindow  # first to last planting
    harvest: DayWindow  # "most active" window
    harvest_full: DayWindow  # first to last harvest

    @property
    def plant_doy(self) -> int:
        return self.planting.mid

    @property
    def harvest_doy(self) -> int:
        return self.harvest.mid

    @property
    def crosses_new_year(self) -> bool:
        return self.harvest_doy < self.plant_doy


def _window(values: dict[str, int], crop: str, first: str, last: str) -> DayWindow:
    try:
        return DayWindow(values[first], values[last])
    except KeyError as missing:
        raise ValueError(f"NASS calendar: crop '{crop}' has no value for {missing}") from None


# @cache: the file is read once, later calls get the same result without reading again.
# Because every caller gets the SAME object, we return a read-only mapping (MappingProxyType).
@cache
def load_nass_calendar(path: Path = NASS_CALENDAR) -> Mapping[str, CropWindow]:
    """Read the NASS calendar CSV (long format: crop, parameter, value) into one entry per crop."""
    values: dict[str, dict[str, int]] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            values.setdefault(row["crop"], {})[row["parameter"]] = int(float(row["value"]))
    calendar = {
        crop: CropWindow(
            planting=_window(v, crop, "planting_most_active_start", "planting_most_active_end"),
            planting_full=_window(v, crop, "planting_begin", "planting_end"),
            harvest=_window(v, crop, "harvest_most_active_start", "harvest_most_active_end"),
            harvest_full=_window(v, crop, "harvest_begin", "harvest_end"),
        )
        for crop, v in values.items()
    }
    return MappingProxyType(calendar)


def _from_doy(year: int, doy: int) -> date:
    # Day of year counts from 1. In leap years dates after February shift by one day,
    # which does not matter at this level of detail.
    return date(year, 1, 1) + timedelta(days=doy - 1)


def season_dates(step: SequenceStep, calendar: Mapping[str, CropWindow] | None = None) -> tuple[date, date]:
    """Target planting and harvest date of one season, ignoring the seasons around it.

    >>> season_dates(SequenceStep(year=2027, crop="corn", irrigation="full"))
    (datetime.date(2027, 4, 30), datetime.date(2027, 10, 2))
    """
    calendar = load_nass_calendar() if calendar is None else calendar
    window = calendar.get(step.crop)
    if window is None:
        raise ValueError(
            f"no NASS calendar entry for main crop '{step.crop}'. "
            f"Known crops: {sorted(calendar)}. Cover crops get their dates separately."
        )
    plant_year = step.year - 1 if window.crosses_new_year else step.year
    return _from_doy(plant_year, window.plant_doy), _from_doy(step.year, window.harvest_doy)
