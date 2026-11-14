"""Tests for WP5 step 1: planting and harvest dates per season (explorer/field_calendar.py)."""

from datetime import date

import pytest

from explorer.field_calendar import load_nass_calendar, season_dates
from explorer.schema import SequenceStep

MAIN_CROPS = ["corn", "sorghum", "soybean", "winter_wheat", "sunflower"]


def _step(crop: str, year: int = 2027) -> SequenceStep:
    return SequenceStep(year=year, crop=crop, irrigation="full")


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
    # Step 2 moves wheat planting later; this checks that the full NASS window allows it.
    calendar = load_nass_calendar()
    assert calendar[previous].harvest_doy < calendar["winter_wheat"].planting_full.last


def test_calendar_is_read_only():
    with pytest.raises(TypeError):
        load_nass_calendar()["corn"] = None


def test_cover_crop_as_main_crop_gives_clear_error():
    with pytest.raises(ValueError, match="triticale"):
        season_dates(_step("triticale"))
