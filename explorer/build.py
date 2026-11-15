"""WP7 Pipeline & Export (first version): build explorer.json from the scorer and our modules.

    uv run python -m explorer.build          # writes explorer/examples/explorer.json + scorer/response.json

Steps:
1. Field, crops, climate (WP1).
2. Which rotations: the field's current rotation (last crops in the CDL history) plus the scorer's
   top 3 for the given weights. Until the scorer has an API we read its CSV exports and build the
   scorer response (``ScorerResponse``) from them.
3. Per rotation: dates (WP5 calendar adapter), water (WP2), frost/heat (WP6), yield (WP3), nitrogen (WP4).
4. Validate everything against ``schema.py`` and write the files.

Irrigation level per season: the scorer has none (it scores the rain-fed irrigation need), so we use
DEFAULT_IRRIGATION for every season. That is an assumption until the UI lets the farmer choose.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, get_args

from crop_scorer.scoring.nitrogen import LB_PER_AC_TO_KG_PER_HA
from crop_scorer.scoring.score_rotations import UI_INPUT_FILE, rank

from explorer import field_climate, nitrogen, yields
from explorer.field_calendar import (
    COVER_CROPS,
    load_scorer_scores,
    scorer_reference_scores,
    monthly_kinds,
    parse_key,
    place_seasons,
    rotation_key,
    summarize,
)
from explorer.frost_heat import monthly_stress
from explorer.on_demand import ensure_scored
from explorer.schema import (
    CONTRACT_VERSION,
    ExplorerExport,
    Irrigation,
    MainCropId,
    MonthDetail,
    ProvenanceEntry,
    Rotation,
    ScoreParts,
    ScorerResponse,
    ScorerRotation,
    ScorerSeason,
    SeasonDetail,
    Source,
    Summary,
)
from explorer.water import MM_PER_IN, monthly_water, season_irrigation

EXAMPLES = Path(__file__).parent / "examples"
DEFAULT_IRRIGATION: Irrigation = "full"
N_PICKS = 3
DAYS_PER_YEAR = 365.25
# the scorer's values per pass (rotation_scores.csv). Its frost_days is left out: days below the crop's optimum,
# not frost (real frost = kill_days).
KPI_COLUMNS = ["risk_per_crop_day", "bare_share", "window_days", "cycle_days", "heat_days", "kill_days"]
KPI_MM_COLUMNS = {"water_mm_per_day": "water_in_per_day", "irrigation_mm": "irrigation_in"}  # converted to inches
KPI_KG_COLUMNS = {"n_fertilizer_kg": "n_lb"}  # kg N/ha -> lb N/acre
# per year of the rotation: pass value / cycle years (first sowing to the first sowing of the next pass), so passes
# of different length compare. Not per window day x 365.25: the window leaves out the gap after the last crop.
KPI_PER_YEAR = {
    "irrigation_in_per_year": ("irrigation_mm", MM_PER_IN),
    "n_lb_per_year": ("n_fertilizer_kg", LB_PER_AC_TO_KG_PER_HA),
}

PROVENANCE: dict[str, ProvenanceEntry] = {
    "rotations.*": ProvenanceEntry(label="modeled", source="scorer"),
    "sequence.plant_date": ProvenanceEntry(label="rule", source="scorer"),
    "sequence.harvest_date": ProvenanceEntry(label="rule", source="scorer"),
    "sequence.irrigation": ProvenanceEntry(label="assumption", source=None),
    "sequence.irr_in": ProvenanceEntry(label="modeled", source="scorer_water"),
    "monthly.kind": ProvenanceEntry(label="rule", source="scorer"),
    "monthly.et_in": ProvenanceEntry(label="modeled", source="scorer_water"),
    "monthly.rain_in": ProvenanceEntry(label="measured", source="nasa_power"),
    "monthly.irr_in": ProvenanceEntry(label="modeled", source="scorer_water"),
    "monthly.heat_years_pct": ProvenanceEntry(label="modeled", source="scorer_risk"),
    # our rule on the scorer's thresholds: below the optimum for at least half the day (assumption)
    "monthly.cold_stress_years_pct": ProvenanceEntry(label="assumption", source="scorer_risk"),
    "monthly.kill_years_pct": ProvenanceEntry(label="modeled", source="scorer_risk"),
    "summary.bare_months": ProvenanceEntry(label="rule", source="scorer"),
}

SOURCES: dict[str, Source] = {
    "scorer": Source(title="Field Shift scorer: seasons from the USDA NASS crop calendar, scores per rotation"),
    "scorer_risk": Source(title="Field Shift scorer: daily temperature risk from NASA POWER and Ecocrop limits"),
}

LABELS = {crop: c.label for crop, c in field_climate.CROPS.items()}


def scorer_rotation(key: str, start_year: int, *, is_current: bool, pick: int | None,
                    total: float | None, parts: dict, kpi: dict,
                    cover_variant: ScorerRotation | None = None) -> ScorerRotation:
    """The scorer's view of one rotation, with its seasons moved to the display years."""
    crops, cover = parse_key(key)
    seasons = [
        ScorerSeason(year=s.harvest_year, crop=s.crop, irrigation=DEFAULT_IRRIGATION, cover=s.cover,
                     plant_date=s.plant_date, harvest_date=s.harvest_date)
        for s in place_seasons(key, start_year)
    ]
    name = " · ".join(LABELS[c] for c in crops)
    covered = [s for s in seasons[:-1] if s.cover]  # no gap after the last season
    if covered and len(covered) < len(seasons) - 1:  # a cover in some gaps only (the farmer's choice)
        name += f" + {cover} after " + ", ".join(LABELS[s.crop].lower() for s in covered)
    elif cover:
        name += f" + {cover} cover"
    return ScorerRotation(
        id=key, is_current=is_current, rank=pick, name=name,
        short="Your rotation" if is_current else f"Pick #{pick}",
        sequence=seasons, score=total, score_parts=ScoreParts(**parts), kpi=kpi, cover_variant=cover_variant,
    )


