"""MCP server of the farmer advisor: a thin wrapper that exposes the ``advisor`` functions to AI clients
(Bob, Claude Desktop, ...) over stdio. It has no logic of its own, everything is read from the files of the repo.

    uv run python -m mcp_server

Tools return JSON-serializable dicts. Errors (unknown rotation, bad weights, ...) reach the client as tool errors
with a message that says how to fix the call, so the client can retry.
"""

from __future__ import annotations

import json
from typing import Any

from functools import wraps

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

import advisor
from advisor.data import known_ids
from advisor.glossary import GLOSSARY_FILE

INSTRUCTIONS = """\
Helps a farmer understand crop rotation results for one field (scorer and explorer data).
- Scores run from 0 (best) to 1 (worst) and compare the tested rotations with each other. They are no absolute grade.
- Use only numbers from the tools, never invent values. Always pass on the caveats (get_data_caveats):
  placeholder values, missing nitrogen amounts (null is not zero), assumptions and sources.
- Explain terms in simple words with explain_term. Short sentences, no jargon, units as given.
- Use rerank_rotations when the farmer says what matters to them (for example less water).
"""

server = MCPServer("field-shift-advisor", instructions=INSTRUCTIONS, version="0.1.0")


def advisor_tool(fn):
    """Register ``fn`` as a tool. The advisor's ``ValueError`` (unknown rotation, bad weights, ...) is an expected
    failure with a message that says how to fix the call, so it becomes a ``ToolError`` the client can read.
    Without it the client would only see 'Error executing tool'."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError as error:
            raise ToolError(str(error)) from error

    return server.tool()(wrapper)


@advisor_tool
def get_field_overview() -> dict[str, Any]:
    """The field (location, soil, crop history), its climate in short, the current rotation and the top picks."""
    return advisor.field_overview()


@advisor_tool
def list_top_rotations(n: int = 10, cover_crop: bool | None = None) -> list[dict[str, Any]]:
    """The n best rotations of all tested ones with equal weights, best first.

    cover_crop=True keeps only rotations with a cover crop, False only those without, omit for all.
    """
    return advisor.list_top_rotations(n, cover_crop)


@advisor_tool
def get_rotation(rotation_id: str) -> dict[str, Any]:
    """One rotation: scores, rank, and (for the current rotation and the top picks) seasons with yield and
    irrigation ranges, nitrogen and summary. rotation_id looks like 'corn-soybean-sorghum+triticale'."""
    return advisor.get_rotation(rotation_id)


@advisor_tool
def compare_rotations(rotation_a: str, rotation_b: str) -> dict[str, Any]:
    """Two rotations side by side, with the differences (b minus a) and the main trade-offs in plain words."""
    return advisor.compare_rotations(rotation_a, rotation_b)


@advisor_tool
def get_monthly_table(rotation_id: str) -> dict[str, Any]:
    """Water (ET, rain, irrigation) and risk (heat, cold stress, frost-kill, in percent of years) per month.
    Only the current rotation and the top picks have months."""
    return advisor.monthly_table(rotation_id)


@advisor_tool
def rerank_rotations(
    water: float = 0, risk: float = 0, soil_health: float = 0, nitrogen: float = 0, top_n: int = 5
) -> dict[str, Any]:
    """Re-rank all rotations with the farmer's own priorities. Weights are non-negative numbers, only their ratio
    matters (water=3, risk=1 means water counts three times as much as risk). Criteria left at 0 do not count.
    At least one weight must be above 0."""
    return advisor.rerank({"water": water, "risk": risk, "soil_health": soil_health, "nitrogen": nitrogen}, top_n)


@advisor_tool
def explain_rotation_score(
    rotation_id: str,
    water: float = 1,
    risk: float = 1,
    soil_health: float = 1,
    nitrogen: float = 1,
) -> dict[str, Any]:
    """Why a rotation has its rank: per criterion the score, the weight and the contribution to the total, plus a
    ready plain-language summary. Default weights count all four criteria equally."""
    weights = {"water": water, "risk": risk, "soil_health": soil_health, "nitrogen": nitrogen}
    return advisor.explain_score(rotation_id, weights)


@advisor_tool
def get_data_caveats(rotation_id: str) -> dict[str, Any]:
    """How far to trust the numbers of a rotation: placeholder values, missing nitrogen amounts, model limits,
    assumptions and the sources behind the data."""
    return advisor.get_data_caveats(rotation_id)


@advisor_tool
def explain_term(term: str) -> dict[str, Any]:
    """A farmer-friendly explanation of a term or data field, for example 'ET0', 'p10', 'cold_stress_years_pct',
    'bare months' or 'provenance label'. Use list_terms to see all."""
    return advisor.explain_term(term)


@advisor_tool
def list_terms() -> list[dict[str, Any]]:
    """All glossary terms with a one-line explanation."""
    return advisor.list_terms()


@server.resource("glossary://terms", mime_type="application/json")
def glossary() -> str:
    """The full plain-language glossary (terms and sentence templates)."""
    return GLOSSARY_FILE.read_text(encoding="utf-8")


@server.resource("rotations://ids", mime_type="application/json")
def rotation_ids() -> str:
    """Every rotation id the advisor knows."""
    return json.dumps(known_ids())


@server.prompt()
def explain_my_recommendation() -> str:
    """Explain the top picks of the field to a farmer in simple words."""
    return (
        "Use get_field_overview, then explain_rotation_score and get_data_caveats for the current rotation and the "
        "picks. Explain to a farmer in short, simple sentences why each pick ranks where it does and how it differs "
        "from the current rotation (compare_rotations). Use explain_term for any technical word. End with what is "
        "uncertain (caveats and assumptions). Do not invent numbers."
    )


@server.prompt()
def what_if_i_care_more_about(priority: str) -> str:
    """What changes if one priority (water, risk, soil_health or nitrogen) counts more."""
    return (
        f"The farmer cares most about '{priority}'. Use rerank_rotations with a high weight for it (for example 4) "
        "and 1 for the others, compare the result with list_top_rotations, and explain in simple words which "
        "rotations move up and what they give up (compare_rotations). Mention the caveats."
    )


def main() -> None:
    server.run("stdio")


if __name__ == "__main__":
    main()
