"""Lookups for the farmer advisor: field, rotations, comparison, monthly table.

Every function returns plain dicts / lists (JSON-serializable), no pandas or pydantic objects.

Two detail levels, stated in the result as ``detail_level``:

* ``"full"``: the rotation is in ``explorer.json`` (current rotation + top picks). Seasons, yield and
  irrigation spreads, nitrogen, summary and months are available.
* ``"scores_only"``: the rotation is only in ``rotation_scores.csv``. Scores and KPIs only.

Scores, ranks and KPIs always come from the CSV, ranked with ``DEFAULT_WEIGHTS`` (equal weights). Flags that
tell how far to trust a value (``placeholder``, null nitrogen) are always part of the result, never dropped.
"""

from __future__ import annotations

from typing import Any

from advisor.data import (
    DEFAULT_WEIGHTS,
    DetailNotAvailableError,
    check_id,
    load_export,
    load_scores,
)
from explorer.build import KPI_COLUMNS, KPI_MM_COLUMNS, LABELS
from explorer.field_calendar import parse_key
from explorer.schema import Rotation
from explorer.water import MM_PER_IN

SCORES_ONLY_NOTE = (
    "Scores only: this rotation is not in explorer.json, so there are no seasons, yields, "
    "nitrogen amounts or monthly values for it."
)


def _full(rotation_id: str) -> Rotation | None:
    """The explorer.json rotation, or None if only the scores table knows it."""
    return next((r for r in load_export().rotations if r.id == rotation_id), None)


def _name(rotation_id: str) -> str:
    crops, cover = parse_key(rotation_id)
    return " · ".join(LABELS[c] for c in crops) + (f" + {cover} cover" if cover else "")


def _scores(rotation_id: str) -> dict[str, Any]:
    """Rank, total score, the four normalised scores (0 = best) and the KPIs of one rotation, from the CSV."""
    scores = load_scores()
    row = scores.loc[rotation_id]
    kpi = ({c: float(row[c]) for c in KPI_COLUMNS}
           | {ours: float(row[mm]) / MM_PER_IN for mm, ours in KPI_MM_COLUMNS.items()})
    return {
        "rank_all": int(row["rank"]),
        "n_rotations": len(scores),
        "weights": dict(DEFAULT_WEIGHTS),
        "total_score": round(float(row["total_score"]), 4),
        "score_parts": {
            name: round(float(row[f"{name}_score"]), 4) for name in DEFAULT_WEIGHTS
        },
        "kpi": kpi,
    }


def _flags(rotation: Rotation | None) -> dict[str, bool | None]:
    """Caveat flags. ``placeholder`` is None when unknown (scores-only rotations)."""
    if rotation is None:
        return {"placeholder": None, "nitrogen_null": True}  # the CSV has the nitrogen score, no amounts
    nitrogen_null = rotation.summary.n_loss_lb is None or any(
        s.n_lb is None or s.n_adj_lb is None for s in rotation.sequence
    ) or any(m.nitrogen is None for m in rotation.monthly)
    return {"placeholder": rotation.placeholder, "nitrogen_null": nitrogen_null}


def _brief(rotation_id: str) -> dict[str, Any]:
    """The short form used in lists: identity, score, detail level, flags."""
    rotation = _full(rotation_id)
    crops, cover = parse_key(rotation_id)
    s = _scores(rotation_id)
    return {
        "id": rotation_id,
        "name": rotation.name if rotation else _name(rotation_id),
        "crops": crops,
        "cover_crop": cover,
        "is_current": bool(rotation and rotation.is_current),
        "pick": rotation.rank if rotation else None,  # 1-3 in explorer.json, else None
        "rank_all": s["rank_all"],
        "total_score": s["total_score"],
        "score_parts": s["score_parts"],
        "detail_level": "full" if rotation else "scores_only",
        "flags": _flags(rotation),
    }


