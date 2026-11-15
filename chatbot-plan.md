# Chatbot Plan (LLM chat for the farmer, next to the graphs)

## Top-Level Overview

**Goal:** A chat window next to the graphs of the web app. The farmer asks in their own words ("Why is rotation 2 better?", "What if water matters most to me?", "What is p10?") and gets a short answer in simple language, based only on the numbers of the advisor.

**Approach:** A small Python backend (`chatbot/`, FastAPI) that calls the Gemini OpenAI-compatible API (`https://generativelanguage.googleapis.com/v1beta/openai/`, model `gemini-3-flash-preview`; switched from NVIDIA/GLM because the team has a free Gemini key) with tool calling. The tools are the existing `advisor` functions (called directly, not over MCP). The frontend sends the conversation and the current page context (which rotation is shown, which weights are set) and shows the answer. The MCP server stays for Bob / Claude Desktop and is not part of this path.

```
Browser chat window -> POST /chat -> chatbot (system prompt + tools) -> Gemini API
                                          |  tool calls
                                          v
                                      advisor functions -> explorer.json, rotation_scores.csv, glossary.json
```

**Non-goals (for now):** the frontend chat window itself (comes later, this plan only fixes the contract), user accounts or stored chat history, streaming, voice, translating the glossary, any change to the scorer or explorer.

**Decisions (from the user)**
- The backend is deployed on Vercel. The frontend talks to it with JSON (the `POST /chat` contract). The model is now Gemini (key as `LLM_API_KEY`); it was not available at first, so sub-tasks 2-6 are built and tested with a fake model client, and sub-task 1 (spike against the real API) waits for the key.
- Vercel notes, not verified here and to check at deployment: functions are serverless, so an in-memory rate limit is per instance only and the file system is read-only. The advisor only reads files, but `explorer.json`, `rotation_scores.csv` and `glossary.json` must be part of the deployed bundle. Function timeout limits matter for a model call with several tool rounds. The key is set as a Vercel environment variable, never in the repo.

**Findings from research**
- The advisor functions return JSON-serializable dicts and raise `ValueError` subclasses with fix hints (unknown rotation with close matches, bad weights). The agent can pass these messages back to the model so it corrects the call.
- `mcp_server/server.py` already holds the tool names, descriptions, parameter lists and the guardrail text (`INSTRUCTIONS`). The chatbot needs the same tools in OpenAI function format.
- The repo has no HTTP backend yet. `uvicorn` and `starlette` are already installed as dependencies of `mcp`; `openai` and `fastapi` are not in `pyproject.toml`.
- `.env.example` exists (`NASS_API_KEY`) and `.env` is git-ignored: the same pattern holds the new key.
- A snippet like `api_key="$LLM_API_KEY"` is a literal string in Python and is not expanded. The key must be read from the environment (`LLM_API_KEY`) and never written into code or committed.
- Not verified: whether Gemini on the OpenAI-compatible Gemini endpoint supports tool calling (function calling), its rate limits, and its quality in other languages. Sub-task 1 checks this first; the rest of the plan depends on it.

## Sub-Tasks

### 1. Spike: connect to the model and check tool calling
**Intent:** Find out early whether the model can do what the design needs, before building on it.

**Expected Outcomes**
- A small script / test that reads the key from the environment, calls the model once, and once with a tool definition (for example `explain_term`).
- A written result in this plan: tool calling works / works partly / does not work, plus observed latency, and the answer to "does it answer in German when asked in German".
- If tool calling does not work: a decision on the fallback (see Open Questions) before sub-task 2.

**Todo List**
1. Add `openai` as a dependency (`uv add openai`) and `LLM_API_KEY=` to `.env.example`.
2. Load the key from the environment (and from `.env`, as the NASS fetch script does); fail with a clear message if it is missing.
3. Run the plain call and the tool-call test against the real API (needs a key set by the user, outside the chat).
4. Record the result and the model's limits (max tokens, rate limit) in this plan.

**Relevant Context:** `data/fetch-scripts/quickstats.py` (how `NASS_API_KEY` is loaded), `.env.example`, `pyproject.toml`.

