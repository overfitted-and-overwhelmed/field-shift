# field-shift
Helping farmers adapt crop rotations to a changing climate using NASA Earth data and ML. NASA Space Apps Challenge 2026.

## Farmer advisor (plain-language answers, no API)

`advisor/` reads `explorer.json` and the scorer's `rotation_scores.csv` and answers in plain language: rotation
lookups, a glossary (`advisor/glossary.json`), "why does this rotation rank here?", data caveats and re-ranking with
the farmer's own weights. No LLM, sentences come from templates. All glossary entries are `reviewed: false` until an
agronomist has checked the wording (see `farmer-advisor-plan.md`, Review TODO).

```bash
uv run python -m advisor.export   # writes explorer/examples/advisor/{glossary,explanations,presets}.json for the web app
```

| File | For |
|---|---|
| `glossary.json` | tooltips: short and long text per term, also keyed by data field name (`cold_stress_years_pct`, ...) |
| `explanations.json` | per rotation: `explain` (rank and criteria in words), `caveats`, `trade_offs_vs_current` |
| `presets.json` | top rotations for fixed weight presets (balanced, water, risk, soil, fertilizer) |

Run it again after `uv run python -m explorer.build`; a test fails if the committed files are stale.

### MCP server (for AI clients such as Bob or Claude Desktop)

A thin wrapper over the same functions (`mcp_server/`), over stdio:

```bash
uv run python -m mcp_server
```

In Bob it is registered in `.bob/mcp.json` (server `field-shift-advisor`). For Claude Desktop add to its config:

```json
{ "mcpServers": { "field-shift-advisor": {
    "command": "uv", "args": ["run", "--directory", "/absolute/path/to/field-shift", "python", "-m", "mcp_server"] } } }
```

Tools: `get_field_overview`, `list_top_rotations`, `get_rotation`, `compare_rotations`, `get_monthly_table`,
`rerank_rotations`, `explain_rotation_score`, `get_data_caveats`, `explain_term`, `list_terms`.
Resources: `glossary://terms`, `rotations://ids`. Prompts: `explain_my_recommendation`, `what_if_i_care_more_about`.

Try: "Explain the picks for my field in simple words", "What if water matters most to me?", "What is p10?".