def field_overview() -> dict[str, Any]:
    """The field, its climate in short, the current rotation and the picks."""
    export = load_export()
    climate = export.climate

    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 2)

    rotations = [_brief(r.id) for r in export.rotations]
    return {
        "contract_version": export.contract_version,
        "generated_at": export.generated_at,
        "field": export.field.model_dump(mode="json"),
        "climate": {
            "weather_years": [climate.weather_years[0], climate.weather_years[-1]],
            "rain_in_mean": mean(climate.rain_in),
            "et0_apr_sep_in_mean": mean(climate.et0_apr_sep_in),
            "deficit_apr_sep_in_mean": mean(climate.deficit_apr_sep_in),
            "heat_days_ge_35_mean": mean(climate.heat_days_ge_35),
        },
        "n_rotations": len(load_scores()),
        "current_rotation": next(r for r in rotations if r["is_current"]),
        "picks": sorted((r for r in rotations if r["pick"] is not None), key=lambda r: r["pick"]),
        "placeholder": any(r.placeholder for r in export.rotations),
    }


def list_top_rotations(n: int = 10, cover_crop: bool | None = None) -> list[dict[str, Any]]:
    """The ``n`` best rotations of all candidates (equal weights), best first.

    ``cover_crop=True`` keeps only rotations with a cover crop, ``False`` only those without, None all.
    """
    if n < 1:
        raise ValueError(f"n must be at least 1, got {n}")
    ids = list(load_scores().index)
    if cover_crop is not None:
        ids = [i for i in ids if (parse_key(i)[1] is not None) == cover_crop]
    return [_brief(i) for i in ids[:n]]


def get_rotation(rotation_id: str) -> dict[str, Any]:
    """One rotation. ``detail_level`` says whether seasons and summary are filled (``"full"``) or None."""
    check_id(rotation_id)
    rotation = _full(rotation_id)
    result = _brief(rotation_id) | {"short": rotation.short if rotation else None}
    result["kpi"] = _scores(rotation_id)["kpi"]
    result["n_rotations"] = len(load_scores())
    result["weights"] = dict(DEFAULT_WEIGHTS)
    if rotation is None:
        return result | {"seasons": None, "summary": None, "note": SCORES_ONLY_NOTE}
    # SeasonDetail serializes "yield_" as "yield"; effects keep their provenance label.
    return result | {
        "seasons": [s.model_dump(mode="json") for s in rotation.sequence],
        "summary": rotation.summary.model_dump(mode="json"),
        "note": None,
    }


def compare_rotations(a: str, b: str) -> dict[str, Any]:
    """Two rotations side by side. ``diff`` values are ``b - a`` (negative = b is better for scores).

    ``trade_offs`` names in plain words where the two differ clearly (see ``advisor.explain.trade_offs``).
    """
    from advisor.explain import trade_offs  # here, not at the top: explain imports this module

    ra, rb = get_rotation(a), get_rotation(b)
    result: dict[str, Any] = {
        "a": ra,
        "b": rb,
        "diff": {
            "total_score": round(rb["total_score"] - ra["total_score"], 4),
            "score_parts": {k: round(rb["score_parts"][k] - ra["score_parts"][k], 4) for k in ra["score_parts"]},
            "kpi": {k: round(rb["kpi"][k] - ra["kpi"][k], 6) for k in ra["kpi"]},
            "summary": None,
        },
        "detail_level": "full" if ra["detail_level"] == rb["detail_level"] == "full" else "scores_only",
        "trade_offs": trade_offs(a, b),
    }
    if ra["summary"] is not None and rb["summary"] is not None:
        result["diff"]["summary"] = {
            k: _minus(rb["summary"][k], ra["summary"][k]) for k in ("bare_months", "same_crop_repeats", "n_loss_lb")
        }
    return result


def _minus(x: float | None, y: float | None) -> float | None:
    """``x - y``, None if a value is missing (e.g. nitrogen pending), never 0 instead of None."""
    return None if x is None or y is None else round(x - y, 4)


def monthly_table(rotation_id: str) -> dict[str, Any]:
    """Water and risk per calendar month of the rotation's window (mean over all weather years).

    Only rotations with ``detail_level == "full"`` have months; others raise ``DetailNotAvailableError``.
    """
    check_id(rotation_id)
    rotation = _full(rotation_id)
    if rotation is None:
        full_ids = [r.id for r in load_export().rotations]
        raise DetailNotAvailableError(
            f"No monthly table for '{rotation_id}': it is only in the scores table. "
            f"Rotations with months: {', '.join(full_ids)}."
        )
    return {
        "id": rotation.id,
        "name": rotation.name,
        "detail_level": "full",
        "flags": _flags(rotation),
        "months": [m.model_dump(mode="json") for m in rotation.monthly],
    }
