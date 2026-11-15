"""Tests for WP4 Nitrogen Adapter (explorer/nitrogen.py)."""

import pytest

from crop_scorer.scoring.nitrogen import LB_PER_AC_TO_KG_PER_HA, season_n_need_kg
from explorer.nitrogen import season_nitrogen


def test_n_is_the_scorers_k_state_need_in_lb():
    seasons = season_nitrogen("winter_wheat-corn-sorghum")
    expected = [season_n_need_kg("winter_wheat", None), season_n_need_kg("corn", "winter_wheat"), season_n_need_kg("sorghum", "corn")]
    assert [s.n_lb for s in seasons] == pytest.approx([kg / LB_PER_AC_TO_KG_PER_HA for kg in expected], abs=0.1)


def test_soybean_gets_no_fertilizer_and_credits_the_next_crop():
    soybean, corn, _ = season_nitrogen("soybean-corn-sorghum")
    assert (soybean.n_lb, soybean.n_adj_lb) == (0, 0)
    assert [e.provenance for e in soybean.effects] == ["assumption"]
    assert corn.n_adj_lb == pytest.approx(-40, abs=0.1)  # K-State MF2586: warm-season crop after soybean


def test_cover_crop_adds_n_to_the_next_crop():
    without = season_nitrogen("sunflower-sorghum-corn")
    with_cover = season_nitrogen("sunflower-sorghum-corn+triticale")
    assert with_cover[1].n_adj_lb - without[1].n_adj_lb == pytest.approx(27.5, abs=0.1)
    assert [e.source for e in with_cover[1].effects] == ["sare_2007"]
    assert with_cover[0].effects == []  # the first season has no cover crop before it
