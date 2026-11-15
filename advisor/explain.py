"""Plain-language explanations: why a rotation ranks where it does, trade-offs between two, and data caveats.

Everything is deterministic: numbers come from the scorer's files, sentences from the templates in
glossary.json. No LLM, nothing is invented. Scores are relative (0 = best, 1 = worst of all tested rotations).
"""

from __future__ import annotations

from typing import Any, Mapping

from advisor.data import check_id, load_export
from advisor.glossary import templates
from advisor.lookup import _brief, _full
from advisor.rerank import ranked_scores, validate_weights
from crop_scorer.scoring.score_rotations import CRITERIA

GOOD_MAX = 1 / 3  # score <= 1/3 counts as good, <= 2/3 as middle, above as weak


def _level(score: float) -> str:
    return "good" if score <= GOOD_MAX else "mid" if score <= 2 * GOOD_MAX else "bad"


def explain_score(rotation_id: str, weights: Mapping[str, float] | None = None) -> dict[str, Any]:
    """Why this rotation has its rank for these weights (None = equal weights).

    ``breakdown`` has per criterion the score (0 = best), the weight and its share, the contribution to the
    total score and a plain phrase. ``summary`` is a ready sentence. Criteria with weight 0 are shown but do
    not count for the strongest and weakest point.
    """
    check_id(rotation_id)
    w = validate_weights(weights)
    ranked = ranked_scores(w)
    row = ranked.loc[rotation_id]
    t = templates()
    brief = _brief(rotation_id)
    total_w = sum(w.values())

    breakdown = []
    for name in CRITERIA:
        score = round(float(row[f"{name}_score"]), 4)
        level = _level(score)
        breakdown.append({
            "criterion": name,
            "score": score,
            "weight": w[name],
            "weight_share": round(w[name] / total_w, 4),
            "contribution": round(w[name] / total_w * score, 4),
            "level": level,
            "phrase": t["criteria_phrases"][name][level],
        })

    counted = [b for b in breakdown if b["weight"] > 0]
    best = min(counted, key=lambda b: b["score"])
    worst = max(counted, key=lambda b: b["score"])
    n = len(ranked)
    fields = {"name": brief["name"], "rank": int(row["rank"]), "n": n, "best": best["phrase"], "worst": worst["phrase"]}
    summary = t["explain_summary_single" if len(counted) == 1 else "explain_summary"].format(**fields)
    return {
        "id": rotation_id,
        "name": brief["name"],
        "rank": int(row["rank"]),
        "n_rotations": n,
        "total_score": round(float(row["total_score"]), 4),
        "weights": w,
        "breakdown": breakdown,
        "strongest": best["criterion"],
        "weakest": worst["criterion"],
        "summary": summary,
        "note": t["explain_relative"].format(n=n),
        "detail_level": brief["detail_level"],
        "flags": brief["flags"],
    }


def trade_offs(a: str, b: str) -> dict[str, Any]:
    """Where two rotations differ clearly (score difference of at least ``trade_off_threshold``).

    The better one (lower score) of each criterion is named in a sentence. Differences below the threshold
    are not reported, so two similar rotations give an empty list.
    """
    check_id(a)
    check_id(b)
    t = templates()
    brief_a, brief_b = _brief(a), _brief(b)
    threshold = t["trade_off_threshold"]
    items = []
    for name in CRITERIA:
        sa, sb = brief_a["score_parts"][name], brief_b["score_parts"][name]
        diff = round(sb - sa, 4)
        if abs(diff) < threshold:
            continue
        better, worse = (brief_a, brief_b) if diff > 0 else (brief_b, brief_a)
        items.append({
            "criterion": name,
            "better": better["id"],
            "diff": diff,  # b - a, like compare_rotations
            "sentence": t["trade_off_sentence"].format(
                name=better["name"], phrase=t["trade_off_phrases"][name], other=worse["name"]
            ),
        })
    return {
        "threshold": threshold,
        "items": items,
        "summary": " ".join(i["sentence"] for i in items) if items else t["trade_off_none"],
    }


def get_data_caveats(rotation_id: str) -> dict[str, Any]:
    """How far to trust the numbers of a rotation: caveats, assumptions and the sources behind them.

    Covers: relative scores, scores-only detail, placeholder values, missing nitrogen amounts, model and grid
    weather limits, literature effects and every value marked as assumption in explorer.json.
    """
    check_id(rotation_id)
    export = load_export()
    t = templates()
    c = t["caveats"]
    rotation = _full(rotation_id)
    brief = _brief(rotation_id)
    flags = brief["flags"]
    years = export.climate.weather_years

    caveats = [{"code": "relative_scores", "text": c["relative_scores"].format(n=len(ranked_scores()))}]
    if rotation is None:
        caveats.append({"code": "scores_only", "text": c["scores_only"]})
        caveats.append({"code": "placeholder_unknown", "text": c["placeholder_unknown"]})
    elif flags["placeholder"]:
        caveats.append({"code": "placeholder", "text": c["placeholder"]})
    if flags["nitrogen_null"]:
        caveats.append({"code": "nitrogen_pending", "text": c["nitrogen_pending"]})
    caveats.append({"code": "modeled", "text": c["modeled"].format(first_year=years[0], last_year=years[-1])})
    caveats.append({"code": "grid_weather", "text": c["grid_weather"]})

    # sources behind the rotation's numbers: the scorer, plus everything its fields cite (field-level only when
    # there is no detailed view, because seasons and months do not exist then)
    used_sources: set[str] = {"scorer"}
    detail = rotation is not None
    for key, entry in export.provenance.items():
        if entry.source and (detail or key.startswith("field.")):
            used_sources.add(entry.source)

    if rotation is not None:
        seen: set[str] = set()
        for season in rotation.sequence:
            for effect in season.effects:
                # only effects from studies ("rule"); model notes and assumptions also cite a source
                if effect.provenance != "rule" or effect.source is None or effect.source in seen:
                    continue
                seen.add(effect.source)
                used_sources.add(effect.source)
                caveats.append({
                    "code": "literature_effect",
                    "text": c["literature_effect"].format(title=export.sources[effect.source].title),
                    "source": effect.source,
                })

    levels = ", ".join(sorted({s.irrigation for s in rotation.sequence})) if rotation else ""
    assumptions = []
    for key, entry in export.provenance.items():
        if entry.label != "assumption" or (not detail and not key.startswith("field.")):
            continue
        text = t["assumptions"].get(key, f"'{key}' is an assumption, not a measurement.").format(levels=levels)
        assumptions.append({"field": key, "text": text, "source": entry.source})

    return {
        "id": rotation_id,
        "name": brief["name"],
        "detail_level": brief["detail_level"],
        "flags": flags,
        "caveats": caveats,
        "assumptions": assumptions,
        "sources": {k: export.sources[k].model_dump(mode="json") for k in sorted(used_sources) if k in export.sources},
    }
