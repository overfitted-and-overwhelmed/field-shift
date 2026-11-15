"""Re-rank all candidate rotations with the farmer's own weights (the slider backend).

Uses the scorer's own ``rank`` on the stored normalised scores, so no simulation is re-run and the formula
is not duplicated.
"""

from __future__ import annotations

import math
from functools import cache
from typing import Any, Mapping

import pandas as pd

from advisor.data import DEFAULT_WEIGHTS
from advisor.lookup import _brief
from crop_scorer.scoring.score_rotations import CRITERIA, rank
from explorer.field_calendar import load_scorer_scores


def validate_weights(weights: Mapping[str, float] | None = None) -> dict[str, float]:
    """The weights as floats for every criterion, in scorer order.

    None gives equal weights. A criterion that is left out gets weight 0 (not counted), like in the scorer.
    Only the ratio matters: ``{"water": 2, "risk": 1}`` and ``{"water": 4, "risk": 2}`` rank the same.
    """
    if weights is None:
        return {name: float(w) for name, w in DEFAULT_WEIGHTS.items()}
    unknown = sorted(set(weights) - set(CRITERIA))
    if unknown:
        raise ValueError(f"Unknown criteria {unknown}. Known criteria: {', '.join(CRITERIA)}.")
    result: dict[str, float] = {}
    for name in CRITERIA:
        value = weights.get(name, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"Weight '{name}' must be a finite number, got {value!r}.")
        if value < 0:
            raise ValueError(f"Weight '{name}' must not be negative, got {value}.")
        result[name] = float(value)
    if sum(result.values()) <= 0:
        raise ValueError("At least one weight must be greater than 0.")
    return result


@cache
def _ranked(items: tuple[tuple[str, float], ...]) -> pd.DataFrame:
    return rank(load_scorer_scores(), dict(items)).set_index("rotation")


def ranked_scores(weights: Mapping[str, float] | None = None) -> pd.DataFrame:
    """All candidates ranked with these weights, indexed by rotation id (has ``rank``, ``total_score``).

    Do not modify the returned table, it is cached.
    """
    return _ranked(tuple(validate_weights(weights).items()))


def rerank(weights: Mapping[str, float] | None = None, top_n: int = 10) -> dict[str, Any]:
    """The ``top_n`` best rotations for these weights, best first.

    ``rank_all`` and ``total_score`` of each rotation are the values for these weights; ``pick`` is still the
    place in explorer.json. ``score_parts`` do not depend on the weights.
    """
    if top_n < 1:
        raise ValueError(f"top_n must be at least 1, got {top_n}")
    w = validate_weights(weights)
    ranked = ranked_scores(w)
    total_w = sum(w.values())
    rotations = []
    for rotation_id, row in ranked.head(top_n).iterrows():
        rotations.append(
            _brief(rotation_id) | {"rank_all": int(row["rank"]), "total_score": round(float(row["total_score"]), 4)}
        )
    return {
        "weights": w,
        "weight_shares": {k: round(v / total_w, 4) for k, v in w.items()},
        "n_rotations": len(ranked),
        "rotations": rotations,
    }
