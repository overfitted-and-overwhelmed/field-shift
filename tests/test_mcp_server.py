"""Smoke test of the MCP server over the real stdio protocol: spawn it as a child process and call it as a client."""

import json
import sys

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from advisor.data import REPO_ROOT

PARAMS = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server"], cwd=str(REPO_ROOT))


def _payload(result):
    """The JSON of a tool result (structured content if present, else the text)."""
    assert not result.is_error, result.content
    if result.structured_content is not None:
        data = result.structured_content
        return data.get("result", data) if isinstance(data, dict) and set(data) == {"result"} else data
    return json.loads(result.content[0].text)


async def _session_run(fn):
    async with stdio_client(PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await fn(session)


def run(fn):
    return anyio.run(_session_run, fn)


def test_server_lists_tools_resources_and_prompts():
    async def check(session):
        tools = {t.name for t in (await session.list_tools()).tools}
        resources = {str(r.uri) for r in (await session.list_resources()).resources}
        prompts = {p.name for p in (await session.list_prompts()).prompts}
        return tools, resources, prompts

    tools, resources, prompts = run(check)
    assert tools == {
        "get_field_overview", "list_top_rotations", "get_rotation", "compare_rotations", "get_monthly_table",
        "rerank_rotations", "explain_rotation_score", "get_data_caveats", "explain_term", "list_terms",
    }
    assert resources == {"glossary://terms", "rotations://ids"}
    assert prompts == {"explain_my_recommendation", "what_if_i_care_more_about"}


def test_tools_answer_over_the_protocol():
    async def check(session):
        overview = _payload(await session.call_tool("get_field_overview", {}))
        rerank = _payload(await session.call_tool("rerank_rotations", {"water": 4, "risk": 1, "top_n": 3}))
        term = _payload(await session.call_tool("explain_term", {"term": "p10"}))
        explain = _payload(await session.call_tool("explain_rotation_score", {"rotation_id": "corn-corn-corn"}))
        return overview, rerank, term, explain

    overview, rerank, term, explain = run(check)
    assert overview["current_rotation"]["id"] == "corn-corn-corn"
    assert len(rerank["rotations"]) == 3 and rerank["weights"]["water"] == 4
    assert term["key"] == "spread"
    assert explain["summary"].startswith("Corn")


def test_errors_reach_the_client_with_a_fix_hint():
    async def check(session):
        unknown = await session.call_tool("get_rotation", {"rotation_id": "corn-soybean-sorgum"})
        no_weights = await session.call_tool("rerank_rotations", {})
        return unknown, no_weights

    unknown, no_weights = run(check)
    assert unknown.is_error and "Close matches" in unknown.content[0].text
    assert no_weights.is_error and "At least one weight" in no_weights.content[0].text


def test_resources_can_be_read():
    async def check(session):
        glossary = await session.read_resource("glossary://terms")
        ids = await session.read_resource("rotations://ids")
        return glossary.contents[0].text, ids.contents[0].text

    glossary, ids = run(check)
    assert "terms" in json.loads(glossary)
    assert "corn-corn-corn" in json.loads(ids)


@pytest.mark.parametrize("name", ["explain_my_recommendation"])
def test_prompt_is_available(name):
    async def check(session):
        return await session.get_prompt(name, {})

    result = run(check)
    assert "get_field_overview" in result.messages[0].content.text
