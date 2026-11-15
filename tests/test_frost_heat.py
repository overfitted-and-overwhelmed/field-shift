"""Tests for WP6 Frost & Heat Adapter (explorer/frost_heat.py)."""

import numpy as np
import pytest

from explorer.field_calendar import load_scorer_monthly, monthly_kinds
from explorer.frost_heat import monthly_cold_stress, monthly_stress, share_of_day_below

KEY, START = "corn-corn-corn", 2027
ROTATIONS = ["corn-corn-corn", "winter_wheat-soybean-sorghum", "sunflower-sorghum-winter_wheat"]
CSV_PRECISION = 1e-4  # the scorer writes its shares with 4 decimals


def _scorer_monthly(key):
    m = load_scorer_monthly()
    return m[m["rotation"] == key].set_index(["year_offset", "month"])


# --- duration below a threshold (sine curve between Tmin and Tmax) ---------------------


@pytest.mark.parametrize("tmin, tmax, threshold, share", [
    (0, 20, 10, 0.5),  # threshold at the middle: half the day
    (0, 20, 25, 1.0),  # always below
    (0, 20, -5, 0.0),  # never below
    (0, 20, 0, 0.0),  # only touches at the minimum
    (5, 5, 10, 1.0),  # constant temperature below
])
def test_share_of_day_below(tmin, tmax, threshold, share):
    assert share_of_day_below(np.array([tmin], float), np.array([tmax], float), threshold)[0] == pytest.approx(share)


def test_share_of_day_grows_with_the_threshold():
    shares = [share_of_day_below(np.array([0.0]), np.array([20.0]), t)[0] for t in (2, 6, 10, 14, 18)]
    assert shares == sorted(shares)


# --- cold stress vs the scorer --------------------------------------------------------


@pytest.mark.parametrize("key", ROTATIONS)
def test_on_the_optimum_without_minimum_duration_it_is_exactly_the_scorers_frost(key):
    # "below the optimum for any part of the day" = the scorer's rule (Tmin below the optimum), so this proves we
    # count the same days, windows and weather years as the scorer.
    ours = monthly_cold_stress(key, min_day_share=1e-9, limit="temp_opt_min")
    scorer = _scorer_monthly(key).reindex(ours.index)
    assert (ours["years"] - scorer["frost_year_share"]).abs().max() < CSV_PRECISION
    assert (ours["days"] - scorer["frost_days"]).abs().max() < 1e-3 * scorer["frost_days"].max()


@pytest.mark.parametrize("key", ROTATIONS)
def test_our_cold_stress_is_never_more_than_the_scorers_frost(key):
    ours = monthly_cold_stress(key)
    scorer = _scorer_monthly(key).reindex(ours.index)
    assert (ours["years"] <= scorer["frost_year_share"] + CSV_PRECISION).all()
    assert (ours["days"] <= scorer["frost_days"] + 1e-6).all()


@pytest.mark.parametrize("key", ROTATIONS)
def test_no_cold_stress_in_summer(key):
    # the scorer's "frost" for corn in July is ~90 % of years, because Tmin dips below the optimum most nights;
    # that only slows growth, our cold stress needs the absolute minimum
    for m in monthly_stress(key, START):
        if m["m"][5:] in ("06", "07", "08"):
            assert m["cold_stress_days"] == 0 and m["cold_stress_years_pct"] == 0


def test_days_tell_summer_months_apart_where_the_share_of_years_does_not():
    months = {m["m"]: m for m in monthly_stress(KEY, START)}
    june, july, august = (months[f"2027-0{i}"] for i in (6, 7, 8))
    assert june["heat_years_pct"] == july["heat_years_pct"] == august["heat_years_pct"] == 100
    assert months["2027-05"]["heat_days"] < june["heat_days"] < july["heat_days"]


def test_no_cold_stress_during_winter_wheat_rest():
    # scorer rule: no cold stress for winter wheat in its winter rest (1 Nov - 31 Mar)
    months = {m["m"]: m for m in monthly_stress("winter_wheat-soybean-sorghum", START)}
    for m in ["2027-11", "2027-12", "2028-01", "2028-02", "2028-03"]:
        assert months[m]["cold_stress_years_pct"] == 0


# --- output -----------------------------------------------------------------------------


def test_heat_and_kill_are_the_scorers():
    row = _scorer_monthly(KEY).iloc[3]
    m = monthly_stress(KEY, START)[3]
    assert m["heat_years_pct"] == pytest.approx(row["heat_year_share"] * 100, abs=0.05)
    assert m["kill_years_pct"] == pytest.approx(row["kill_year_share"] * 100, abs=0.05)
    assert m["heat_days"] == pytest.approx(row["heat_days"], abs=0.05)
    assert m["kill_days"] == pytest.approx(row["kill_days"], abs=0.05)


def test_values_are_percent_and_days_of_a_month():
    for m in monthly_stress(KEY, START):
        for f in ("heat_years_pct", "cold_stress_years_pct", "kill_years_pct"):
            assert 0 <= m[f] <= 100
        for f in ("heat_days", "cold_stress_days", "kill_days"):
            assert 0 <= m[f] <= 31


def test_months_match_the_calendar():
    assert [m["m"] for m in monthly_stress(KEY, START)] == [m["m"] for m in monthly_kinds(KEY, START)]
