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

## Chatbot for the web app (backend, JSON)

`chatbot/` is a small FastAPI backend: an LLM (Gemini via its OpenAI-compatible endpoint, model `gemini-3-flash-preview`) answers the farmer's
questions and uses the `advisor` functions as tools, so every number comes from the data. The frontend only sends JSON.
The key stays on the server.

```bash
cp .env.example .env            # then add LLM_API_KEY=...  (on Vercel: an environment variable)
uv run uvicorn chatbot.api:app  # http://127.0.0.1:8000, entry point for Vercel: index.py
```

### `POST /chat`

The frontend keeps the conversation and sends it with every request (the server stores nothing).

```json
{
  "messages": [
    {"role": "user", "content": "What if water matters most to me?"}
  ],
  "context": {"rotation_id": "corn-corn-corn", "weights": {"water": 3, "risk": 1, "soil_health": 1, "nitrogen": 1}}
}
```

- `messages`: 1 to 20 entries, `role` is `user` or `assistant`, `content` 1 to 2000 characters. The last one must be from the user.
- `context` (optional): what the farmer sees, so "this rotation" or "my settings" has a meaning. `rotation_id` is a rotation id,
  `weights` are the slider values (criteria `water`, `risk`, `soil_health`, `nitrogen`, non-negative, at least one above 0).
- Unknown keys are rejected.

Answer `200`:

```json
{
  "answer": "With water counting most, the best rotation is Sunflower · Sunflower · Sunflower ...",
  "tool_calls": [
    {"name": "rerank_rotations", "arguments": {"water": 4, "top_n": 3}, "error": false}
  ],
  "caveats_shown": true
}
```

- `answer`: plain text in the language of the question.
- `tool_calls`: what the answer is based on. Show it as a "based on" line (for example "Based on: ranking with your priorities").
- `caveats_shown`: the model looked up the data caveats in this turn.

Errors have the shape `{"error": {"code": "...", "message": "..."}}`. The message is safe to show to the farmer.

| Status | `code` | Meaning |
|---|---|---|
| 422 | `invalid_request` | the request breaks a rule above |
| 429 | `rate_limited` | too many questions (this server or the model provider), try again in a minute |
| 502 | `empty` | the model gave no answer, ask again |
| 503 | `unavailable` | model or key not available |
| 504 | `timeout` | the model took too long |

`GET /health` returns `{"status": "ok"}`.

### Notes for the UI

- Show that the answers are **model values, not a promise of yield or profit**, and that the wording of the explanations
  is **not yet reviewed by an agronomist** (glossary `reviewed: false`, see `farmer-advisor-plan.md`).
- Tell the farmer that the **questions are sent to an external provider (Google Gemini)**. The server logs no message text.
- Send `context` whenever the page shows a rotation or the weight sliders.
- Cross-origin access is off by default: set `CHAT_ALLOWED_ORIGINS` to the origin of the web app.

### Vercel (not tested here)

`index.py` exposes the app, `.vercelignore` keeps the deployment small (the chatbot reads only `explorer/examples/explorer.json`,
`data/processed/rotation_scores/rotation_scores.csv` and `advisor/glossary.json`; a copy of the repo with just these files
starts and answers `/health`). Set `LLM_API_KEY` and `CHAT_ALLOWED_ORIGINS` in the Vercel project. The rate limit is
in memory, so each serverless instance counts for itself. Check the function timeout of your Vercel plan, a question
with several tool rounds can take a while.

Tests use a fake model: `uv run pytest tests/test_chatbot.py`. Against the real model (needs the key, by hand):
`RUN_LIVE_CHAT=1 uv run pytest tests/test_chatbot_guardrails.py -k live -s`.

