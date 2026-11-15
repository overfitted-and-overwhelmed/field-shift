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

**Status:** [x] done (waiting for review)

**Notes for sub-task 2 and later (what was built)**
- Layout: `advisor/__init__.py` (public API + errors), `advisor/data.py` (loading), `advisor/lookup.py` (lookups), tests in `tests/test_advisor_core.py`. No existing module was changed.
- `advisor/data.py`: `load_export()` (validated `ExplorerExport`, `@cache`), `load_scores()` (CSV via `explorer.field_calendar.load_scorer_scores`, ranked with the scorer's `rank` and `DEFAULT_WEIGHTS` = equal weights for all four criteria, indexed by rotation id, has `rank`, `total_score`, `*_score`), `known_ids()`, `check_id(id)`. Errors: `UnknownRotationError` (has `.rotation_id`, `.close_matches`, message lists them) and `DetailNotAvailableError`. Both are `ValueError`.
- `advisor/lookup.py` (all return JSON-serializable dicts/lists): `field_overview()`, `list_top_rotations(n=10, cover_crop=None)`, `get_rotation(id)`, `compare_rotations(a, b)` (`diff` = b minus a), `monthly_table(id)`.
- Result shape of a rotation: `id, name, crops, cover_crop, is_current, pick (1-3 or None), rank_all, total_score, score_parts {water, risk, soil_health, nitrogen} (0 = best), detail_level ("full" | "scores_only"), flags {placeholder, nitrogen_null}`; `get_rotation` adds `short, kpi, n_rotations, weights, seasons, summary, note`. `seasons`/`summary` are None for `scores_only`.
- Detail levels: only the 4 rotations in `explorer.json` (current + 3 picks) are `"full"`. All other candidates are `"scores_only"`, with `flags.placeholder = None` (unknown) and `flags.nitrogen_null = True` (the CSV has the nitrogen score but no amounts). `monthly_table` raises `DetailNotAvailableError` for them.
- Flags: `flags.nitrogen_null` is true while any season `n_lb` / `n_adj_lb`, `summary.n_loss_lb` or month `nitrogen` is null (currently true for all full rotations). Nulls stay null, differences with a null side are null, never 0.
- Scores, rank and KPIs always come from the CSV with equal weights (`rank_all` out of 225). The `rank` in `explorer.json` is the pick number (1-3) and is exposed as `pick`. For `explain_score` (sub-task 3) and `rerank` (sub-task 4), reuse `advisor.data.load_scores()` / `crop_scorer.scoring.score_rotations.rank` and `CRITERIA`. Note that `rank` ignores criteria missing from the weights.
- Provenance and `sources` of `explorer.json` are not part of the lookup results yet. Season `effects` already carry their `provenance` label and `source` key. `load_export().provenance` / `.sources` are available for `get_data_caveats`.
- `pyproject.toml` `testpaths` is `tests` and `explorer`, so doctests in `advisor/` are not collected (no doctests used).

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

**Status:** [x] done (waiting for review). Agronomic review (todo 4) stays open, see Review TODO.

**Notes (what was built)**
- `advisor/glossary.json` (terms + sentence templates), `advisor/glossary.py` (`explain_term`, `list_terms`, `UnknownTermError`). A term is found by key, alias (also data field names such as `cold_stress_years_pct`, `et0_apr_sep_in`) or title, in any case.
- Tests (`tests/test_advisor_explain.py`) check that every provenance label, criterion, `MonthDetail` / `MonthNitrogen` / `Summary` / `SeasonDetail` field and every field name in `provenance` resolves to an entry, and that every entry is `reviewed: false`.

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

**Status:** [x] done (waiting for review)

**Notes (what was built)**
- `advisor/explain.py`: `explain_score(id, weights=None)`, `trade_offs(a, b)`, `get_data_caveats(id)`. `compare_rotations` now includes `trade_offs`. Score levels: <= 1/3 good, <= 2/3 middle, above weak. Trade-offs are reported from a score difference of 0.1 (`trade_off_threshold` in glossary.json).
- Criteria with weight 0 are shown but not used for the strongest / weakest point. Scores-only rotations get no season-level assumptions or literature effects in the caveats.

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

**Status:** [x] done (waiting for review)

**Notes (what was built)**
- `advisor/rerank.py`: `rerank(weights=None, top_n=10)`, `validate_weights`, `ranked_scores`. Uses the scorer's `rank`; a test checks that default weights reproduce the picks of `explorer.json`. Omitted criteria get weight 0.

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

**Status:** [x] done (waiting for review)

**Notes (what was built)**
- `uv run python -m advisor.export` writes `glossary.json`, `explanations.json` and `presets.json` to `explorer/examples/advisor/` (pydantic models with `extra="forbid"`, `contract_version` 1.0.0-draft). A test fails if the committed files are stale. Documented in the README.

## Review TODO: agronomic correctness of the wording (open)

**Status:** [x] part A done (2026-11-15): every glossary entry and template checked against the code it describes. [ ] part B open, no reviewer assigned: agronomic review. Every glossary entry keeps `reviewed: false` until part B; a test enforces it, so it must be changed when entries are reviewed (then also re-run `uv run python -m advisor.export`).

**Part A, what was fixed** (wording did not match the code):
- ETc / `et_in` described as actual use; it is the use without water stress (actual use is ETa = Ks x ETc).
- Water and irrigation: the need is on top of rain *and* stored soil water; the water score always counts the full need; cover crops are not irrigated.
- Risk and window: risk is averaged over main-crop days only, not over the window.
- Nitrogen: amounts per season *are* computed by the scorer, just not passed into explorer.json; the first season gets no previous-crop adjustment, so the field's previous crop does not change any score.
- Yield: levels are NASS district/state means, not county; sorghum and sunflower levels are derived; with full irrigation the p10/p90 range comes from NASS irrigated years, not weather years.
- `effects` also holds model notes and assumptions, not only studies. Bug fixed in `get_data_caveats`: NASS and scorer notes were reported as "a study from another region".
- Smaller: `rain_in` (per year in climate, per month in monthly), `deficit_apr_sep_in` (not the irrigation need), rank/picks, sowing/harvest rule, cover crop rule, kill thresholds (0 / -20 °C fallbacks), `heat_days` / `kill_days` key figures, weights need one value above 0.

**Part B, questions for the agronomist** (only modelling choices and general claims are left):
- Kill temperature: Ecocrop's early-growth value is used for the whole season; corn, sorghum, soybean have none and fall back to 0 °C; winter wheat in winter rest uses -20 °C. Reasonable for southwest Kansas?
- Cold-stress half-day rule and heat above the optimum range: sensible thresholds for "stress"?
- Bare-soil evaporation as 25 % of ET0; triticale water use like winter wheat; +27.5 lb N after triticale for every next crop.
- Yield response to the water deficit (FAO-33 idea, `ks` entry) and the Corn Belt / North Dakota effects applied to Kansas.
- The general `why_it_matters` sentences (erosion, slope, frost, fertilizer loss).

Suggested reference sources, most are already used by the repo's data, so wording can be checked against the same material:
- **ET0, ETc, Kc, Ks, root depth (water):** FAO Irrigation and Drainage Paper 56 (FAO-56), the basis of the repo's water model (`data/base-data/fao56/`).
- **Nitrogen need and previous-crop credit:** K-State MF2586 (K-State Research and Extension nitrogen recommendations), basis of `crop_scorer/scoring/nitrogen.py`.
- **Heat, cold, kill temperatures:** FAO Ecocrop database (`data/base-data/ecocrop/`).
- **Weather and temperature data (measured):** NASA POWER documentation, for describing what "measured" means.
- **Yields, planting/harvest windows:** USDA NASS QuickStats and Crop Progress calendar.
- **Soil water capacity, organic matter:** USDA NRCS SSURGO.
- **Rotation effects (for example continuous-corn penalty):** the literature table in `data/processed/crop_data/literature/rotation_effects_clean.csv`; cite the underlying paper per entry.
- Possible human reviewers to ask: a K-State or local extension agent for Kansas wording, or a farmer for readability (not agronomy).

## MCP server (added early for testing, was Future Outlook)
**Status:** [x] done (waiting for review)
- `mcp_server/` (stdio, Python `mcp` 2.3.0 with `MCPServer`): a thin wrapper over the `advisor` functions with no logic of its own. 10 tools, 2 resources (`glossary://terms`, `rotations://ids`) and 2 prompts. The advisor's `ValueError` becomes a `ToolError`, so the client sees the fix hint (unknown rotation with close matches, bad weights).
- Registered for Bob in `.bob/mcp.json` (server `field-shift-advisor`). Run: `uv run python -m mcp_server`. `tests/test_mcp_server.py` calls it over the real stdio protocol. Documented in the README.

## Future Outlook (not in scope now)
- **LLM chat in the web app** on top of the same functions, with guardrails against invented numbers; needs a backend and an API key.
- **HTTP API** (for example FastAPI) for free-form weights from the slider.