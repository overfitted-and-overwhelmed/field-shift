"""File-based hand-off of the advisor to the web app (no API): writes JSON files next to explorer.json.

    uv run python -m advisor.export

Files in explorer/examples/advisor/:

* ``glossary.json``     plain-language terms for tooltips (key, aliases, short / long text, unit, reviewed flag)
* ``explanations.json`` per rotation of explorer.json: ``explain`` (rank and criteria in words, equal weights),
                        ``caveats`` (how far to trust it) and ``trade_offs`` against the current rotation
* ``presets.json``      re-ranked top rotations for fixed weight presets (buttons or slider steps without a backend)

The content is derived from explorer.json and the scorer's CSV, so run it again after ``explorer.build``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from advisor.data import DEFAULT_WEIGHTS, load_export
from advisor.explain import explain_score, get_data_caveats, trade_offs
from advisor.glossary import terms
from advisor.rerank import rerank
from explorer.paths import REPO_ROOT

OUT_DIR = REPO_ROOT / "explorer" / "examples" / "advisor"
CONTRACT_VERSION = "1.0.0-draft"
PRESET_TOP_N = 5

# label shown on the button -> weights (only the ratio matters)
PRESETS: dict[str, dict[str, Any]] = {
    "balanced": {"label": "Balanced", "weights": dict(DEFAULT_WEIGHTS)},
    "water": {"label": "Save water", "weights": {"water": 4, "risk": 1, "soil_health": 1, "nitrogen": 1}},
    "risk": {"label": "Low weather risk", "weights": {"water": 1, "risk": 4, "soil_health": 1, "nitrogen": 1}},
    "soil": {"label": "Protect the soil", "weights": {"water": 1, "risk": 1, "soil_health": 4, "nitrogen": 1}},
    "fertilizer": {"label": "Save fertilizer", "weights": {"water": 1, "risk": 1, "soil_health": 1, "nitrogen": 4}},
}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GlossaryTerm(_Strict):
    term: str
    short: str
    long: str
    unit: str
    why_it_matters: str
    source: str
    aliases: list[str]
    reviewed: bool


class GlossaryFile(_Strict):
    contract_version: str
    terms: dict[str, GlossaryTerm]


class RotationAdvice(_Strict):
    explain: dict[str, Any]
    caveats: dict[str, Any]
    trade_offs_vs_current: dict[str, Any] | None  # None for the current rotation itself


class ExplanationsFile(_Strict):
    contract_version: str
    explorer_generated_at: str  # of the explorer.json it was derived from, so the files can be matched
    current_rotation: str
    rotations: dict[str, RotationAdvice]


class Preset(_Strict):
    label: str
    weights: dict[str, float]
    weight_shares: dict[str, float]
    rotations: list[dict[str, Any]] = Field(min_length=1)


class PresetsFile(_Strict):
    contract_version: str
    explorer_generated_at: str
    n_rotations: int
    presets: dict[str, Preset]


def build_glossary() -> GlossaryFile:
    return GlossaryFile(
        contract_version=CONTRACT_VERSION,
        terms={key: GlossaryTerm(**{f: e[f] for f in GlossaryTerm.model_fields}) for key, e in terms().items()},
    )


def build_explanations() -> ExplanationsFile:
    export = load_export()
    current = next(r.id for r in export.rotations if r.is_current)
    advice = {
        r.id: RotationAdvice(
            explain=explain_score(r.id),
            caveats=get_data_caveats(r.id),
            trade_offs_vs_current=None if r.is_current else trade_offs(current, r.id),
        )
        for r in export.rotations
    }
    return ExplanationsFile(
        contract_version=CONTRACT_VERSION,
        explorer_generated_at=export.generated_at,
        current_rotation=current,
        rotations=advice,
    )


def build_presets() -> PresetsFile:
    export = load_export()
    presets = {}
    n = 0
    for key, p in PRESETS.items():
        result = rerank(p["weights"], PRESET_TOP_N)
        n = result["n_rotations"]
        presets[key] = Preset(
            label=p["label"], weights=result["weights"], weight_shares=result["weight_shares"],
            rotations=result["rotations"],
        )
    return PresetsFile(
        contract_version=CONTRACT_VERSION, explorer_generated_at=export.generated_at, n_rotations=n, presets=presets
    )


def _write(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(model.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main(out_dir: Path = OUT_DIR) -> None:
    files = {
        "glossary.json": build_glossary(),
        "explanations.json": build_explanations(),
        "presets.json": build_presets(),
    }
    for name, model in files.items():
        _write(out_dir / name, model)
        print(f"[advisor] wrote {out_dir / name}")


if __name__ == "__main__":
    main()
