"""WP5 Field Calendar: what is on the field, and when.

Step 1: target planting and harvest date per season, from the USDA NASS crop progress
        calendar for Kansas (``season_dates``).
Step 2: plan the 4 seasons one after another, move a planting later if the field is still
        occupied, and build a calendar with one row per day (``schedule``, ``daily_calendar``).
Step 3: condense the daily calendar into the 48 months of the frontend view and the summary
        numbers (``monthly_view``, ``summarize``).
Step 4: cover crops (``SequenceStep.cover``) fill the gap after their season's harvest, until
        shortly before the next main crop is planted. Done inside ``schedule``.

Rules:
* Target date = middle of NASS's "most active" window, i.e. roughly the date by which half of
  Kansas farmers have planted (or harvested). A typical date, not an extreme one.
* A season's ``year`` is its harvest year. Winter wheat for 2029 is planted in autumn 2028.
  We detect this from the data: if harvest comes earlier in the year than planting, the crop
  must cross New Year.
* If the field is still occupied on the target planting date (typical: winter wheat after
  soybean or sunflower), planting moves to harvest + GAP_AFTER_HARVEST_DAYS, as long as that
  stays inside NASS's FULL planting window. Otherwise the rotation is impossible and we raise
  CalendarConflict on purpose: a bad rotation should fail loudly, not produce wrong numbers.
* A cover crop is planted GAP_AFTER_HARVEST_DAYS after its season's harvest, but not before
  COVER_PLANTING_WINDOW opens (triticale is a winter cereal, sown in autumn), and terminated
  COVER_END_BEFORE_PLANTING_DAYS before the next main crop is planted (after the last season:
  it stays until the end of the rotation). Planting after the window closes or a cover that
  stands less than MIN_COVER_DAYS -> CalendarConflict.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import date, timedelta
from functools import cache
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

import pandas as pd

from explorer.paths import NASS_CALENDAR
from explorer.schema import SequenceStep

# Days between harvesting one crop and planting the next. Assumption: wheat after soybean is
# often drilled right after harvest in Kansas.
GAP_AFTER_HARVEST_DAYS = 3

# Cover crops (assumptions): terminated about two weeks before the next crop is planted, so the
# seedbed can settle. A cover that would stand less than a month is not worth planting.
COVER_END_BEFORE_PLANTING_DAYS = 14
MIN_COVER_DAYS = 30
# Autumn sowing window for the cover crop, as (month, day). After wheat (harvest end of June)
# the field stays bare until the window opens instead of being "covered" all summer.
COVER_PLANTING_WINDOW = ((9, 1), (11, 30))


class CalendarConflict(ValueError):
    """A crop cannot be planted because the field is still occupied by the crop before it."""


# --------------------------------------------------------------------------------------
# Step 1: NASS windows and target dates
# --------------------------------------------------------------------------------------


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
    """NASS day of year -> calendar date, the SAME calendar date in every year.

    Counting from 1 January directly would move every date after February one day earlier in
    leap years (day 289 = 16 Oct, but 15 Oct in 2028). That can flip a month in the monthly
    view, so we read the day in a non-leap year (2001) and only swap the year.
    """
    return (date(2001, 1, 1) + timedelta(days=min(doy, 365) - 1)).replace(year=year)


def _window_for(crop: str, calendar: Mapping[str, CropWindow]) -> CropWindow:
    window = calendar.get(crop)
    if window is None:
        raise ValueError(
            f"no NASS calendar entry for main crop '{crop}'. "
            f"Known crops: {sorted(calendar)}. Cover crops get their dates separately."
        )
    return window


def _target_dates(crop: str, harvest_year: int, calendar: Mapping[str, CropWindow]) -> tuple[date, date]:
    window = _window_for(crop, calendar)
    plant_year = harvest_year - 1 if window.crosses_new_year else harvest_year
    return _from_doy(plant_year, window.plant_doy), _from_doy(harvest_year, window.harvest_doy)


def season_dates(step: SequenceStep, calendar: Mapping[str, CropWindow] | None = None) -> tuple[date, date]:
    """Target planting and harvest date of one season, ignoring the seasons around it.

    >>> season_dates(SequenceStep(year=2027, crop="corn", irrigation="full"))
    (datetime.date(2027, 4, 30), datetime.date(2027, 10, 2))
    """
    return _target_dates(step.crop, step.year, load_nass_calendar() if calendar is None else calendar)


# --------------------------------------------------------------------------------------
# Step 2: plan the seasons and build the daily calendar
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PlannedCover:
    """A cover crop after a season: from ``plant`` to ``end`` (termination), both inclusive."""

    crop: str
    plant: date
    end: date


@dataclass(frozen=True)
class PlannedSeason:
    """One season with its final dates, after checking the season before it."""

    index: int  # 0..3, position in the rotation
    crop: str
    plant: date
    harvest: date
    shifted_days: int  # > 0: planting had to wait for the previous harvest ("tight window")
    cover: PlannedCover | None = None  # cover crop after this season's harvest


def schedule(
    sequence: Sequence[SequenceStep],
    previous_crop: str,
    calendar: Mapping[str, CropWindow] | None = None,
) -> list[PlannedSeason]:
    """Final planting and harvest dates for all seasons, in order.

    ``previous_crop`` is what grew in the year before the rotation (``field.previous_crop``).
    It matters when the first season is a winter crop planted in the autumn before.
    Raises CalendarConflict if a crop cannot be planted inside its NASS window.
    """
    calendar = load_nass_calendar() if calendar is None else calendar
    _, field_free_from = _target_dates(previous_crop, sequence[0].year - 1, calendar)
    before = f"previous crop '{previous_crop}'"

    planned: list[PlannedSeason] = []
    for i, step in enumerate(sequence):
        plant, harvest = _target_dates(step.crop, step.year, calendar)
        earliest = field_free_from + timedelta(days=GAP_AFTER_HARVEST_DAYS)
        shifted = 0
        if plant < earliest:
            latest = _from_doy(plant.year, _window_for(step.crop, calendar).planting_full.last)
            if earliest > latest or earliest >= harvest:
                raise CalendarConflict(
                    f"season {i} ({step.crop}, harvest {step.year}) cannot be planted: the field is "
                    f"occupied by {before} until {field_free_from}, but {step.crop} must be planted "
                    f"by {latest} at the latest (NASS planting window)."
                )
            shifted = (earliest - plant).days
            plant = earliest
        planned.append(PlannedSeason(i, step.crop, plant, harvest, shifted))
        field_free_from = harvest
        before = f"season {i} ({step.crop})"

    # Cover crops need the FINAL planting date of the next season, so they come second.
    for i, step in enumerate(sequence):
        if step.cover is None:
            continue
        season = planned[i]
        start = season.harvest + timedelta(days=GAP_AFTER_HARVEST_DAYS)
        (m1, d1), (m2, d2) = COVER_PLANTING_WINDOW
        window_opens, window_closes = date(start.year, m1, d1), date(start.year, m2, d2)
        if start > window_closes:
            raise CalendarConflict(
                f"cover crop '{step.cover}' after season {i} ({step.crop}): the field is free only from "
                f"{start}, after the cover planting window closes ({window_closes})."
            )
        start = max(start, window_opens)
        if i + 1 < len(planned):
            end = planned[i + 1].plant - timedelta(days=COVER_END_BEFORE_PLANTING_DAYS)
        else:
            end = date(sequence[-1].year, 12, 31)  # last season: cover stays until the rotation ends
        if (end - start).days + 1 < MIN_COVER_DAYS:
            raise CalendarConflict(
                f"cover crop '{step.cover}' after season {i} ({step.crop}) would stand only "
                f"{max((end - start).days + 1, 0)} days ({start} to {end}), less than {MIN_COVER_DAYS}."
            )
        planned[i] = replace(season, cover=PlannedCover(step.cover, start, end))
    return planned


def daily_calendar(seasons: Sequence[PlannedSeason], first_year: int, n_years: int = 4) -> pd.DataFrame:
    """One row per day from 1 Jan ``first_year`` to 31 Dec of the last year.

    Columns: ``crop`` (None if bare), ``kind`` ("crop", "cover" or "bare"),
    ``season`` (index of the season the day belongs to, also for its cover crop; <NA> if bare).
    A winter crop planted before ``first_year`` shows up from 1 January.

    To look at main crops only (e.g. frost/heat while the crop stands), filter on
    ``kind == "crop"``. Filtering on ``season`` alone would include the cover crop days.
    """
    days = pd.date_range(f"{first_year}-01-01", f"{first_year + n_years - 1}-12-31", freq="D", name="date")
    cal = pd.DataFrame(
        {
            "crop": pd.Series(None, index=days, dtype="object"),
            "kind": "bare",
            "season": pd.Series(pd.NA, index=days, dtype="Int64"),  # Int64 = integer that allows <NA>
        }
    )
    for s in seasons:
        # .loc with two dates selects the range including both ends.
        span = cal.loc[pd.Timestamp(s.plant) : pd.Timestamp(s.harvest)]
        if span["season"].notna().any():  # cannot happen after schedule(); guards against misuse
            raise CalendarConflict(f"season {s.index} overlaps another season")
        cal.loc[span.index, ["crop", "kind", "season"]] = [s.crop, "crop", s.index]
    for s in seasons:
        if s.cover is None:
            continue
        span = cal.loc[pd.Timestamp(s.cover.plant) : pd.Timestamp(s.cover.end)]
        if (span["kind"] != "bare").any():  # cannot happen after schedule(); guards against misuse
            raise CalendarConflict(f"cover crop after season {s.index} overlaps a main crop")
        cal.loc[span.index, ["crop", "kind", "season"]] = [s.cover.crop, "cover", s.index]
    return cal


# --------------------------------------------------------------------------------------
# Step 3: months and summary
# --------------------------------------------------------------------------------------


def monthly_view(cal: pd.DataFrame) -> list[dict]:
    """One entry per month: ``{"m": "YYYY-MM", "kind": ..., "crop": ...}``.

    A month shows what covers the field on MORE than half of its days. Otherwise it is "bare".
    Example: corn harvested on 2 October -> October is bare (2 of 31 days).
    """
    months = []
    for period, days in cal.groupby(cal.index.to_period("M")):
        covered = days[days["kind"] != "bare"]
        if len(covered) * 2 > len(days):
            kind = covered["kind"].mode().iloc[0]  # mode = most frequent value
            crop = covered.loc[covered["kind"] == kind, "crop"].mode().iloc[0]
        else:
            kind, crop = "bare", None
        months.append({"m": str(period), "kind": kind, "crop": crop})
    return months


def summarize(cal: pd.DataFrame, seasons: Sequence[PlannedSeason], previous_crop: str) -> dict:
    """Summary numbers of the rotation (the part of ``schema.Summary`` that WP5 owns).

    * ``bare_months``: days without crop or cover, converted to months, mean per year.
      Counted per day, not per month, so a half-bare month counts as 0.5.
    * ``same_crop_repeats``: seasons with the same crop as the season before
      (season 1 compares to ``previous_crop``). Continuous corn after corn = 4.
    """
    bare_share = (cal["kind"] == "bare").groupby(cal.index.year).mean()  # share of bare days per year
    crops = [previous_crop] + [s.crop for s in seasons]
    return {
        "bare_months": float(bare_share.mean() * 12),
        "same_crop_repeats": sum(a == b for a, b in zip(crops, crops[1:])),
    }
