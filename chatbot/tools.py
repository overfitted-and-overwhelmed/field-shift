"""Tools of the chatbot: the ``advisor`` functions in the OpenAI function format, plus ``run_tool``.

The tool names and parameters are the same as in the MCP server (``mcp_server/server.py``); a test keeps the two lists
equal. The model can only call a tool of this fixed list, every tool only reads files.

Tool results are JSON strings. A failure the model can fix (unknown rotation, bad weights, missing argument) comes
back as ``{"error": "..."}`` with the advisor's fix hint, so the model can retry.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import advisor

WEIGHT = {"type": "number", "minimum": 0}
ROTATION_ID = {
    "type": "string",
    "description": "Rotation id like 'corn-soybean-sorghum' or 'corn-soybean-sorghum+triticale'.",
}


def _tool(name: str, description: str, properties: dict[str, Any] | None = None, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties or {},
                "required": required or [],
                "additionalProperties": False,
            },
        },
    }


TOOLS: list[dict[str, Any]] = [
    _tool("get_field_overview",
          "The field (location, soil, crop history), its climate in short, the current rotation and the top picks."),
    _tool("list_top_rotations",
          "The n best rotations of all tested ones with equal weights, best first.",
          {"n": {"type": "integer", "minimum": 1, "maximum": 50},
           "cover_crop": {"type": "boolean", "description": "true: only with cover crop, false: only without."}}),
    _tool("get_rotation",
          "One rotation: scores, rank, and (for the current rotation and the top picks) seasons with yield and "
          "irrigation ranges, nitrogen and summary.",
          {"rotation_id": ROTATION_ID}, ["rotation_id"]),
    _tool("compare_rotations",
          "Two rotations side by side, with the differences (b minus a) and the main trade-offs in plain words.",
          {"rotation_a": ROTATION_ID, "rotation_b": ROTATION_ID}, ["rotation_a", "rotation_b"]),
    _tool("get_monthly_table",
          "Water (ET, rain, irrigation) and risk (heat, cold stress, frost-kill, in percent of years) per month. "
          "Only the current rotation and the top picks have months.",
          {"rotation_id": ROTATION_ID}, ["rotation_id"]),
    _tool("rerank_rotations",
          "Re-rank all rotations with the farmer's own priorities. Weights are non-negative numbers, only their "
          "ratio matters (water=3, risk=1 means water counts three times as much as risk). Criteria left at 0 do "
          "not count. At least one weight must be above 0.",
          {"water": WEIGHT, "risk": WEIGHT, "soil_health": WEIGHT, "nitrogen": WEIGHT,
           "top_n": {"type": "integer", "minimum": 1, "maximum": 50}}),
    _tool("explain_rotation_score",
          "Why a rotation has its rank: per criterion the score, the weight and the contribution to the total, plus "
          "a ready plain-language summary. Default weights count all four criteria equally.",
          {"rotation_id": ROTATION_ID, "water": WEIGHT, "risk": WEIGHT, "soil_health": WEIGHT, "nitrogen": WEIGHT},
          ["rotation_id"]),
    _tool("get_data_caveats",
          "How far to trust the numbers of a rotation: placeholder values, missing nitrogen amounts, model limits, "
          "assumptions and the sources behind the data.",
          {"rotation_id": ROTATION_ID}, ["rotation_id"]),
    _tool("explain_term",
          "A farmer-friendly explanation of a term or data field, for example 'ET0', 'p10', "
          "'cold_stress_years_pct', 'bare months' or 'provenance label'.",
          {"term": {"type": "string"}}, ["term"]),
    _tool("list_terms", "All glossary terms with a one-line explanation."),
]

TOOL_NAMES = [t["function"]["name"] for t in TOOLS]
MAX_RESULT_CHARS = 20_000  # a tool result is cut here, so one call cannot fill the model's context


def _weights(args: dict[str, Any], default: float) -> dict[str, float]:
    return {name: args.get(name, default) for name in ("water", "risk", "soil_health", "nitrogen")}


def _rerank(a: dict[str, Any]) -> Any:
    return advisor.rerank(_weights(a, 0), a.get("top_n", 5))


def _explain_score(a: dict[str, Any]) -> Any:
    return advisor.explain_score(a["rotation_id"], _weights(a, 1))


HANDLERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "get_field_overview": lambda a: advisor.field_overview(),
    "list_top_rotations": lambda a: advisor.list_top_rotations(a.get("n", 10), a.get("cover_crop")),
    "get_rotation": lambda a: advisor.get_rotation(a["rotation_id"]),
    "compare_rotations": lambda a: advisor.compare_rotations(a["rotation_a"], a["rotation_b"]),
    "get_monthly_table": lambda a: advisor.monthly_table(a["rotation_id"]),
    "rerank_rotations": _rerank,
    "explain_rotation_score": _explain_score,
    "get_data_caveats": lambda a: advisor.get_data_caveats(a["rotation_id"]),
    "explain_term": lambda a: advisor.explain_term(a["term"]),
    "list_terms": lambda a: advisor.list_terms(),
}


def _error(message: str) -> str:
    return json.dumps({"error": message})


def run_tool(name: str, arguments: str | dict[str, Any] | None) -> str:
    """Run one tool and return its result as a JSON string. ``arguments`` is the JSON text the model sent.

    Never raises for a wrong call: unknown tool, invalid JSON, missing or unknown arguments and advisor errors
    (unknown rotation, bad weights, no monthly detail) come back as ``{"error": ...}`` so the model can correct it.
    """
    handler = HANDLERS.get(name)
    if handler is None:
        return _error(f"Unknown tool '{name}'. Available tools: {', '.join(TOOL_NAMES)}.")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments) if arguments.strip() else {}
        except json.JSONDecodeError:
            return _error("The arguments are not valid JSON. Send a JSON object.")
    if arguments is None:
        arguments = {}
    if not isinstance(arguments, dict):
        return _error("The arguments must be a JSON object.")

    schema = next(t["function"]["parameters"] for t in TOOLS if t["function"]["name"] == name)
    unknown = sorted(set(arguments) - set(schema["properties"]))
    if unknown:
        return _error(f"Unknown arguments {unknown} for '{name}'. Known: {', '.join(schema['properties']) or 'none'}.")
    missing = [k for k in schema["required"] if k not in arguments]
    if missing:
        return _error(f"Missing required arguments {missing} for '{name}'.")

    try:
        result = json.dumps(handler(arguments), ensure_ascii=False)
    except (ValueError, TypeError) as error:  # advisor errors are ValueError, a wrong argument type is TypeError
        return _error(str(error))
    if len(result) > MAX_RESULT_CHARS:
        return _error("The result is too long. Ask for fewer rotations or a narrower question.")
    return result
