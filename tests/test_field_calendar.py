"""Tests for WP5 Field Calendar (explorer/field_calendar.py).

Step 1: target planting and harvest dates per season.
Step 2: planning the seasons in order (schedule) and the daily calendar.
"""

from datetime import date
from pathlib import Path

import pytest

from explorer.field_calendar import (
    GAP_AFTER_HARVEST_DAYS,
    CalendarConflict,
    daily_calendar,
    load_nass_calendar,
    schedule,
    season_dates,
)
from explorer.schema import SequenceStep, load_explorer

MAIN_CROPS = ["corn", "sorghum", "soybean", "winter_wheat", "sunflower"]
EXAMPLE = load_explorer(Path(__file__).resolve().parents[1] / "explorer" / "examples" / "explorer.json")
MOCKUP_ROTATIONS = {r.id: r.sequence for r in EXAMPLE.rotations}
PREVIOUS_CROP = EXAMPLE.field.previous_crop  # corn


def _step(crop: str, year: int = 2027) -> SequenceStep:
    return SequenceStep(year=year, crop=crop, irrigation="full")


def _seq(*crops: str, start: int = 2027) -> list[SequenceStep]:
    return [_step(c, start + i) for i, c in enumerate(crops)]


# --- Step 1: target dates ------------------------------------------------------------


def test_calendar_has_all_main_crops():
    assert set(MAIN_CROPS) <= set(load_nass_calendar())


def test_corn_dates_are_middle_of_nass_window():
    # NASS corn: planting 105-135 -> 120 = 30 April; harvest 253-298 -> 275 = 2 October
    assert season_dates(_step("corn")) == (date(2027, 4, 30), date(2027, 10, 2))


def test_winter_wheat_is_planted_the_autumn_before():
    plant, harvest = season_dates(_step("winter_wheat", year=2029))
    assert plant.year == 2028 and plant.month in (9, 10)
    assert harvest.year == 2029 and harvest.month == 6


@pytest.mark.parametrize("crop", MAIN_CROPS)
def test_season_length_is_plausible(crop):
    # Summer crops in Kansas grow ~4-5 months, winter wheat ~9 months.
    plant, harvest = season_dates(_step(crop, year=2029))
    assert 100 <= (harvest - plant).days <= 300


@pytest.mark.parametrize("previous", ["corn", "sorghum", "soybean", "sunflower"])
def test_wheat_after_summer_crop_fits_into_full_planting_window(previous):
    # The target wheat date (~1 Oct) is often BEFORE the summer crop is harvested.
    # schedule() moves wheat planting later; this checks that the full NASS window allows it.
    calendar = load_nass_calendar()
    assert calendar[previous].harvest_doy < calendar["winter_wheat"].planting_full.last


def test_calendar_is_read_only():
    with pytest.raises(TypeError):
        load_nass_calendar()["corn"] = None


def test_cover_crop_as_main_crop_gives_clear_error():
    with pytest.raises(ValueError, match="triticale"):
        season_dates(_step("triticale"))


# --- Step 2: schedule ----------------------------------------------------------------


@pytest.mark.parametrize("rotation_id", MOCKUP_ROTATIONS)
def test_all_mockup_rotations_can_be_scheduled(rotation_id):
    seasons = schedule(MOCKUP_ROTATIONS[rotation_id], PREVIOUS_CROP)
    assert len(seasons) == 4
    for before, after in zip(seasons, seasons[1:]):
        assert (after.plant - before.harvest).days >= GAP_AFTER_HARVEST_DAYS


def test_continuous_corn_needs_no_shift():
    assert all(s.shifted_days == 0 for s in schedule(MOCKUP_ROTATIONS["current"], PREVIOUS_CROP))


@pytest.mark.parametrize("previous", ["soybean", "sunflower"])
def test_wheat_waits_for_summer_crop_harvest(previous):
    # opt_cswg has soybean -> wheat, opt_sfw sunflower -> wheat (both in autumn 2028)
    soy_or_sun, wheat = schedule(_seq("corn", previous, "winter_wheat"), PREVIOUS_CROP)[1:]
    assert wheat.shifted_days > 0
    assert (wheat.plant - soy_or_sun.harvest).days == GAP_AFTER_HARVEST_DAYS
    assert wheat.plant <= date(2028, 11, 1)  # still inside NASS wheat planting window


def test_first_season_is_checked_against_previous_crop():
    # Wheat for 2027 is planted in autumn 2026, right after last year's soybean.
    first = schedule(_seq("winter_wheat", "sorghum", "corn", "corn"), previous_crop="soybean")[0]
    assert first.plant.year == 2026 and first.shifted_days > 0


def test_impossible_rotation_fails_loudly():
    # Two corn seasons harvested in the same year: the second cannot be planted.
    impossible = [_step("corn", 2027), _step("corn", 2027), _step("corn", 2028), _step("corn", 2029)]
    with pytest.raises(CalendarConflict, match="season 1"):
        schedule(impossible, PREVIOUS_CROP)


# --- Step 2: daily calendar ----------------------------------------------------------


def test_daily_calendar_covers_four_full_years():
    cal = daily_calendar(schedule(MOCKUP_ROTATIONS["current"], PREVIOUS_CROP), first_year=2027)
    assert cal.index[0].date() == date(2027, 1, 1) and cal.index[-1].date() == date(2030, 12, 31)
    assert len(cal) == 365 * 4 + 1  # 2028 is a leap year


def test_continuous_corn_calendar():
    cal = daily_calendar(schedule(MOCKUP_ROTATIONS["current"], PREVIOUS_CROP), first_year=2027)
    assert cal.loc["2027-01-01", "kind"] == "bare"
    assert cal.loc["2027-07-01", "crop"] == "corn"
    assert cal.loc["2027-12-01", "kind"] == "bare"
    # roughly 5 months corn per year (30 Apr - 2 Oct)
    assert 150 <= (cal["kind"] == "crop").sum() / 4 <= 160


def test_wheat_planted_before_window_shows_from_january():
    seasons = schedule(_seq("winter_wheat", "sorghum", "corn", "corn"), previous_crop="soybean")
    cal = daily_calendar(seasons, first_year=2027)
    assert cal.loc["2027-01-01", "crop"] == "winter_wheat"


def test_soybean_then_wheat_in_calendar():
    cal = daily_calendar(schedule(MOCKUP_ROTATIONS["opt_cswg"], PREVIOUS_CROP), first_year=2027)
    assert cal.loc["2028-08-01", "crop"] == "soybean"
    assert cal.loc["2028-12-01", "crop"] == "winter_wheat"
    assert cal.loc["2029-08-01", "kind"] == "bare"  # after wheat harvest in June
