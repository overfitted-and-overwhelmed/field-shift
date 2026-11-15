"""Cover crops end to end: the scorer's "+triticale" variants through calendar, water, yield and export."""

import pytest

from explorer.build import build_explorer
from explorer.field_calendar import monthly_kinds, parse_key, place_seasons, rotation_key, summarize
from explorer.schema import SequenceStep
from explorer.water import monthly_water
from explorer.yields import rotation_yields, season_deficits

PLAIN, COVERED, START = "corn-soybean-sorghum", "corn-soybean-sorghum+triticale", 2027


def test_key_round_trip():
    assert parse_key(COVERED) == (["corn", "soybean", "sorghum"], "triticale")
    assert parse_key(PLAIN) == (["corn", "soybean", "sorghum"], None)
    assert rotation_key(["corn", "soybean", "sorghum"], "triticale") == COVERED


def test_only_triticale_is_a_cover_crop():
    with pytest.raises(ValueError, match="not a cover crop"):
        parse_key("corn-soybean-sorghum+rye")


def test_seasons_get_the_scorers_cover():
    seasons = place_seasons(COVERED, START)
    assert [s.cover for s in seasons] == ["triticale", "triticale", None]  # no gap after the last season
    assert [(s.crop, s.plant_date, s.harvest_date) for s in seasons] == \
           [(s.crop, s.plant_date, s.harvest_date) for s in place_seasons(PLAIN, START)]  # main crops unchanged


def test_cover_months_are_kind_cover():
    months = {m["m"]: m for m in monthly_kinds(COVERED, START)}
    assert months["2027-12"] == {"m": "2027-12", "kind": "cover", "crop": "triticale"}
    assert months["2027-07"]["kind"] == "crop"


def test_cover_reduces_bare_months_but_not_same_crop_repeats():
    plain, covered = summarize(PLAIN, "corn"), summarize(COVERED, "corn")
    assert covered["bare_months"] < plain["bare_months"] - 3
    assert covered["same_crop_repeats"] == plain["same_crop_repeats"] == 1  # corn after corn


def test_cover_is_not_irrigated():
    seasons = place_seasons(COVERED, START)
    months = {m["m"]: m for m in monthly_water(COVERED, START, seasons, ["full"] * 3)}
    assert months["2028-01"]["irr_in"] == 0


def test_yield_uses_the_water_deficit_of_the_variant_with_cover():
    # the cover takes soil water, so the scorer's deficits of the two variants differ; the yield must use
    # the cover variant, not silently the one without
    assert season_deficits(COVERED) != season_deficits(PLAIN)
    seq = [SequenceStep(year=2027 + i, crop=c, irrigation="none", cover=c_)
           for i, (c, c_) in enumerate(zip(["corn", "soybean", "sorghum"], ["triticale", "triticale", None]))]
    plain_seq = [s.model_copy(update={"cover": None}) for s in seq]
    with_cover = [y.yield_.v for y in rotation_yields(seq, history=["corn"] * 18)]
    without = [y.yield_.v for y in rotation_yields(plain_seq, history=["corn"] * 18)]
    assert with_cover != without


def test_export_with_cover_variants_is_valid():
    export, _ = build_explorer({"water": 1, "risk": 1, "soil_health": 1, "nitrogen": 1})
    covered = [r for r in export.rotations if "+" in r.id]
    assert covered, "expected at least one cover crop variant among the picks"
    for r in covered:
        assert any(s.cover == "triticale" for s in r.sequence)
        assert any(m.kind == "cover" for m in r.monthly)
        assert r.name.endswith("+ triticale cover")
