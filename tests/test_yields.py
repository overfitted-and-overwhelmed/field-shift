"""Tests for WP3 Yield (explorer/yields.py).

The model tests use a made-up crop, so they run without the scorer data. The last tests use the
real scorer file and are skipped until it arrives on this branch (scorer merge into main).
"""

import pandas as pd
import pytest

from explorer.paths import ROTATION_EFFECTS, SCORER_SEASONS_BY_YEAR
from explorer.field_calendar import parse_key
from explorer.schema import SequenceStep
from explorer.yields import SOURCES, CropYield, crop_yields, rotation_yields, season_yield

# full 200, rain-fed 80 at a mean deficit of 0.5  ->  k = (1 - 80/200) / 0.5 = 1.2
CROP = CropYield(unit="bu", full=200, none=80, k=1.2, mean_deficit=0.5, full_band=(0.9, 1.1), derived=False)


def test_reference_is_nass_level_and_midpoint_for_reduced():
    assert (CROP.reference("full"), CROP.reference("none"), CROP.reference("reduced")) == (200, 80, 140)


def test_mean_deficit_gives_the_nass_level():
    for irrigation, expected in [("none", 80), ("reduced", 140)]:
        s = season_yield(CROP, "sorghum", irrigation, [0.5] * 10, earlier=["corn"])
        assert s.yield_.v == expected and s.pct_rotation == 0 and s.effects == []


def test_weather_years_give_the_spread():
    s = season_yield(CROP, "sorghum", "none", [0.3, 0.4, 0.5, 0.6, 0.7], earlier=["corn"])
    assert s.yield_.p10 < s.yield_.v == 80 < s.yield_.p90


def test_full_irrigation_ignores_the_deficit():
    s = season_yield(CROP, "sorghum", "full", [0.9] * 5, earlier=["corn"])
    assert (s.yield_.p10, s.yield_.v, s.yield_.p90) == (180, 200, 220)


def test_yield_never_negative():
    s = season_yield(CROP, "sorghum", "none", [1.0, 1.0], earlier=["corn"])  # 1 - 1.2 * 1.0 < 0
    assert s.yield_.p10 == s.yield_.v == 0


def test_corn_after_corn_uses_the_literature_rate():
    rain_fed = season_yield(CROP, "corn", "none", [0.5] * 5, earlier=["corn"])
    irrigated = season_yield(CROP, "corn", "full", [], earlier=["corn"])
    assert (rain_fed.pct_rotation, irrigated.pct_rotation) == (-4.3, -1.7)
    assert all(e.source == "seifert_2017" for e in rain_fed.effects + irrigated.effects)


def test_soybean_after_soybean():
    assert season_yield(CROP, "soybean", "full", [], earlier=["soybean"]).pct_rotation == -7.5
    assert season_yield(CROP, "soybean", "full", [], earlier=["corn"]).pct_rotation == 0


def test_sunflower_too_soon_is_a_text_not_a_number():
    s = season_yield(CROP, "sunflower", "full", [], earlier=["sunflower", "corn", "sorghum"])
    assert s.pct_rotation == 0 and "Sclerotinia" in s.effects[0].text
    assert season_yield(CROP, "sunflower", "full", [], earlier=["sunflower", "corn", "sorghum", "corn"]).effects == []


def test_double_crop_is_flagged():
    s = season_yield(CROP, "soybean", "full", [], earlier=["winter_wheat"], double_crop=True)
    assert s.effects[-1].provenance == "assumption"


def test_source_titles_match_the_literature_table():
    e = pd.read_csv(ROTATION_EFFECTS)
    assert SOURCES["seifert_2017"].title in set(e["source"])
    assert SOURCES["ndsu_sunflower"].title in set(e["source"])


needs_scorer = pytest.mark.skipif(not SCORER_SEASONS_BY_YEAR.exists(), reason="scorer data not on this branch yet")


@needs_scorer
def test_levels_from_nass():
    crops = crop_yields()
    assert (crops["corn"].full, crops["corn"].none) == (203.2, 81.0)
    assert (crops["winter_wheat"].full, crops["winter_wheat"].none) == (64.3, 44.0)
    assert round(crops["sorghum"].full, 1) == 100.4 and round(crops["sorghum"].none, 1) == 61.0
    assert round(crops["sunflower"].none, 1) == 1265.6 and crops["sunflower"].derived


@needs_scorer
def test_every_scorer_rotation_gets_valid_yields():
    rotations = pd.read_csv(SCORER_SEASONS_BY_YEAR)["rotation"].unique()
    # 125 crop orders, plus a "+triticale" variant where a cover crop fits
    assert sum("+" not in r for r in rotations) == 125
    for rotation in rotations:
        crops, cover = parse_key(rotation)
        for irrigation in ("full", "reduced", "none"):
            seq = [SequenceStep(year=2027 + i, crop=c, irrigation=irrigation, cover=cover if i == 0 else None)
                   for i, c in enumerate(crops)]
            for s in rotation_yields(seq, history=["corn"] * 18):
                assert s.yield_.v > 0
                assert all(e.source is None or e.source in SOURCES for e in s.effects)
