"""The explorer API: query parsing and the crop filter / pick count it passes to build_explorer."""

import pytest

from explorer.api import BadRequest, parse_request
from explorer.build import build_explorer


def test_defaults_weigh_every_criterion_the_same():
    req = parse_request("")
    assert req["crops"] is None and req["n_picks"] == 3
    assert set(req["weights"]) == {"water", "risk", "soil_health", "nitrogen"}
    assert len(set(req["weights"].values())) == 1


def test_parses_weights_crops_and_count_and_ignores_unknown_priorities():
    req = parse_request("w=water:5,risk:1,profit:4&crops=corn,soybean&n=2&lat=38&lon=-101")
    assert req["weights"] == {"water": 5, "risk": 1, "soil_health": 0, "nitrogen": 0}
    assert req["crops"] == ["corn", "soybean"] and req["n_picks"] == 2


@pytest.mark.parametrize("query", ["rotation=corn-rice-corn", "rotation=corn-corn-corn+clover", "w=water:x", "w=water:-1", "w=water:0", "crops=triticale", "crops=rice", "n=0", "n=4", "n=a"])
def test_rejects_bad_input(query):
    with pytest.raises(BadRequest):
        parse_request(query)


def test_picks_use_only_the_chosen_crops():
    export, _ = build_explorer({"water": 1}, crops=["corn", "soybean"], n_picks=2)
    picks = [r for r in export.rotations if not r.is_current]
    assert [r.rank for r in picks] == [1, 2]
    for r in picks:
        assert {s.crop for s in r.sequence} <= {"corn", "soybean"}
    assert all(r.kpi["n_lb_per_year"] >= 0 for r in export.rotations)


def test_a_built_rotation_replaces_the_current_one_and_keeps_the_picks():
    weights = {"water": 1, "risk": 1, "soil_health": 1, "nitrogen": 1}
    base, _ = build_explorer(weights)
    picks = [r.id for r in base.rotations if not r.is_current]
    built = picks[0]  # even a pick: it must then not show up twice
    export, _ = build_explorer(weights, current=built)
    assert [r.id for r in export.rotations if r.is_current] == [built]
    assert built not in [r.id for r in export.rotations if not r.is_current]
    assert parse_request("rotation=corn-soybean-sorghum+triticale")["current"] == "corn-soybean-sorghum+triticale"


def test_a_rotation_the_scorer_did_not_score_is_rejected():
    with pytest.raises(ValueError, match="not scored"):
        build_explorer({"water": 1}, current="corn-corn")


def test_a_cover_in_one_gap_only_is_scored_on_request():
    from explorer.on_demand import canonical_key
    weights = {"water": 1, "risk": 1, "soil_health": 1, "nitrogen": 1}
    assert canonical_key("corn-soybean-sorghum+triticale_12") == "corn-soybean-sorghum+triticale"
    export, _ = build_explorer(weights, current="corn-soybean-sorghum+triticale_1")
    cur = next(r for r in export.rotations if r.is_current)
    assert cur.id == "corn-soybean-sorghum+triticale_1"
    assert [s.cover for s in cur.sequence] == ["triticale", None, None]
    assert cur.kpi["n_rotations"] == 225  # still ranked against the precomputed rotations only
    assert all("_" not in r.id.partition("+")[2] for r in export.rotations if not r.is_current)
    assert parse_request("rotation=corn-soybean-sorghum%2Btriticale_2")["current"] == "corn-soybean-sorghum+triticale_2"


def test_weather_monthly_has_twelve_months_with_tmax_above_tmin():
    from explorer.api import weather_monthly
    w = weather_monthly()
    assert [x["month"] for x in w] == list(range(1, 13))
    assert all(x["tmax_f"] > x["tmin_f"] for x in w)
    assert max(x["tmax_f"] for x in w) > 85  # a western Kansas summer
