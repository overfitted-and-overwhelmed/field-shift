# Farmer Advisor Plan (core functions, glossary, explain/rerank, file-based, no API)

## Top-Level Overview

**Goal:** Let a farmer explore the crop scorer / explorer results in plain language inside the web app, without needing an AI agent.

**Approach:** Build the logic once as a plain Python module (`advisor/`) that reads the existing files (`explorer.json`, scorer CSVs). No API, no server, no LLM for now. Plain-language content lives in a data file (glossary + sentence templates). The web app consumes either the glossary file directly (tooltips) or pre-generated JSON written by the module (explanations, re-ranked lists).

**Non-goals (for now):** HTTP API, LLM calls, re-running the simulation (`score_all`, `explorer.build` pipelines), changing the scoring model, building the web frontend, MCP server (see Future Outlook).

**Key findings from research**
- `explorer/examples/explorer.json` (contract `explorer/schema.py`, v6.1.0-draft) holds only the current rotation + top 3 picks. The full candidate set (225 rotations, with and without cover crop) is in `data/processed/rotation_scores/rotation_scores.csv` with normalized `water_score`, `risk_score`, `soil_health_score`, `nitrogen_score` (0-1, smaller is better).
- Re-ranking already exists: `rank(scores, weights)` in `crop_scorer/scoring/score_rotations.py` and `scorer_response(...)` in `explorer/build.py`. Weights only need the stored `*_score` columns, so no simulation re-run is required.
- `explorer.json` carries `provenance` (measured / modeled / rule / assumption), `sources`, `placeholder` flags and null nitrogen fields (pending WP4). Explanations must surface these caveats and never invent numbers.
- There is no REST API, frontend or MCP code in the repo. Conventions: Python 3.14, `uv`, pydantic v2 with `extra="forbid"`, pytest with doctests, unit suffixes in field names (`_in`, `_lb`, `_pct`).
- Hard-to-read terms for a farmer: ET0/ETc, Ks, p10/p90 spreads, bare months, kill/cold-stress/heat years %, normalized score, provenance labels, irrigation level (full / reduced / none), cover crop.

## Sub-Tasks

### 1. Core read layer (load files, look up rotations)
**Intent:** One place that loads `explorer.json` and `rotation_scores.csv` and answers basic lookups, so everything else shares the same data access.

**Expected Outcomes**
- `advisor` package importable; functions return plain dicts/lists (JSON-serializable).
- Functions: field overview, list top rotations, get one rotation (seasons, yield/irrigation spreads, N, summary), compare two rotations, monthly water/risk table for a rotation.
- Rotations not in `explorer.json` (rank beyond top 3) can still be looked up from the CSV with scores only; the response says which detail level it has.
- Unknown rotation ids give a clear error listing close matches.

**Todo List**
1. Create `advisor/` package with a data-loading module reusing `explorer/paths.py` and the `ExplorerExport` model for validation.
2. Implement the lookup functions listed above.
3. Always include `placeholder` / null-nitrogen flags in results instead of dropping them.
4. Tests with the example `explorer.json` and the real CSV.

**Relevant Context:** `explorer/schema.py` (`ExplorerExport`, `Rotation`, `SeasonDetail`, `MonthDetail`), `explorer/paths.py`, `explorer/build.py` (`load_scorer_scores`), `tests/test_build.py` for test style.

**Status:** [ ] pending

### 2. Glossary and plain-language content
**Intent:** Most of the farmer value: short, accurate, non-technical explanations, kept as data so the web app (and later an MCP wrapper) can use them.

**Expected Outcomes**
- A data file (JSON or YAML) with entries per term: short farmer wording, longer wording, unit, "why it matters", and a `source` reference.
- Covers at least: the four score criteria, ET0/ETc, Ks, p10/v/p90 spread, bare months / erosion, heat / cold-stress / kill years %, irrigation levels, cover crop, N fertilizer and previous-crop credit, provenance labels, placeholder.
- Provenance and source caveats are phrased once, in plain words.
- A test checks that every provenance label, criterion and `MonthDetail` field has a glossary entry, so the glossary can't drift from the schema.
- Entries are marked `reviewed: false` until the review TODO below is done.

**Todo List**
1. Draft glossary entries from the definitions in `crop_scorer/` docstrings and `explorer/schema.py` descriptions (do not invent new domain facts).
2. Implement `explain_term(term)` and `list_terms()` in `advisor`.
3. Add the coverage test.
4. **TODO (open, owner not yet assigned): agronomic review of the wording** for water, nitrogen and risk (see "Review TODO" below).

**Relevant Context:** `crop_scorer/scoring/score_rotations.py` (CRITERIA, docstrings), `crop_scorer/risk_score/severity.py`, `explorer/yields.py` (model description), `explorer/frost_heat.py`, `explorer/build.py` (PROVENANCE, SOURCES).

**Status:** [ ] pending

### 3. Explain-score and caveats
**Intent:** Answer "why is this rotation ranked here?" and "how much can I trust this?" with templated, deterministic sentences.

