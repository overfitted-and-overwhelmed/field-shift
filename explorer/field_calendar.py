"""WP5 Field Calendar (adapter): what is on the field, and when, as decided by the scorer.

The scorer (``crop_scorer/scoring/score_rotations.py``) is the single source of truth for seasons:
it picks sowing and harvest dates (``water_usage.build_timeline``) and scores water, risk and soil
health on exactly these days. We do NOT compute dates ourselves, so the explorer always shows the
days the scores are about. Double crops (two harvests in one year) and skipped years come from the
scorer as they are.

What this module does:
* ``place_seasons``: take one pass of a scorer rotation and move it to the display years, so the first
  sowing falls into ``start_year`` (the scorer replays the rotation on past weather, 1991-2025).
* ``monthly_kinds``: crop or bare per month, from the scorer's monthly table.
* ``summarize``: bare months per year and same-crop repeats.

A rotation is identified like the scorer does it: crops joined by "-", e.g. "winter_wheat-soybean-sorghum".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import cache
from pathlib import Path
from typing import Sequence

import pandas as pd

from explorer.paths import SCORER_MONTHLY, SCORER_SCORES, SCORER_SEASONS_BY_YEAR

FALLOW = "fallow"  # the scorer's name for a day or month without crop


def rotation_key(crops: Sequence[str]) -> str:
    """Scorer id of a rotation: ``["corn", "soybean"]`` -> ``"corn-soybean"``."""
    return "-".join(crops)


# @cache: each file is read once, later calls reuse the table.
@cache
def load_scorer_seasons(path: Path = SCORER_SEASONS_BY_YEAR) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["sow_date", "harvest_date"])


@cache
def load_scorer_monthly(path: Path = SCORER_MONTHLY) -> pd.DataFrame:
    return pd.read_csv(path)


@cache
def load_scorer_scores(path: Path = SCORER_SCORES) -> pd.DataFrame:
    return pd.read_csv(path)


def scorer_rows(table: pd.DataFrame, rotation: str, file: str) -> pd.DataFrame:
    rows = table[table["rotation"] == rotation]
    if rows.empty:
        raise KeyError(f"rotation '{rotation}' is not in the scorer's {file}")
    return rows


@dataclass(frozen=True)
class PlacedSeason:
    """One season of the rotation, moved to the display years."""

    index: int  # 0, 1, 2 ... position in the rotation (the scorer's "season")
    crop: str
    plant_date: date
    harvest_date: date  # like the scorer: the harvest day itself is not part of the season

    @property
    def harvest_year(self) -> int:
        return self.harvest_date.year


def reference_start_year(rotation: str, start_year: int) -> int:
    """The scorer run whose dates we show: the latest one with the same leap-year rhythm as ``start_year``.

    The scorer counts days from 1 January, so in leap years its dates sit one day earlier. A run that is
    a multiple of 4 years before ``start_year`` has the same rhythm, so moving it keeps every date exact.
    """
    runs = scorer_rows(load_scorer_seasons(), rotation, "seasons table")["start_year"].unique()
    same_rhythm = [int(y) for y in runs if (start_year - y) % 4 == 0]
    if not same_rhythm:
        raise ValueError(f"rotation '{rotation}': no scorer run with the leap-year rhythm of {start_year}")
    return max(same_rhythm)


def place_seasons(rotation: str, start_year: int) -> list[PlacedSeason]:
    """The seasons of one pass of ``rotation``, with the first sowing in ``start_year``."""
    ref = reference_start_year(rotation, start_year)
    rows = scorer_rows(load_scorer_seasons(), rotation, "seasons table")
    rows = rows[rows["start_year"] == ref].sort_values("season")
    shift = pd.DateOffset(years=start_year - ref)  # a multiple of 4 years, see reference_start_year
    return [
        PlacedSeason(int(r.season), r.crop, (r.sow_date + shift).date(), (r.harvest_date + shift).date())
        for r in rows.itertuples()
    ]


def monthly_kinds(rotation: str, start_year: int) -> list[dict]:
    """One entry per month of the window: ``{"m": "YYYY-MM", "kind": "crop" | "bare", "crop": ... | None}``.

    The window is the scorer's: from the month of the first sowing to the month of the day before the
    last harvest. The crop of a month is what the scorer says stands there on most days.
    """
    rows = scorer_rows(load_scorer_monthly(), rotation, "monthly table").sort_values(["year_offset", "month"])
    return [
        {
            "m": f"{start_year + int(r.year_offset)}-{int(r.month):02d}",
            "kind": "bare" if r.crop == FALLOW else "crop",
            "crop": None if r.crop == FALLOW else r.crop,
        }
        for r in rows.itertuples()
    ]


def summarize(rotation: str, previous_crop: str) -> dict:
    """Calendar part of ``schema.Summary``.

    * ``bare_months``: the scorer's bare share of the window (fallow days / window days), as months per year.
    * ``same_crop_repeats``: seasons with the same crop as the one before (season 0 compares to ``previous_crop``).
    """
    bare_share = float(scorer_rows(load_scorer_scores(), rotation, "scores table")["bare_share"].iloc[0])
    crops = [previous_crop, *rotation.split("-")]
    return {
        "bare_months": bare_share * 12,
        "same_crop_repeats": sum(a == b for a, b in zip(crops, crops[1:])),
    }
