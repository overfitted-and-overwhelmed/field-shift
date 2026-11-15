"""Tests for WP2 Water Adapter (explorer/water.py)."""

import pytest

from explorer.field_calendar import load_scorer_seasons, place_seasons
from explorer.water import MM_PER_IN, monthly_water, season_irrigation

KEY, START = "winter_wheat-soybean-sorghum", 2027


def test_full_irrigation_is_the_scorers_mean_need_in_inches():
    s = load_scorer_seasons()
    need = s[(s["rotation"] == KEY) & (s["season"] == 0)]["irrigation_need_mm"]
    assert season_irrigation(KEY, ["full"] * 3)[0].v == pytest.approx(need.mean() / MM_PER_IN, abs=0.01)


def test_reduced_is_half_and_none_is_zero():
    full = season_irrigation(KEY, ["full"] * 3)
    reduced = season_irrigation(KEY, ["reduced"] * 3)
    none = season_irrigation(KEY, ["none"] * 3)
    for f, r, n in zip(full, reduced, none):
        assert r.v == pytest.approx(f.v / 2, abs=0.01)
        assert (n.v, n.p10, n.p90) == (0, 0, 0)


def test_spread_is_ordered():
    for s in season_irrigation(KEY, ["full"] * 3):
        assert s.p10 <= s.v <= s.p90


def test_months_add_up_to_the_seasons():
    seasons = place_seasons(KEY, START)
    months = monthly_water(KEY, START, seasons, ["full"] * 3)
    total_months = sum(m["irr_in"] for m in months)
    total_seasons = sum(s.v for s in season_irrigation(KEY, ["full"] * 3))
    assert total_months == pytest.approx(total_seasons, abs=0.1)  # only rounding differs


def test_month_uses_the_irrigation_level_of_its_season():
    seasons = place_seasons(KEY, START)
    months = {m["m"]: m for m in monthly_water(KEY, START, seasons, ["none", "full", "none"])}
    assert months["2027-11"]["irr_in"] == 0  # wheat, rain-fed
    assert months["2028-08"]["irr_in"] > 0  # soybean, irrigated


def test_wrong_number_of_irrigation_levels_fails():
    with pytest.raises(ValueError, match="3 seasons, but 2"):
        season_irrigation(KEY, ["full", "full"])
