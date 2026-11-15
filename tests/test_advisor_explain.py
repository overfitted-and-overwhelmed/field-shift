"""Tests for the advisor glossary, explanations, re-ranking and export (sub-tasks 2-5)."""

import json
from typing import get_args

import pytest

from advisor import (
    UnknownRotationError,
    UnknownTermError,
    compare_rotations,
    explain_score,
    explain_term,
    get_data_caveats,
    list_terms,
    list_top_rotations,
    rerank,
    trade_offs,
)
from advisor import export as advisor_export
from advisor.data import DEFAULT_WEIGHTS, load_export, load_scores
from advisor.glossary import normalize, templates, terms
from advisor.rerank import validate_weights
from crop_scorer.scoring.score_rotations import CRITERIA
from explorer.schema import MonthDetail, MonthNitrogen, ProvenanceLabel, SeasonDetail, Spread, Summary

CURRENT = "corn-corn-corn"
PICK_1 = "sunflower-soybean-sunflower+triticale"
CSV_ONLY = "corn-corn-sorghum"  # a candidate that is not in explorer.json


# ---------------------------------------------------------------- glossary (sub-task 2)


def test_glossary_covers_criteria_labels_and_schema_fields():
    keys = set(terms())
    assert set(CRITERIA) <= keys
    assert set(get_args(ProvenanceLabel)) <= keys
    for model in (MonthDetail, MonthNitrogen, Summary, SeasonDetail):
        for name, field in model.model_fields.items():
            # explain_term also finds the alias, so the data field names of the contract all resolve
            assert explain_term(field.alias or name)["key"] in keys, f"{model.__name__}.{name} has no glossary entry"
    # the p10 / p90 of a Spread and the climate fields
    assert explain_term("p10")["key"] == "spread"
    assert explain_term("et0_apr_sep_in")["key"] == "et0"


def test_every_provenance_key_field_is_explainable():
    # the last part of 'monthly.heat_years_pct' etc. is a field name the frontend may look up
    for key in load_export().provenance:
        field = key.split(".")[-1]
        if field != "*":
            try:
                explain_term(field)
            except UnknownTermError:
                pytest.fail(f"provenance field '{field}' has no glossary entry")


def test_entries_are_complete_and_marked_unreviewed():
    for key, entry in terms().items():
        assert {"term", "short", "long", "unit", "why_it_matters", "source", "aliases", "reviewed"} <= set(entry), key
        assert entry["short"].strip() and entry["long"].strip(), key
        assert entry["reviewed"] is False, f"{key}: set reviewed only after the agronomic review"


def test_explain_term_accepts_key_alias_title_and_any_case():
    expected = explain_term("cold_stress_years_pct")["key"]
    for name in ("Cold stress", "cold-stress", "COLD_STRESS_YEARS_PCT", "Cold-stress years"):
        assert explain_term(name)["key"] == expected


def test_unknown_term_lists_close_matches():
    with pytest.raises(UnknownTermError) as error:
        explain_term("nitrogn")
    assert "nitrogen" in error.value.close_matches


def test_list_terms_is_json_serializable_and_complete():
    listed = list_terms()
    assert [t["key"] for t in listed] == list(terms())
    json.dumps(listed)


def test_glossary_names_are_unique():
    seen: dict[str, str] = {}
    for key, entry in terms().items():
        for name in [key, entry["term"], *entry["aliases"]]:
            assert seen.setdefault(normalize(name), key) == key, f"'{name}' is used twice"


# ---------------------------------------------------------------- explain_score and trade-offs (sub-task 3)


def test_explain_score_breakdown_adds_up_to_the_total():
    result = explain_score(PICK_1)
    assert [b["criterion"] for b in result["breakdown"]] == list(CRITERIA)
    assert sum(b["contribution"] for b in result["breakdown"]) == pytest.approx(result["total_score"], abs=2e-4)
    assert result["rank"] == int(load_scores().loc[PICK_1, "rank"])
    assert result["summary"].startswith(result["name"])
    assert "relative" not in result["note"] or "Scores compare" in result["note"]
    json.dumps(result)


def test_explain_score_names_the_strongest_and_weakest_counted_criterion():
    result = explain_score(CURRENT)
    scores = {b["criterion"]: b["score"] for b in result["breakdown"]}
    assert result["strongest"] == min(scores, key=scores.get)
    assert result["weakest"] == max(scores, key=scores.get)


