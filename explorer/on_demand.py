"""Score a rotation the scorer did not precompute, e.g. one the farmer built with a cover crop in one gap only.

The scorer precomputes every three-crop rotation without a cover and with a cover in every gap where it fits
(``data/processed/rotation_scores``). The farmer can also choose the gaps one by one ("+triticale_1" = cover only
after the first crop). Such a rotation is scored here with the scorer's own functions (about 1.5 s), normalised
against the precomputed rotations (so its scores are on the same scale) and added to the explorer's scorer tables
for this process. Nothing is written to disk.
"""

from __future__ import annotations

import threading

from crop_scorer.scoring.score_rotations import (
    COVER_CROP,
    cover_gaps,
    monthly_table,
    normalize,
    rotation_days,
    rotation_key,
    score_days,
    season_by_year,
)

import pandas as pd

from explorer.field_calendar import add_scorer_rows, load_scorer_scores, parse_key, scorer_reference_scores
from explorer.paths import SCORER_MONTHLY, SCORER_SCORES, SCORER_SEASONS_BY_YEAR

_LOCK = threading.Lock()  # two requests for the same new rotation must not score it twice


def canonical_key(key: str) -> str:
    """The scorer's spelling of ``key``: a cover in every gap is "+triticale", none is no suffix."""
    crops, _ = parse_key(key)
    return rotation_key(crops, cover_gaps(key))


def ensure_scored(key: str) -> str:
    """Make sure the scorer tables have ``key``; score it now if not. Returns the canonical key.

    Raises ValueError if a chosen gap has no room for a cover crop (the result would be the rotation without one).
    """
    key = canonical_key(key)
    with _LOCK:
        if key in set(load_scorer_scores()["rotation"]):
            return key
        crops, _ = parse_key(key)
        gaps = cover_gaps(key)
        days = rotation_days(crops, gaps)
        if gaps is not False:
            wanted = [i for i, g in enumerate(gaps)] if gaps is True else [i for i, g in enumerate(gaps) if g]
            covered = set(((days.loc[days["crop"] == COVER_CROP, "segment"] - 1) // 2).unique())
            missing = [i for i in wanted if i not in covered]
            if gaps is True and not covered or gaps is not True and missing:
                after = ", ".join(crops[i] for i in (missing or wanted))
                raise ValueError(f"rotation '{key}' is not scored (no cover crop fits after {after})")
        row = normalize(pd.DataFrame([score_days(crops, days, gaps)]), scorer_reference_scores())
        row["rotation"] = key  # score_days writes the key from the flags; keep the canonical one
        seasons = season_by_year(days)
        monthly = monthly_table(days)
        add_scorer_rows(SCORER_SCORES, row)
        add_scorer_rows(SCORER_SEASONS_BY_YEAR, seasons.assign(rotation=key)[["rotation", *seasons.columns]])
        add_scorer_rows(SCORER_MONTHLY, monthly.assign(rotation=key)[["rotation", *monthly.columns]])
        return key
