"""Tests for WP5 Field Calendar (explorer/field_calendar.py): the scorer's seasons, placed in the display years."""

from datetime import timedelta

import pytest

from explorer.field_calendar import (
    load_scorer_scores,
    load_scorer_seasons,
    monthly_kinds,
    place_seasons,
    reference_start_year,
    summarize,
)

START = 2027


def test_seasons_are_the_scorers_dates_moved_to_the_start_year():
    key = "corn-soybean-sorghum"
    ref = reference_start_year(key, START)
    scorer = load_scorer_seasons()
    scorer = scorer[(scorer["rotation"] == key) & (scorer["start_year"] == ref)].sort_values("season")
    placed = place_seasons(key, START)
    years = START - ref
    assert [s.crop for s in placed] == list(scorer["crop"])
    for s, (_, row) in zip(placed, scorer.iterrows()):
        assert s.plant_date == row["sow_date"].date().replace(year=row["sow_date"].year + years)
        assert s.harvest_date == row["harvest_date"].date().replace(year=row["harvest_date"].year + years)


def test_first_sowing_is_in_the_start_year():
    for key in ["corn-corn-corn", "winter_wheat-soybean-sorghum", "sunflower-sunflower-sunflower"]:
        assert place_seasons(key, START)[0].plant_date.year == START


def test_reference_run_has_the_same_leap_year_rhythm():
    # a multiple of 4 years before 2027, so moving the dates keeps them exact
    assert (START - reference_start_year("corn-corn-corn", START)) % 4 == 0


def test_double_crop_two_harvests_in_one_year():
    # wheat harvested end of June 2028, soybean sown right after and harvested in November 2028
    wheat, soy, _ = place_seasons("winter_wheat-soybean-sorghum", START)
    assert wheat.harvest_year == soy.harvest_year == 2028
    assert (soy.plant_date - wheat.harvest_date).days == 3


def test_skipped_year_when_a_crop_misses_its_window():
    # wheat after the soybean double crop misses autumn 2028, so there is no harvest in 2029
    assert [s.harvest_year for s in place_seasons("winter_wheat-soybean-winter_wheat", START)] == [2028, 2028, 2030]


def test_seasons_do_not_overlap():
    for key in load_scorer_scores()["rotation"]:
        seasons = place_seasons(key, START)
        for before, after in zip(seasons, seasons[1:]):
            assert after.plant_date >= before.harvest_date, key


def test_monthly_window_runs_from_first_sowing_to_last_harvest():
    seasons = place_seasons("winter_wheat-soybean-sorghum", START)
    months = monthly_kinds("winter_wheat-soybean-sorghum", START)
    last_day = seasons[-1].harvest_date - timedelta(days=1)  # the harvest day is not part of the season
    assert months[0]["m"] == f"{seasons[0].plant_date:%Y-%m}" == "2027-10"
    assert months[-1]["m"] == f"{last_day:%Y-%m}"
    assert len(months) == len({m["m"] for m in months})  # no month twice


def test_monthly_kinds_follow_the_scorer():
    months = {m["m"]: m for m in monthly_kinds("corn-corn-corn", START)}
    assert months["2027-07"] == {"m": "2027-07", "kind": "crop", "crop": "corn"}
    assert months["2027-12"] == {"m": "2027-12", "kind": "bare", "crop": None}


def test_summary_bare_months_is_the_scorers_bare_share():
    scores = load_scorer_scores().set_index("rotation")
    s = summarize("corn-corn-corn", previous_crop="corn")
    assert s["bare_months"] == pytest.approx(scores.loc["corn-corn-corn", "bare_share"] * 12)


@pytest.mark.parametrize("key, previous, repeats", [
    ("corn-corn-corn", "corn", 3),  # corn after corn in every season
    ("corn-corn-corn", "soybean", 2),
    ("winter_wheat-soybean-sorghum", "corn", 0),
])
def test_same_crop_repeats(key, previous, repeats):
    assert summarize(key, previous)["same_crop_repeats"] == repeats


def test_unknown_rotation_fails_loudly():
    with pytest.raises(KeyError, match="not in the scorer"):
        place_seasons("corn-triticale-corn", START)


def test_monthly_window_matches_the_seasons_for_every_rotation():
    # the contract (schema.Rotation) checks this for the exported rotations; here for all of the scorer's
    for key in load_scorer_scores()["rotation"]:
        seasons, months = place_seasons(key, START), monthly_kinds(key, START)
        last_day = seasons[-1].harvest_date - timedelta(days=1)
        assert (months[0]["m"], months[-1]["m"]) == (f"{seasons[0].plant_date:%Y-%m}", f"{last_day:%Y-%m}"), key
