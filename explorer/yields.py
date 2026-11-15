"""WP3 Yield: expected yield per season, its spread over the weather years, and rotation effects.

Model, per season and weather year ``w``:

    yield(w) = Y_full * (1 - k * share * d(w)) * (1 + literature effect)

* ``Y_full`` / ``Y_none``: NASS mean yield with full irrigation / rain-fed (``mean_yield``, not the
  1.05 x yield goal, which is only for the N rate in WP4).
* ``d(w) = 1 - ETa/ETc``: rain-fed ET deficit of this very season in its rotation, from the scorer's
  water balance (one value per weather year, previous crop and soil water included).
* ``share``: part of the deficit that irrigation leaves open: full 0, reduced 0.5 (half the water), none 1.
* ``k``: yield response to the deficit (FAO-33 idea), calibrated per crop so that the mean rain-fed yield
  over all scorer seasons of the crop equals ``Y_none``. NASS sets the level, the weather years the spread.
* Full irrigation has no water stress, so its spread is the year-to-year range of NASS irrigated yields.

``yield_pct_rotation`` compares the season's mean yield with the crop's reference at the same irrigation
(NASS for full / none, their midpoint for reduced): water carry-over in the rotation plus literature effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal, Sequence

import numpy as np
import pandas as pd

from crop_scorer.scoring.yield_levels import yield_levels
from explorer.field_calendar import rotation_key
from explorer.paths import NASS_EXPECTED_YIELD, NASS_YIELDS, ROTATION_EFFECTS, SCORER_SEASONS_BY_YEAR
from explorer.schema import Effect, Irrigation, ProvenanceEntry, SequenceStep, Source, YieldSpread

UNCOVERED_DEFICIT: dict[str, float] = {"full": 0.0, "reduced": 0.5, "none": 1.0}  # reduced = 50 % of full

UNITS = {"BU / ACRE": "bu", "LB / ACRE": "lb"}
SPACING_YEARS_DEFAULT = 4

PROVENANCE: dict[str, ProvenanceEntry] = {
    "sequence.yield": ProvenanceEntry(label="modeled", source="nass_quickstats"),
    "sequence.yield_pct_rotation": ProvenanceEntry(label="modeled", source="scorer_water"),
}

# Titles and URLs as in rotation_effects_clean.csv and caleb_sources.md
SOURCES: dict[str, Source] = {
    "nass_quickstats": Source(
        title="USDA NASS Quick Stats, yields by irrigation practice (mean of the last 5 available years)",
        url="https://quickstats.nass.usda.gov",
        retrieved="2026-11-14",
    ),
    "seifert_2017": Source(
        title="Seifert, Roberts & Lobell 2017, Agron. J. 109(2):541 (summary: UNL CropWatch 2020)",
        url="https://cropwatch.unl.edu/2020/yield-penalties-continuous-corn-and-soybean-midwest-us/",
    ),
    "ndsu_sunflower": Source(
        title="NDSU Sunflower Production Guide",
        url="https://www.ndsu.edu/agriculture/extension/publications/sunflower-production-guide",
    ),
    "scorer_water": Source(title="Field Shift scorer: FAO-56 soil water balance on NASA POWER weather"),
}


@dataclass(frozen=True)
class CropYield:
    """Yield level and water response of one crop."""

    unit: Literal["bu", "lb"]
    full: float  # mean yield, full irrigation
    none: float  # mean yield, rain-fed
    k: float  # yield loss per unit of ET deficit
    mean_deficit: float  # mean rain-fed ET deficit of the crop over all scorer seasons
    full_band: tuple[float, float]  # P10 / P90 of irrigated yields relative to their mean
    derived: bool  # True if full or none is not a NASS value but derived (sorghum, sunflower)

    def reference(self, irrigation: str) -> float:
        """Mean yield of the crop at this irrigation over all seasons: NASS for full / none, midpoint for reduced."""
        return self.full * (1 - self.k * UNCOVERED_DEFICIT[irrigation] * self.mean_deficit)


@dataclass(frozen=True)
class SeasonYield:
    yield_: YieldSpread
    pct_rotation: float
    effects: list[Effect]


@cache
def scorer_seasons(path: Path = SCORER_SEASONS_BY_YEAR) -> pd.DataFrame:
    """The scorer's seasons per weather year, with the rain-fed ET deficit ``d``."""
    s = pd.read_csv(path)
    if not ((s["etc_mm"] > 0) & (s["eta_mm"] >= 0) & (s["eta_mm"] <= s["etc_mm"] + 0.5)).all():
        raise ValueError(f"{path.name}: expected 0 <= eta_mm <= etc_mm and etc_mm > 0")
    return s.assign(d=(1 - s["eta_mm"] / s["etc_mm"]).clip(0, 1))


