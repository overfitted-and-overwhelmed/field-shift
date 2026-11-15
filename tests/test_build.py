"""Tests for WP7 Pipeline & Export (explorer/build.py)."""

import pytest

from explorer.build import build_explorer, scorer_response
from explorer.field_calendar import place_seasons
from explorer.nitrogen import season_nitrogen
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


def _scorer_view(d: dict) -> dict:
    # strip what the explorer adds, also inside the cover variant
    scorer_fields = set(ScorerSeason.model_fields)
    d = {k: v for k, v in d.items() if k not in ("placeholder", "monthly", "summary")}
    d["sequence"] = [{k: v for k, v in s.items() if k in scorer_fields} for s in d["sequence"]]
    if d["cover_variant"]:
        d["cover_variant"] = _scorer_view(d["cover_variant"])
    return d


def test_explorer_passes_scorer_rotations_through(built):
    export, response = built
    for ours, theirs in zip(export.rotations, response.rotations):
        assert _scorer_view(ours.model_dump()) == theirs.model_dump()


def test_every_rotation_comes_with_its_cover_variant(built):
    export, _ = built
    for r in export.rotations:
        v = r.cover_variant
        assert v.id.split("+")[0] == r.id.split("+")[0] and ("+" in v.id) != ("+" in r.id)
        assert (v.is_current, v.rank, v.short) == (r.is_current, r.rank, r.short)
        assert v.score != r.score and v.kpi["rank_all"] != r.kpi["rank_all"]  # its own scorer row
        with_cover, without = (r, v) if "+" in r.id else (v, r)
        # the cover crop covers the soil, ties up N and takes soil water
        assert with_cover.summary.bare_months < without.summary.bare_months
        assert sum(s.n_lb for s in with_cover.sequence) > sum(s.n_lb for s in without.sequence)


def test_no_cover_variant_where_no_gap_fits_a_cover_crop():
    # winter wheat sown right after the summer crop's harvest leaves no gap for triticale
    response = scorer_response(["corn", "winter_wheat", "sorghum"], 2027, WEIGHTS)
    assert response.rotations[0].id == "corn-winter_wheat-sorghum"
    assert response.rotations[0].cover_variant is None


def test_dates_are_the_calendar_adapters(built):
    export, _ = built
    for r in export.rotations:
        placed = place_seasons(r.id, export.field.rotation_start_year)
        assert [(s.plant_date, s.harvest_date) for s in r.sequence] == [(p.plant_date, p.harvest_date) for p in placed]


def test_kpi_is_in_inches_without_the_scorers_frost_days(built):
    export, _ = built
    for r in export.rotations:
        assert "frost_days" not in r.kpi and not any("_mm" in k for k in r.kpi)
        assert r.kpi["irrigation_in"] == pytest.approx(sum(s.irr_in.v for s in r.sequence), abs=0.05)


def test_kpi_per_year_is_the_pass_value_over_the_cycle_years(built):
    export, _ = built
    for r in export.rotations:
        years = r.kpi["cycle_days"] / 365.25
        assert r.kpi["irrigation_in_per_year"] == pytest.approx(r.kpi["irrigation_in"] / years)
        assert r.kpi["n_lb_per_year"] == pytest.approx(r.kpi["n_lb"] / years)
        assert r.kpi["n_lb"] == pytest.approx(sum(s.n_lb for s in r.sequence), abs=0.5)


def test_continuous_corn_has_one_season_per_year(built):
    export, _ = built
    corn = export.rotations[0]  # corn-corn-corn
    assert corn.kpi["cycle_days"] == pytest.approx(3 * 365.25, abs=1)
    assert corn.kpi["n_lb_per_year"] == pytest.approx(corn.sequence[0].n_lb, abs=0.5)
    assert corn.kpi["irrigation_in_per_year"] == pytest.approx(sum(s.irr_in.v for s in corn.sequence) / 3, abs=0.1)


def test_nitrogen_per_season_is_the_scorers_and_the_monthly_balance_stays_null(built):
    export, _ = built
    for r in export.rotations:
        assert [s.n_lb for s in r.sequence] == [n.n_lb for n in season_nitrogen(r.id)]
        assert all(m.nitrogen is None for m in r.monthly) and r.summary.n_loss_lb is None


def test_current_rotation_ignores_non_crop_years_in_history():
    history = ["corn"] * 16 + ["fallow/idle cropland", "corn"]
    current = scorer_response(history, 2027, WEIGHTS).rotations[0]
    assert current.id == "corn-corn-corn"


def test_score_parts_cover_every_scorer_criterion(built):
    from crop_scorer.scoring.score_rotations import CRITERIA
    _, response = built
    assert set(response.rotations[0].score_parts.model_dump()) == set(CRITERIA)
