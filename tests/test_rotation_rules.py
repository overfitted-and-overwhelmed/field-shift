"""Tests for the scorer's rotation rule: Sclerotinia hosts (sunflower, soybean) at most every 3 years (NDSU A1995, p. 46)."""

import pandas as pd
import pytest

from crop_scorer.scoring.score_rotations import SCORES_FILE, follows_rotation_rules, parse_key, rank

WEIGHTS = {"water": 1, "risk": 1, "soil_health": 1, "nitrogen": 1}


@pytest.mark.parametrize("crops, cycle_days, ok", [
    (["corn", "soybean", "sorghum"], 1095, True),  # no sunflower
    (["corn", "sorghum", "sunflower"], 1095, True),  # one host in 3 years
    (["corn", "sorghum", "soybean"], 1095, True),
    (["corn", "soybean", "sunflower"], 1095, False),  # two hosts in 3 years
    (["corn", "soybean", "soybean"], 1095, False),
    (["sunflower"] * 3, 1095, False),
    (["corn", "winter_wheat", "sunflower"], 730, False),  # one host, but the double crop makes it every 2 years
])
def test_sclerotinia_hosts_at_most_every_three_years(crops, cycle_days, ok):
    assert follows_rotation_rules(crops, cycle_days) == ok


def test_rule_breakers_are_ranked_behind_all_others():
    ranked = rank(pd.read_csv(SCORES_FILE), WEIGHTS)
    first_breaker = ranked["follows_rules"].idxmin()
    assert ranked.loc[:first_breaker - 1, "follows_rules"].all() and not ranked.loc[first_breaker:, "follows_rules"].any()
    # still ranked, so the farmer's own rotation can be shown even if it breaks the rule
    assert len(ranked) == 225 and "sunflower-sunflower-sunflower" in set(ranked["rotation"])
    top = ranked.head(10)["rotation"].map(lambda r: sum(c in ("sunflower", "soybean") for c in parse_key(r)[0]))
    assert (top <= 1).all()