def season_deficits(rotation: str, path: Path = SCORER_SEASONS_BY_YEAR) -> dict[int, list[float]]:
    """Rain-fed ET deficit per weather year for each season (0, 1, ...) of a scorer rotation like 'corn-corn-corn'."""
    s = scorer_seasons(path)
    rows = s[s["rotation"] == rotation]
    if rows.empty:
        raise KeyError(f"rotation '{rotation}' is not in {path.name}")
    return {int(season): g["d"].tolist() for season, g in rows.groupby("season")}


def _irrigated_band(yields_path: Path) -> dict[str, tuple[float, float]]:
    # Year-to-year range of NASS irrigated yields (most local level with >= 5 years), relative to their mean.
    y = pd.read_csv(yields_path)
    y = y[y["practice"] == "irrigated"]
    bands, pooled = {}, []
    for crop, g in y.groupby("crop"):
        for level in ("county", "district", "state"):
            values = g.loc[g["level"] == level, "value"].dropna()
            if len(values) >= 5:
                rel = values / values.mean()
                bands[crop] = (float(rel.quantile(0.1)), float(rel.quantile(0.9)))
                pooled += rel.tolist()
                break
    # assumption: crops without such a series vary like the pooled irrigated crops
    bands["_pooled"] = (float(np.quantile(pooled, 0.1)), float(np.quantile(pooled, 0.9)))
    return bands


@cache
def crop_yields(
    expected_path: Path = NASS_EXPECTED_YIELD,
    yields_path: Path = NASS_YIELDS,
    seasons_path: Path = SCORER_SEASONS_BY_YEAR,
) -> dict[str, CropYield]:
    nass = pd.read_csv(expected_path).set_index(["crop", "practice"])
    mean_deficit = scorer_seasons(seasons_path).groupby("crop")["d"].mean()
    bands = _irrigated_band(yields_path)

    out = {}
    # same levels as the scorer's N need (K-State expected yield), incl. the derived sorghum and sunflower levels
    for crop, (full, none, derived) in yield_levels(expected_path).items():
        unit = UNITS[nass.loc[crop, "unit"].iloc[0]]
        d = float(mean_deficit[crop])
        out[crop] = CropYield(
            unit=unit,
            full=full,
            none=none,
            k=(1 - none / full) / d,
            mean_deficit=d,
            full_band=bands.get(crop, bands["_pooled"]),
            derived=derived,
        )
    return out


@cache
def _effect_rows(path: Path = ROTATION_EFFECTS) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"value": float})


def _literature_value(previous: str, crop: str, condition_start: str, path: Path = ROTATION_EFFECTS) -> float:
    e = _effect_rows(path)
    hit = e[(e["previous_crop"] == previous) & (e["crop"] == crop) & e["condition"].str.startswith(condition_start)]
    if hit.empty:
        raise KeyError(f"{path.name}: no row {previous} -> {crop} with condition '{condition_start}...'")
    return float(hit["value"].iloc[0])