def scorer_response(field_history: list[str], start_year: int, weights: dict[str, float], *,
                    crops: Iterable[str] | None = None, n_picks: int = N_PICKS,
                    current: str | None = None) -> ScorerResponse:
    """Current rotation + top picks, as the scorer would answer for these weights.

    ``crops``: if given, picks only use these main crops (the farmer's choice). The current rotation is
    always included, whatever its crops.
    ``current``: a rotation key the farmer built (e.g. "corn-soybean-sorghum+triticale"). It replaces the
    rotation from the crop history as the current one; the picks do not change (they never repeat either one).
    """
    reference = scorer_reference_scores()  # the scorer's precomputed rotations: the picks come from these
    length = len(parse_key(reference["rotation"].iloc[0])[0])
    if current is not None:
        if len(parse_key(current)[0]) != length:
            raise ValueError(f"rotation '{current}' is not scored; the scorer has {length}-crop rotations")
        current = ensure_scored(current)  # e.g. a cover crop in one gap only: scored now, same scale
    keys = set(reference["rotation"]) | ({current} if current else set())
    scores = load_scorer_scores()
    ranked = rank(scores[scores["rotation"].isin(keys)], weights).set_index("rotation")
    # only main crops count: the CDL history can also contain e.g. "fallow/idle cropland"
    main_crops = [c for c in field_history if c in get_args(MainCropId)]
    if len(main_crops) < length:
        raise ValueError(f"field history has only {len(main_crops)} main crops, need {length} for the current rotation")
    history_key = rotation_key(main_crops[-length:])
    current = current or history_key
    allowed = None if crops is None else set(crops)
    candidates = [r for r in ranked.index
                  if r not in (current, history_key) and r in set(reference["rotation"])
                  and (allowed is None or set(parse_key(r)[0]) <= allowed)]
    if not candidates:
        raise ValueError(f"no scored rotation uses only the crops {sorted(allowed or [])}")
    picks = candidates[:n_picks]

    def build(key: str, is_current: bool, pick: int | None, with_variant: bool = True) -> ScorerRotation:
        row = ranked.loc[key]
        crops, cover = parse_key(key)
        toggled = rotation_key(crops, None if cover else COVER_CROPS[0])
        # the scorer only has a cover variant where a gap fits a cover crop
        variant = build(toggled, is_current, pick, False) if with_variant and toggled in ranked.index else None
        kpi = ({c: float(row[c]) for c in KPI_COLUMNS}
               | {ours: float(row[mm]) / MM_PER_IN for mm, ours in KPI_MM_COLUMNS.items()}
               | {ours: float(row[kg]) / LB_PER_AC_TO_KG_PER_HA for kg, ours in KPI_KG_COLUMNS.items()}
               | {ours: float(row[col]) / factor / (float(row["cycle_days"]) / DAYS_PER_YEAR)
                  for ours, (col, factor) in KPI_PER_YEAR.items()}
               | {"rank_all": int(row["rank"]), "n_rotations": len(reference)})
        parts = {name: row[f"{name}_score"] for name in ScoreParts.model_fields}  # one per scorer criterion
        return scorer_rotation(key, start_year, is_current=is_current, pick=pick,
                               total=round(float(row["total_score"]), 4),
                               parts={k: round(float(v), 4) for k, v in parts.items()}, kpi=kpi,
                               cover_variant=variant)

    rotations = [build(current, True, None)] + [build(k, False, i) for i, k in enumerate(picks, 1)]
    return ScorerResponse(placeholder=False, rotations=rotations)