**Expected Outcomes**
- `explain_score(rotation, weights)` returns a per-criterion breakdown (score, weight, contribution to total), the strongest and weakest criterion, and a templated plain-language summary.
- `compare_rotations` includes the main trade-offs (for example "needs less water but leaves more bare months").
- `get_data_caveats(rotation)` lists placeholders, null nitrogen, `assumption` provenance and sources relevant to that rotation.
- Wording makes clear that scores are relative among the evaluated rotations (min-max normalized), not absolute quality.

**Todo List**
1. Define the breakdown structure and the sentence templates (stored with the glossary content).
2. Implement `explain_score`, trade-off detection and `get_data_caveats`.
3. Tests, including edge cases: a criterion with weight 0, nitrogen null, a rotation with a cover crop.

**Relevant Context:** `rank` and `normalize` in `score_rotations.py`, `ScoreParts` and `Rotation.kpi` in `explorer/schema.py`.

**Status:** [ ] pending

### 4. Re-rank with custom weights (slider backend)
**Intent:** Let the farmer say "water matters more to me" and get a new top list, using the existing ranking logic.

**Expected Outcomes**
- `rerank(weights, top_n)` returns ranked rotations from the full CSV, using the existing `rank` function (no duplicated formula).
- Weights are validated (non-negative, at least one > 0, only known criteria) with a clear message.
- The result includes, per rotation, enough data for the web app to render it and for `explain_score` to be called next.
- Test: default weights reproduce the current top 3 in `explorer.json`.

**Todo List**
1. Implement `rerank` as a thin wrapper over `rank` and the CSV loader.
2. Add weight validation.
3. Add the regression test against the example export.

**Relevant Context:** `explorer/build.py` (`scorer_response`, `load_scorer_scores`), `crop_scorer/scoring/ui_input_mock.json` (default weights shape).

**Status:** [ ] pending

### 5. File-based hand-off to the web app (no API)
**Intent:** Make the results usable by the web app without a server: the module writes JSON files the frontend reads like it already reads `explorer.json`.

**Expected Outcomes**
- A small CLI (for example `uv run python -m advisor.export`) that writes: the glossary (for tooltips), plus pre-computed explanations (`explain_score` and caveats) for the current rotation and the top picks, under `explorer/examples/` or a similar folder.
- Optionally pre-computed re-rank results for a fixed set of weight presets (for example water-first, soil-first, balanced), so a slider or preset buttons work without a backend. Free-form weights stay possible only where Python runs (see Future Outlook).
- A short doc listing each file, its shape and an example, so the frontend can map "Explain this" buttons and tooltips onto it.
- Output is validated (pydantic, `extra="forbid"`, like the existing contract) and covered by a test.

**Todo List**
1. Define the output file shapes and validate them with pydantic models.
2. Implement the export CLI over the functions from sub-tasks 1-4.
3. Document the files and add a test that the export runs on the example data.

**Relevant Context:** `explorer/build.py` (`main`, how `explorer.json` is written and validated), `explorer/examples/`.

**Status:** [ ] pending

## Review TODO: agronomic correctness of the wording (open)

**Status:** [ ] open, no reviewer assigned yet. Until then every glossary entry carries `reviewed: false`.

Suggested reference sources, most are already used by the repo's data, so wording can be checked against the same material:
- **ET0, ETc, Kc, Ks, root depth (water):** FAO Irrigation and Drainage Paper 56 (FAO-56), the basis of the repo's water model (`data/processed/crop_data/fao56/`).
- **Nitrogen need and previous-crop credit:** K-State MF2586 (K-State Research and Extension nitrogen recommendations), basis of `crop_scorer/scoring/nitrogen.py`.
- **Heat, cold, kill temperatures:** FAO Ecocrop database (`data/processed/crop_data/ecocrop/`).
- **Weather and temperature data (measured):** NASA POWER documentation, for describing what "measured" means.
- **Yields, planting/harvest windows:** USDA NASS QuickStats and Crop Progress calendar.
- **Soil water capacity, organic matter:** USDA NRCS SSURGO.
- **Rotation effects (for example continuous-corn penalty):** the literature table in `data/processed/crop_data/literature/rotation_effects_clean.csv`; cite the underlying paper per entry.
- Possible human reviewers to ask: a K-State or local extension agent for Kansas wording, or a farmer for readability (not agronomy).

## Future Outlook (not in scope now)
- **MCP server** (`mcp_server/`, stdio): a thin wrapper that registers the `advisor` functions as tools and the glossary as a resource, for demos in Bob or Claude Desktop. It would contain no logic of its own, and the `build-mcp-server` skill covers the setup. Nothing in sub-tasks 1-5 blocks this.
- **LLM chat in the web app** on top of the same functions, with guardrails against invented numbers; needs a backend and an API key.
- **HTTP API** (for example FastAPI) for free-form weights from the slider.

## Possible sources
Review TODO: the agronomic review of the glossary wording is now an open TODO with no owner assigned. Glossary entries stay reviewed: false until someone checks them. I suggested reference sources per topic, most of which the repo's data already uses:
Water: FAO-56
Nitrogen: K-State MF2586
Temperature limits: FAO Ecocrop
Measured weather: NASA POWER
Yields and calendar: USDA NASS
Soil: NRCS SSURGO
Rotation effects: the underlying papers behind rotation_effects_clean.csv