"""Tests for WP7 Pipeline & Export (explorer/build.py)."""

import pytest

from explorer.build import build_explorer, scorer_response
from explorer.field_calendar import place_seasons
from explorer.schema import ScorerSeason

WEIGHTS = {"water": 1, "risk": 1, "soil_health": 1}


@pytest.fixture(scope="module")
def built():
    return build_explorer(WEIGHTS)


def test_export_is_valid_and_has_current_plus_three_picks(built):
    export, _ = built  # building validates against schema.py, a bad value would raise here
    assert [r.is_current for r in export.rotations] == [True, False, False, False]
    assert [r.rank for r in export.rotations] == [None, 1, 2, 3]


def test_current_rotation_comes_from_the_field_history(built):
    export, _ = built
    assert export.rotations[0].id == "corn-corn-corn"  # Kearny: corn every year in the CDL


def test_picks_follow_the_weights():
    water_only = scorer_response(["corn"] * 18, 2027, {"water": 1, "risk": 0, "soil_health": 0})
    picks = [r for r in water_only.rotations if not r.is_current]
    assert [r.score_parts.water for r in picks] == sorted(r.score_parts.water for r in picks)


def test_explorer_passes_scorer_rotations_through(built):
    export, response = built
    scorer_fields = set(ScorerSeason.model_fields)
    for ours, theirs in zip(export.rotations, response.rotations):
        d = ours.model_dump(exclude={"placeholder", "monthly", "summary"})
        d["sequence"] = [{k: v for k, v in s.items() if k in scorer_fields} for s in d["sequence"]]
        assert d == theirs.model_dump()


def test_dates_are_the_calendar_adapters(built):
    export, _ = built
    for r in export.rotations:
        placed = place_seasons(r.id, export.field.rotation_start_year)
        assert [(s.plant_date, s.harvest_date) for s in r.sequence] == [(p.plant_date, p.harvest_date) for p in placed]


def test_nitrogen_is_null_until_wp4(built):
    export, _ = built
    r = export.rotations[0]
    assert r.sequence[0].n_lb is None and r.monthly[0].nitrogen is None and r.summary.n_loss_lb is None


def test_current_rotation_ignores_non_crop_years_in_history():
    history = ["corn"] * 16 + ["fallow/idle cropland", "corn"]
    current = scorer_response(history, 2027, WEIGHTS).rotations[0]
    assert current.id == "corn-corn-corn"