def literature_effects(crop: str, irrigation: str, earlier: Sequence[str]) -> tuple[float, list[Effect]]:
    """Yield change (fraction) and effect texts from the literature table, given the crops before this season."""
    previous = earlier[-1] if earlier else None
    change, effects = 0.0, []
    if crop == "corn" and previous == "corn":
        condition = "rainfed" if irrigation == "none" else "irrigated"
        pct = _literature_value("corn", "corn", condition)
        change += pct / 100
        effects.append(Effect(text=f"Corn after corn: {pct:+.1f} % yield ({condition}, Corn Belt study)",
                              source="seifert_2017", provenance="rule"))
    if crop == "soybean" and previous == "soybean":
        pct = _literature_value("soybean", "soybean", "1st year")
        change += pct / 100
        effects.append(Effect(text=f"Soybean after soybean: {pct:+.1f} % yield (Corn Belt study)",
                              source="seifert_2017", provenance="rule"))
    if crop == "sunflower":
        e = _effect_rows()
        row = e[(e["crop"] == "sunflower") & (e["effect"] == "min_years_between")]
        years = int(row["value"].iloc[0]) if not row.empty else SPACING_YEARS_DEFAULT
        if "sunflower" in earlier[-(years - 1):]:
            effects.append(Effect(text=f"Sunflower again within {years} years: Sclerotinia risk, not quantified",
                                  source="ndsu_sunflower", provenance="rule"))
    return change, effects


def season_yield(
    cy: CropYield,
    crop: str,
    irrigation: Irrigation,
    deficits: Sequence[float],
    earlier: Sequence[str],
    double_crop: bool = False,
) -> SeasonYield:
    """Yield of one season: mean and P10 / P90 over the weather years, rotation effect in %, effect texts."""
    lit_change, effects = literature_effects(crop, irrigation, earlier)
    reference = cy.reference(irrigation)

    if irrigation == "full":
        v = cy.full * (1 + lit_change)
        p10, p90 = v * cy.full_band[0], v * cy.full_band[1]
    else:
        share = UNCOVERED_DEFICIT[irrigation]
        d = np.asarray(deficits, dtype=float)
        if d.size == 0:
            raise ValueError(f"{crop}: no weather years for the water deficit")
        per_year = np.clip(cy.full * (1 - cy.k * share * d), 0, None) * (1 + lit_change)
        v = float(per_year.mean())
        p10, p90 = (float(x) for x in np.percentile(per_year, [10, 90]))
        water = per_year.mean() / (1 + lit_change) / reference - 1
        if abs(water) >= 0.01:
            effects.append(Effect(text=f"Rain-fed water supply in this rotation: {water * 100:+.1f} % vs. the crop average",
                                  source="scorer_water", provenance="modeled"))

    if double_crop:
        effects.append(Effect(text=f"Double crop after {earlier[-1]}: late planting, yield not reduced for it (no data)",
                              source=None, provenance="assumption"))
    if cy.derived:
        effects.append(Effect(text=f"No NASS yields by irrigation for {crop}: irrigated vs. rain-fed level derived",
                              source="nass_quickstats", provenance="assumption"))

    # the mean can fall outside P10..P90 for a very skewed spread; keep the contract's p10 <= v <= p90
    spread = YieldSpread(v=round(v, 1), p10=round(min(p10, v), 1), p90=round(max(p90, v), 1), unit=cy.unit)
    return SeasonYield(yield_=spread, pct_rotation=round((v / reference - 1) * 100, 1), effects=effects)


def rotation_yields(
    sequence: Sequence[SequenceStep],
    history: Sequence[str],
    seasons_path: Path = SCORER_SEASONS_BY_YEAR,
) -> list[SeasonYield]:
    """Yields of all seasons of a scorer rotation. ``history``: crops before the rotation, oldest first (CDL)."""
    # the scorer's key: crops joined by "-", plus "+triticale" if the scorer sowed a cover crop in the pass
    # (the cover uses soil water, so the deficits of the variant with cover differ from the one without)
    cover = next((s.cover for s in sequence if s.cover), None)
    rotation = rotation_key([s.crop for s in sequence], cover)
    deficits = season_deficits(rotation, seasons_path)
    if len(deficits) != len(sequence):
        raise ValueError(f"rotation '{rotation}': {len(sequence)} seasons, scorer has {len(deficits)}")
    crops = crop_yields(seasons_path=seasons_path)
    out = []
    for i, step in enumerate(sequence):
        earlier = [*history, *(s.crop for s in sequence[:i])]
        double_crop = i > 0 and step.year == sequence[i - 1].year
        out.append(season_yield(crops[step.crop], step.crop, step.irrigation, deficits[i], earlier, double_crop))
    return out
