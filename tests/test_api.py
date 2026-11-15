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


@pytest.mark.parametrize("query", ["w=water:x", "w=water:-1", "w=water:0", "crops=triticale", "crops=rice", "n=0", "n=4", "n=a"])
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