**Status:** [~] partly done (spike on 2026-11-15, manual calls, not the full live test suite). Result:
- `gemini-3-flash-preview` on the OpenAI-compatible endpoint works with tool calling. One question in German ran 3 tool calls and answered in German in 7.3 s.
- `gemini-flash-latest` and `gemini-3.8-flash` hung until the timeout (40-80 s, also from the owner's machine), `gemini-3.7-flash` hung, `gemini-3.5-flash` answered empty with `max_tokens=20`, `gemini-2.5-flash` gives 404 ("no longer available to new users"), `gemini-3.1-flash-lite-preview` gave a 503 once. Cause not investigated.
- Gemini 3 sends a `thought_signature` in `extra_content` of each tool call and answers 400 if the next request does not send it back. `chatbot/agent.py` (`_echo_tool_call`) now passes extra fields of the call on unchanged; a test covers it.
- Free tier limit seen: 5 requests per minute for `gemini-3-flash` (HTTP 429). One chat turn with tools uses 2 to 4 requests, so about 1 to 2 turns per minute. Not enough for several users at once.
- Still open: the 8 live guardrail tests, the quality of the answers (the one answer was not checked against the data), preview model may change or be removed.

### 2. Tool registry for the chat
**Intent:** One list of tools in the OpenAI function format that maps to the `advisor` functions, so the model can call them.

**Expected Outcomes**
- `chatbot/tools.py` with the JSON schema of each tool and a `run_tool(name, arguments)` that calls the advisor function and returns JSON.
- Same tool names and parameters as the MCP server (`get_field_overview`, `list_top_rotations`, `get_rotation`, `compare_rotations`, `get_monthly_table`, `rerank_rotations`, `explain_rotation_score`, `get_data_caveats`, `explain_term`, `list_terms`).
- `ValueError` from the advisor becomes a tool result with `error` and the fix hint, not a crash. Unknown tool names and invalid arguments are handled the same way.
- A test checks that the chat tool names equal the MCP tool names, so the two cannot drift apart.

**Todo List**
1. Write the schemas from the existing tool signatures and docstrings in `mcp_server/server.py`.
2. Implement `run_tool` with argument validation and error mapping.
3. Add the consistency test against `mcp_server.server.server`.

**Relevant Context:** `mcp_server/server.py` (tool list), `advisor/__init__.py` (public functions), `advisor/data.py` (`UnknownRotationError`).

**Status:** [x] done (waiting for review)

**Notes (what was built)**
- `chatbot/tools.py`: `TOOLS` (OpenAI function format, 10 tools), `HANDLERS`, `run_tool(name, arguments)`. Same names as the MCP server; `test_chat_tools_equal_the_mcp_tools` keeps them equal. A wrong call (unknown tool, bad JSON, missing or unknown arguments, advisor `ValueError`, wrong type) returns `{"error": ...}` with the fix hint, never raises. A result over 20,000 characters is replaced by an error.

### 3. Agent loop and system prompt
**Intent:** The part that talks to the model: send the conversation, run the requested tools, return the final answer.

**Expected Outcomes**
- `chatbot/agent.py`: `answer(messages, context)` loops (a fixed maximum number of tool rounds) until the model gives a text answer. It returns the answer and the list of tools called with their arguments (for transparency in the UI).
- `chatbot/prompt.py`: system prompt built from the guardrails in `INSTRUCTIONS` plus: answer in the language of the farmer, short sentences, only numbers from tool results, null is not zero, always mention relevant caveats (placeholder, assumptions, nitrogen pending), say that scores compare tested rotations and are no promise of yield, refuse topics outside the field data, never invent a rotation id.
- The page context (rotation id shown, weights set in the UI) is added to the prompt, so "this rotation" in a question has a meaning.
- Timeouts and API errors give a clear, friendly failure (no stack trace to the user).

**Todo List**
1. Implement the loop with a maximum number of rounds and a maximum answer length.
2. Write the prompt and the context block.
3. Handle API errors (timeout, rate limit, invalid key) and a model that returns no text.
4. Tests with a fake client (no network): one tool round, two rounds, tool error, round limit reached.

**Relevant Context:** `mcp_server/server.py` (`INSTRUCTIONS`, prompts), results of sub-task 1.

**Status:** [x] done (waiting for review), tested with a fake model only

**Notes (what was built)**
- `chatbot/agent.py`: `answer(messages, context, client=None, settings=None)` returns `AgentResult(answer, tool_calls, caveats_shown)`. Up to 5 tool rounds and 4 calls per round; after the limit the model is asked once more without tools. Every tool call gets an answer (also the ones over the limit). Provider errors become `ChatError` with a short code (`rate_limited`, `timeout`, `unavailable`, `empty`), no provider text.
- `chatbot/prompt.py`: system prompt with the guardrails (only tool numbers, null is not zero, caveats, short answers in the farmer's language, only this field, ignore instructions in questions) plus the page context marked as data. `chatbot/config.py`: settings from the environment or `.env`; overrides `LLM_BASE_URL`, `CHAT_MODEL`, `CHAT_MAX_TOKENS`, `CHAT_TIMEOUT_S`. Temperature 0.3, max 700 tokens.
- Not verified: how the real model behaves with this prompt (needs the key).

### 4. HTTP endpoint for the web app
**Intent:** Make the chat reachable from the browser without exposing the key.

**Expected Outcomes**
- `chatbot/api.py` (FastAPI): `POST /chat` and `GET /health`. Run with `uv run uvicorn chatbot.api:app`.
- Request: `messages` (list of role + text, the frontend keeps the history) and `context` (`rotation_id`, `weights`, both optional). Response: `answer`, `tool_calls` (name + arguments, for a "based on" line), `caveats_shown` flag.
- Limits: maximum message length, maximum number of history messages, a simple rate limit per client, and CORS limited to the configured web app origin (set by an environment variable).
- Request and response models are pydantic with `extra="forbid"`, like the existing contract.
- The API key is read on the server only and never appears in a response or in logs.

**Todo List**
1. Add `fastapi` as a dependency and define the pydantic models.
2. Implement the endpoints, limits and CORS from environment variables.
3. Tests with FastAPI's test client and the fake model client.

**Relevant Context:** `explorer/schema.py` (`_Strict` pattern), `.env.example`.

**Status:** [x] done (waiting for review)

**Notes (what was built)**
- `chatbot/api.py`: `create_app(client, settings, rate_per_minute)` and `app`. `POST /chat`, `GET /health`; docs pages are off. Limits: 20 messages, 2000 characters each, rate limit 20/min per client (`CHAT_RATE_PER_MIN`, in memory), CORS only for `CHAT_ALLOWED_ORIGINS`. Models are pydantic with `extra="forbid"`; weights are checked with the advisor's `validate_weights`. A rejected request returns a generic 422 that does not echo the farmer's text. The app starts without a key and answers 503 for a chat.
- Entry point for Vercel: `index.py`; `.vercelignore` keeps only what the chatbot reads. A copy of the repo with just these files (740 KB) starts and answers `/health` and `/chat` (503 without key). Not deployed, the Vercel CLI is not installed here, so the Python function setup is unverified.

### 5. Guardrail tests and example questions
**Intent:** Show that the answers rely on tool data, and keep it that way when the prompt or the model changes.

**Expected Outcomes**
- A fixed set of example questions (for example: why is rank 1 ranked first, what if water matters most, what is p10, what is the nitrogen amount of pick 2 where it is still null, a question outside the topic, a made-up rotation) with the expected tool calls.
- A check that numbers in the answer appear in the tool results of the same turn (a simple automatic check on the fake or recorded model output), and that a null value is not stated as zero.
- An optional live test against the real API, skipped when no key is set, run by hand before showing the chatbot to anyone.

**Todo List**
1. Write the question set with expected tools.
2. Implement the number check as a test helper.
3. Add the skipped-by-default live test.

**Relevant Context:** `tests/test_mcp_server.py` (test style), `advisor/glossary.json` (`nitrogen_pending`, `placeholder` texts).

**Status:** [x] done (waiting for review). The live part still has to be run with a key.

**Notes (what was built)**
- `tests/chat_checks.py`: `ungrounded_numbers(answer, tool_results, context)` (a number of the answer must be in a tool result, also rounded or as percent; counting words up to 10 and numbers of the question are allowed) and `states_null_as_zero`. These checks are tested on good and bad example answers.
- `tests/test_chatbot_guardrails.py`: 6 example questions with the expected tools, an out-of-topic question and a prompt-injection question, run against the real model only with `RUN_LIVE_CHAT=1` and a key (8 tests, skipped otherwise). The heuristic catches an invented number, it cannot judge wording.

### 6. Frontend contract
**Intent:** The chat window comes later; this step lets the frontend be built without guessing.

**Expected Outcomes**
- A short doc (in the README or next to the chatbot) with the request / response JSON, error cases and an example conversation, how the page context is sent, and how to show `tool_calls` as a "based on" line.
- Notes for the UI: a visible hint that results are model values and the wording is not yet agronomically reviewed (the glossary is still `reviewed: false`), and that messages are sent to an external LLM provider.

**Todo List**
1. Write the contract and examples from the real responses of sub-task 4.
2. Add the UI notes.

**Relevant Context:** `README.md` (advisor section), `farmer-advisor-plan.md` (Review TODO).

**Status:** [x] done (waiting for review). Contract and UI notes are in the README, section "Chatbot for the web app".

## Open Questions
- **Tool calling on this model** (sub-task 1). Fallback if it does not work: the backend picks the data itself (keyword rules or a first model call that only returns a tool name as JSON), puts the tool results into the prompt, and the model only writes the answer. This is simpler to guard but less flexible. Another fallback is a different Gemini model.
- **Language:** the glossary is English. The model can answer in the language of the question; the quality for the farmer's language is not verified.
- **Privacy:** the farmer's messages go to an external provider (Google Gemini). Decide what the UI tells the farmer, and whether messages are logged (default: no content logging).
- **Hosting and cost:** where the backend runs, who owns the key, and what rate limit protects it.
- **Shared tool definitions:** the chat registry duplicates the tool list of the MCP server for now (a test keeps them equal). A later step could generate both from one definition.
- **Review of wording:** the agronomic review of the glossary stays open (see `farmer-advisor-plan.md`). The chatbot repeats that wording, so it should be done before real farmers use it.

## Security notes
- Read `LLM_API_KEY` from the environment or `.env` only. Do not put the key in code, tests, README examples or this plan, and do not paste it into the chat.
- Treat user text as untrusted: it must not be able to change the system prompt, call tools with other names, or read files. Tools are a fixed list and read only.