def test_explain_score_ignores_criteria_with_weight_zero():
    # corn-corn-corn is best at risk (0.0) and bad at soil_health / nitrogen; with only water and risk
    # counting, soil_health and nitrogen must not become the weakest point
    result = explain_score(CURRENT, {"water": 1, "risk": 1})
    assert result["weakest"] == "water"
    by_name = {b["criterion"]: b for b in result["breakdown"]}
    assert by_name["soil_health"]["weight"] == 0 and by_name["soil_health"]["contribution"] == 0
    assert by_name["soil_health"]["score"] > 0  # still shown


def test_explain_score_with_a_single_criterion_uses_the_single_template():
    result = explain_score(PICK_1, {"water": 1})
    assert "Only one criterion counts" in result["summary"]
    assert result["strongest"] == result["weakest"] == "water"


def test_explain_score_works_for_a_scores_only_rotation_and_a_cover_crop():
    result = explain_score(CSV_ONLY)
    assert result["detail_level"] == "scores_only"
    cover = explain_score(PICK_1)
    assert cover["detail_level"] == "full" and "cover" in cover["name"]


def test_explain_score_unknown_id_and_bad_weights():
    with pytest.raises(UnknownRotationError):
        explain_score("corn-corn-corm")
    with pytest.raises(ValueError):
        explain_score(CURRENT, {"water": 0})


def test_trade_offs_name_the_better_rotation_per_criterion():
    result = trade_offs(CURRENT, PICK_1)
    assert result["items"], "the pick differs clearly from corn-corn-corn"
    scores = load_scores()
    for item in result["items"]:
        name = item["criterion"]
        better = item["better"]
        other = PICK_1 if better == CURRENT else CURRENT
        assert scores.loc[better, f"{name}_score"] < scores.loc[other, f"{name}_score"]
        assert abs(item["diff"]) >= result["threshold"]
        assert item["sentence"] in result["summary"]


def test_trade_offs_of_a_rotation_with_itself_is_empty():
    result = trade_offs(CURRENT, CURRENT)
    assert result["items"] == []
    assert result["summary"] == templates()["trade_off_none"]


def test_compare_rotations_includes_trade_offs():
    result = compare_rotations(CURRENT, PICK_1)
    assert result["trade_offs"] == trade_offs(CURRENT, PICK_1)


def test_caveats_of_a_full_rotation():
    result = get_data_caveats(CURRENT)
    codes = {c["code"] for c in result["caveats"]}
    assert {"relative_scores", "nitrogen_pending", "modeled", "grid_weather"} <= codes
    assert "scores_only" not in codes
    assert {a["field"] for a in result["assumptions"]} >= {"sequence.irrigation", "monthly.cold_stress_years_pct"}
    assert "scorer" in result["sources"]
    # every cited source exists in explorer.json
    assert set(result["sources"]) <= set(load_export().sources)
    json.dumps(result)


def test_caveats_flag_placeholder_values(monkeypatch):
    export = load_export()
    rotation = next(r for r in export.rotations if r.id == CURRENT)
    monkeypatch.setattr(rotation, "placeholder", True)
    codes = {c["code"] for c in get_data_caveats(CURRENT)["caveats"]}
    assert "placeholder" in codes


def test_caveats_of_a_scores_only_rotation_do_not_claim_season_assumptions():
    result = get_data_caveats(CSV_ONLY)
    codes = {c["code"] for c in result["caveats"]}
    assert {"scores_only", "placeholder_unknown", "nitrogen_pending"} <= codes
    assert all(a["field"].startswith("field.") for a in result["assumptions"])
    assert "literature_effect" not in codes


def test_caveats_name_the_literature_source_of_rotation_effects():
    result = get_data_caveats(CURRENT)  # corn after corn has a literature effect
    effects = [c for c in result["caveats"] if c["code"] == "literature_effect"]
    assert effects and all(c["source"] in result["sources"] for c in effects)


# ---------------------------------------------------------------- rerank (sub-task 4)


def test_rerank_with_default_weights_reproduces_the_picks_of_explorer_json():
    export = load_export()
    picks = [r.id for r in sorted((r for r in export.rotations if r.rank), key=lambda r: r.rank)]
    ranked = [r["id"] for r in rerank(None, top_n=len(load_scores()))["rotations"] if r["id"] != CURRENT]
    assert ranked[: len(picks)] == picks


def test_rerank_default_weights_equal_the_scorer_ranking():
    assert [r["id"] for r in rerank(DEFAULT_WEIGHTS, 10)["rotations"]] == list(load_scores().index[:10])


