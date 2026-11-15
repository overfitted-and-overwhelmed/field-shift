"""Data access of the advisor: one place that reads ``explorer.json`` and ``rotation_scores.csv``.

* ``explorer.json`` is validated with :class:`explorer.schema.ExplorerExport`. It holds the current
  rotation and the top picks with full detail (seasons, spreads, months).
* ``rotation_scores.csv`` (via ``explorer.field_calendar.load_scorer_scores``) holds all candidates
  with scores only. It is ranked with the scorer's own ``rank`` function.

Everything is read once (``@cache``), later calls reuse the tables. Do not modify the returned objects.
"""

from __future__ import annotations

from difflib import get_close_matches
from functools import cache
from pathlib import Path

import pandas as pd

from crop_scorer.scoring.score_rotations import CRITERIA, rank
from explorer.field_calendar import load_scorer_scores
from explorer.paths import REPO_ROOT, SCORER_SCORES
from explorer.schema import ExplorerExport, load_explorer

EXPLORER_JSON = REPO_ROOT / "explorer" / "examples" / "explorer.json"

# Equal weights for all scorer criteria, like crop_scorer/scoring/ui_input_mock.json (only the ratio matters).
DEFAULT_WEIGHTS: dict[str, float] = {name: 1 for name in CRITERIA}


class UnknownRotationError(ValueError):
    """The rotation id is in neither explorer.json nor the scores table."""

    def __init__(self, rotation_id: str, close_matches: list[str]):
        self.rotation_id = rotation_id
        self.close_matches = close_matches
        hint = f" Close matches: {', '.join(close_matches)}." if close_matches else " No close matches found."
        super().__init__(f"Unknown rotation '{rotation_id}'.{hint}")


class DetailNotAvailableError(ValueError):
    """The rotation exists but only with scores, the requested detail is in explorer.json only."""


@cache
def load_export(path: Path = EXPLORER_JSON) -> ExplorerExport:
    """The validated explorer.json (current rotation + top picks, full detail)."""
    return load_explorer(path)


@cache
def load_scores(path: Path = SCORER_SCORES) -> pd.DataFrame:
    """All candidate rotations ranked with ``DEFAULT_WEIGHTS``, indexed by rotation id."""
    return rank(load_scorer_scores(path), DEFAULT_WEIGHTS).set_index("rotation")


def known_ids() -> list[str]:
    """Every rotation id the advisor can answer for."""
    return sorted(set(load_scores().index) | {r.id for r in load_export().rotations})


def check_id(rotation_id: str) -> str:
    """Return the id if known, otherwise raise :class:`UnknownRotationError` with close matches."""
    ids = known_ids()
    if rotation_id not in ids:
        raise UnknownRotationError(rotation_id, get_close_matches(str(rotation_id), ids, n=5, cutoff=0.6))
    return rotation_id
