"""Tests for the scorer's rotation rule: at most one Sclerotinia host (sunflower, soybean) per pass (NDSU A1995, p. 46)."""

import pandas as pd
import pytest

from crop_scorer.scoring.score_rotations import SCORES_FILE, follows_rotation_rules, parse_key, rank

WEIGHTS = {"water": 1, "risk": 1, "soil_health": 1, "nitrogen": 1}


@pytest.mark.parametrize("crops, ok", [
    (["corn", "sorghum", "winter_wheat"], True),  # no host
    (["corn", "sorghum", "sunflower"], True),  # one host
    (["corn", "sorghum", "soybean"], True),
    (["corn", "winter_wheat", "sunflower"], True),  # double crop: the pass is shorter, but we only simulate one pass
    (["corn", "soybean", "sunflower"], False),  # two hosts
    (["corn", "soybean", "soybean"], False),
    (["sunflower"] * 3, False),
])
def test_at_most_one_sclerotinia_host_per_pass(crops, ok):
    assert follows_rotation_rules(crops) == ok


def test_rule_breakers_are_ranked_behind_all_others():
    ranked = rank(pd.read_csv(SCORES_FILE), WEIGHTS)
    first_breaker = ranked["follows_rules"].idxmin()
    assert ranked.loc[:first_breaker - 1, "follows_rules"].all() and not ranked.loc[first_breaker:, "follows_rules"].any()
    # still ranked, so the farmer's own rotation can be shown even if it breaks the rule
    assert len(ranked) == 225 and "sunflower-sunflower-sunflower" in set(ranked["rotation"])
    top = ranked.head(10)["rotation"].map(lambda r: sum(c in ("sunflower", "soybean") for c in parse_key(r)[0]))
    assert (top <= 1).all()
