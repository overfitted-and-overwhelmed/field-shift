"""Tests for the advisor core read layer (advisor/), on the example explorer.json and the real scores CSV."""

import json

import pytest

from advisor import (
    DetailNotAvailableError,
    UnknownRotationError,
    compare_rotations,
    field_overview,
    get_rotation,
    list_top_rotations,
    monthly_table,
)
from advisor.data import load_export, load_scores

CURRENT = "corn-corn-corn"
PICK_1 = "sunflower-soybean-sunflower+triticale"
CSV_ONLY = "corn-corn-sorghum"  # a candidate that is not in explorer.json


def test_field_overview():
    overview = field_overview()
    assert overview["field"]["id"] == "ks-kearny-01"
    assert overview["n_rotations"] == 225
    assert overview["current_rotation"]["id"] == CURRENT
    assert [p["pick"] for p in overview["picks"]] == [1, 2, 3]
    assert overview["picks"][0]["id"] == PICK_1
    assert overview["placeholder"] is False


def test_list_top_rotations_is_ranked_and_filterable():
    top = list_top_rotations(5)
    assert [r["rank_all"] for r in top] == [1, 2, 3, 4, 5]
    assert top[0]["id"] == PICK_1  # equal weights reproduce the picks of explorer.json
    assert all(r["cover_crop"] is None for r in list_top_rotations(5, cover_crop=False))
    assert all(r["cover_crop"] == "triticale" for r in list_top_rotations(5, cover_crop=True))
    assert [r["detail_level"] for r in top[:4]] == ["full", "full", "full", "scores_only"]
    with pytest.raises(ValueError, match="at least 1"):
        list_top_rotations(0)


def test_top_three_match_the_example_export():
    picks = [r.id for r in sorted(load_export().rotations, key=lambda r: r.rank or 0) if r.rank]
    assert [r["id"] for r in list_top_rotations(3)] == picks


def test_get_rotation_full_detail():
    r = get_rotation(PICK_1)
    assert r["detail_level"] == "full"
    assert r["pick"] == 1 and r["rank_all"] == 1
    assert len(r["seasons"]) == 3
    season = r["seasons"][0]
    assert {"irr_in", "yield", "n_lb", "n_adj_lb", "effects"} <= season.keys()  # "yield", not "yield_"
    assert set(season["yield"]) == {"v", "p10", "p90", "unit"}
    assert r["summary"]["bare_months"] > 0
    assert set(r["score_parts"]) == {"water", "risk", "soil_health", "nitrogen"}


def test_flags_are_kept_for_pending_nitrogen():
    r = get_rotation(CURRENT)
    assert r["flags"] == {"placeholder": False, "nitrogen_null": True}
    assert r["seasons"][0]["n_lb"] is None  # null stays null, not 0
    assert r["summary"]["n_loss_lb"] is None
    assert monthly_table(CURRENT)["flags"] == r["flags"]


def test_get_rotation_csv_only_says_its_detail_level():
    r = get_rotation(CSV_ONLY)
    assert r["detail_level"] == "scores_only"
    assert r["seasons"] is None and r["summary"] is None
    assert "Scores only" in r["note"]
    assert r["flags"]["placeholder"] is None  # unknown, not False
    assert r["rank_all"] == load_scores().index.get_loc(CSV_ONLY) + 1
    assert 0 <= r["total_score"] <= 1


def test_unknown_rotation_lists_close_matches():
    with pytest.raises(UnknownRotationError, match="corn-soybean-sorghum") as e:
        get_rotation("corn-soybean-sorgum")
    assert "corn-soybean-sorghum" in e.value.close_matches
    with pytest.raises(UnknownRotationError, match="No close matches"):
        get_rotation("zzz")
    with pytest.raises(UnknownRotationError):
        monthly_table("nope")
    with pytest.raises(UnknownRotationError):
        compare_rotations(CURRENT, "nope")


def test_compare_rotations_full():
    c = compare_rotations(CURRENT, PICK_1)
    assert c["detail_level"] == "full"
    assert c["diff"]["total_score"] < 0  # the pick scores better (smaller) than the current rotation
    assert c["diff"]["summary"]["bare_months"] < 0
    assert c["diff"]["summary"]["n_loss_lb"] is None  # nitrogen pending: no difference invented
    assert c["a"]["id"] == CURRENT and c["b"]["id"] == PICK_1


def test_compare_with_csv_only_rotation_drops_to_scores_only():
    c = compare_rotations(CURRENT, CSV_ONLY)
    assert c["detail_level"] == "scores_only"
    assert c["diff"]["summary"] is None
    assert c["diff"]["total_score"] == pytest.approx(c["b"]["total_score"] - c["a"]["total_score"], abs=1e-4)


def test_monthly_table():
    t = monthly_table(PICK_1)
    assert t["detail_level"] == "full"
    months = t["months"]
    assert [m["m"] for m in months] == sorted(m["m"] for m in months)
    assert {"et_in", "rain_in", "irr_in", "heat_years_pct", "cold_stress_years_pct", "kill_years_pct"} <= months[0].keys()
    assert len(months) == len(next(r for r in load_export().rotations if r.id == PICK_1).monthly)


def test_monthly_table_for_csv_only_rotation_explains_why():
    with pytest.raises(DetailNotAvailableError, match="only in the scores table"):
        monthly_table(CSV_ONLY)


def test_all_results_are_json_serializable():
    json.dumps(field_overview())
    json.dumps(list_top_rotations(10))
    json.dumps(get_rotation(CURRENT))
    json.dumps(get_rotation(CSV_ONLY))
    json.dumps(compare_rotations(CURRENT, PICK_1))
    json.dumps(monthly_table(PICK_1))