def test_rerank_depends_on_the_weights_and_not_on_their_scale():
    water_first = rerank({"water": 10, "risk": 1, "soil_health": 1, "nitrogen": 1}, 5)
    scaled = rerank({"water": 20, "risk": 2, "soil_health": 2, "nitrogen": 2}, 5)
    balanced = rerank(None, 5)
    assert [r["id"] for r in water_first["rotations"]] == [r["id"] for r in scaled["rotations"]]
    assert [r["id"] for r in water_first["rotations"]] != [r["id"] for r in balanced["rotations"]]
    ranks = [r["rank_all"] for r in water_first["rotations"]]
    assert ranks == [1, 2, 3, 4, 5]
    totals = [r["total_score"] for r in water_first["rotations"]]
    assert totals == sorted(totals)


def test_rerank_single_criterion_puts_the_lowest_score_first():
    top = rerank({"soil_health": 1}, 1)["rotations"][0]["id"]
    scores = load_scores()
    assert scores.loc[top, "soil_health_score"] == scores["soil_health_score"].min()


def test_rerank_result_shape():
    result = rerank({"water": 3, "risk": 1}, 3)
    assert result["weights"] == {"water": 3.0, "risk": 1.0, "soil_health": 0.0, "nitrogen": 0.0}
    assert result["weight_shares"]["water"] == 0.75
    assert result["n_rotations"] == len(load_scores())
    assert len(result["rotations"]) == 3
    assert {"id", "name", "rank_all", "total_score", "score_parts", "detail_level", "flags"} <= set(result["rotations"][0])
    json.dumps(result)


@pytest.mark.parametrize(
    "weights",
    [{"water": -1}, {"water": 0}, {}, {"wter": 1}, {"water": float("nan")}, {"water": float("inf")}, {"water": "1"},
     {"water": True}],
)
def test_rerank_rejects_bad_weights(weights):
    with pytest.raises(ValueError):
        rerank(weights)


def test_rerank_rejects_bad_top_n_and_validate_weights_defaults():
    with pytest.raises(ValueError):
        rerank(None, 0)
    assert validate_weights(None) == {name: 1.0 for name in CRITERIA}
    assert validate_weights({"water": 2}) == {"water": 2.0, "risk": 0.0, "soil_health": 0.0, "nitrogen": 0.0}


def test_rerank_does_not_change_the_default_ranking_cache():
    before = list(load_scores().index[:5])
    rerank({"water": 9}, 5)
    assert list(load_scores().index[:5]) == before
    assert [r["id"] for r in list_top_rotations(5)] == before


# ---------------------------------------------------------------- export (sub-task 5)


def test_export_writes_valid_files(tmp_path):
    advisor_export.main(tmp_path)
    assert {p.name for p in tmp_path.iterdir()} == {"glossary.json", "explanations.json", "presets.json"}

    glossary = advisor_export.GlossaryFile.model_validate_json((tmp_path / "glossary.json").read_text())
    assert set(glossary.terms) == set(terms())

    explanations = advisor_export.ExplanationsFile.model_validate_json((tmp_path / "explanations.json").read_text())
    export = load_export()
    assert set(explanations.rotations) == {r.id for r in export.rotations}
    assert explanations.explorer_generated_at == export.generated_at
    current = explanations.rotations[explanations.current_rotation]
    assert current.trade_offs_vs_current is None
    assert all(a.trade_offs_vs_current is not None for k, a in explanations.rotations.items() if k != explanations.current_rotation)

    presets = advisor_export.PresetsFile.model_validate_json((tmp_path / "presets.json").read_text())
    assert set(presets.presets) == set(advisor_export.PRESETS)
    assert presets.presets["balanced"].rotations[0]["id"] == load_scores().index[0]
    assert presets.presets["water"].rotations[0]["id"] != presets.presets["soil"].rotations[0]["id"]


def test_committed_example_files_are_up_to_date(tmp_path):
    """The files in explorer/examples/advisor/ must equal a fresh export (run `uv run python -m advisor.export`)."""
    advisor_export.main(tmp_path)
    for name in ("glossary.json", "explanations.json", "presets.json"):
        fresh = json.loads((tmp_path / name).read_text())
        committed = json.loads((advisor_export.OUT_DIR / name).read_text())
        assert committed == fresh, f"{name} is stale, run: uv run python -m advisor.export"


def test_export_models_reject_unknown_keys():
    with pytest.raises(Exception):
        advisor_export.PresetsFile.model_validate({"contract_version": "x", "explorer_generated_at": "x",
                                                   "n_rotations": 1, "presets": {}, "extra": 1})


def test_spread_is_imported_for_the_glossary_check():
    assert set(Spread.model_fields) == {"v", "p10", "p90"}