def explorer_rotation(sr: ScorerRotation, start_year: int, history: list[str], previous_crop: str) -> Rotation:
    """Add our data (water, yield, months, summary) to a scorer rotation."""
    key = sr.id
    irrigation = [s.irrigation for s in sr.sequence]
    placed = place_seasons(key, start_year)
    irr = season_irrigation(key, irrigation)
    ylds = yields.rotation_yields(sr.sequence, history=history, rotation=key)
    n = nitrogen.season_nitrogen(key)
    sequence = [
        SeasonDetail(**s.model_dump(), irr_in=irr[i], yield_=y.yield_, n_lb=n[i].n_lb, n_adj_lb=n[i].n_adj_lb,
                     yield_pct_rotation=y.pct_rotation, effects=y.effects + n[i].effects)
        for i, (s, y) in enumerate(zip(sr.sequence, ylds))
    ]
    kinds = monthly_kinds(key, start_year)
    water = {w["m"]: w for w in monthly_water(key, start_year, placed, irrigation)}
    stress = {x["m"]: x for x in monthly_stress(key, start_year)}
    monthly = [MonthDetail(**k, **{f: water[k["m"]][f] for f in ("et_in", "rain_in", "irr_in")},
                           **{f: stress[k["m"]][f] for f in ("heat_years_pct", "cold_stress_years_pct", "kill_years_pct")})
               for k in kinds]
    s = summarize(key, previous_crop)
    summary = Summary(bare_months=round(s["bare_months"], 2), same_crop_repeats=s["same_crop_repeats"])
    variant = sr.cover_variant and explorer_rotation(sr.cover_variant, start_year, history, previous_crop)
    return Rotation(**sr.model_dump(exclude={"sequence", "cover_variant"}), placeholder=False, sequence=sequence,
                    monthly=monthly, summary=summary, cover_variant=variant)


def build_explorer(weights: dict[str, float], *, crops: Iterable[str] | None = None,
                   n_picks: int = N_PICKS, current: str | None = None) -> tuple[ExplorerExport, ScorerResponse]:
    field = field_climate.build_field()
    history = [h.crop for h in field.crop_history]
    start = field.rotation_start_year
    response = scorer_response(history, start, weights, crops=crops, n_picks=n_picks, current=current)
    rotations = [explorer_rotation(r, start, history, field.previous_crop) for r in response.rotations]
    export = ExplorerExport(
        contract_version=CONTRACT_VERSION,
        generated_at=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        field=field,
        crops=field_climate.build_crops(),
        climate=field_climate.build_climate(),
        rotations=rotations,
        provenance=field_climate.PROVENANCE | yields.PROVENANCE | nitrogen.PROVENANCE | PROVENANCE,
        sources=field_climate.SOURCES | yields.SOURCES | nitrogen.SOURCES | SOURCES,
    )
    return export, response


def _write(path: Path, model) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    weights = json.loads(UI_INPUT_FILE.read_text())["weights"]  # MOCK of the UI input (scorer)
    export, response = build_explorer(weights)
    _write(EXAMPLES / "explorer.json", export)
    _write(EXAMPLES / "scorer" / "response.json", response)
    for r in export.rotations:
        for v, label in ((r, "current" if r.is_current else f"pick {r.rank}"), (r.cover_variant, "  toggle")):
            if v is not None:
                print(f"{label:8} {v.id:40} seasons {len(v.sequence)}  months {len(v.monthly)}  bare {v.summary.bare_months}")


if __name__ == "__main__":
    main()
