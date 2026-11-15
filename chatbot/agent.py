"""The chat agent: send the conversation to the model, run the tools it asks for, return the final answer.

The model client is passed in (anything with ``chat.completions.create`` like the OpenAI client), so tests use a fake
and need no network or key. Raw errors never reach the farmer: failures become a ``ChatError`` with a short message.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from chatbot.config import MissingApiKeyError, Settings, load_settings, make_client
from chatbot.prompt import build_system_prompt
from chatbot.tools import TOOLS, run_tool

CAVEATS_TOOL = "get_data_caveats"
UNAVAILABLE = "The assistant is not available right now. Please try again in a moment."


class ChatError(Exception):
    """A failure to show the farmer. ``code`` is machine readable, the message is safe to display."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass
class AgentResult:
    answer: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)  # name, arguments, error (bool)

    @property
    def caveats_shown(self) -> bool:
        """True if the model looked up the data caveats in this turn (the prompt asks it to)."""
        return any(c["name"] == CAVEATS_TOOL and not c["error"] for c in self.tool_calls)


def _log(message: str) -> None:
    print(f"[chatbot] {message}", file=sys.stderr)  # stderr, never the farmer's text or the key


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(raw) if raw and raw.strip() else {}
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _complete(client: Any, settings: Settings, messages: list[dict[str, Any]], *, with_tools: bool):
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "stream": False,
    }
    if with_tools:
        kwargs["tools"] = TOOLS
        kwargs["tool_choice"] = "auto"
    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as error:  # the provider's errors differ by version, the farmer gets one short message
        status = getattr(error, "status_code", None)
        _log(f"model call failed: {type(error).__name__} status={status}")
        if status == 429:
            raise ChatError("rate_limited", "The assistant is busy. Please try again in a minute.") from error
        if type(error).__name__ in ("APITimeoutError", "TimeoutError"):
            raise ChatError("timeout", "The assistant took too long. Please try a shorter question.") from error
        raise ChatError("unavailable", UNAVAILABLE) from error
    if not getattr(response, "choices", None):
        raise ChatError("empty", "The assistant gave no answer. Please ask again.")
    return response.choices[0].message


def answer(
    messages: Sequence[Mapping[str, str]],
    context: Mapping[str, Any] | None = None,
    *,
    client: Any = None,
    settings: Settings | None = None,
) -> AgentResult:
    """Answer the last farmer message. ``messages`` is the history, each ``{"role": "user" | "assistant", "content"}``.

    The model may call tools for up to ``max_tool_rounds`` rounds. If it is still asking for tools after that, it is
    asked once more without tools, so there is always a text answer or a ``ChatError``.
    """
    settings = settings or load_settings()
    if client is None:
        try:
            client = make_client(settings)
        except MissingApiKeyError as error:
            _log("LLM_API_KEY is missing")
            raise ChatError("unavailable", UNAVAILABLE) from error

    conversation: list[dict[str, Any]] = [{"role": "system", "content": build_system_prompt(context)}]
    conversation += [{"role": m["role"], "content": m["content"]} for m in messages]
    result = AgentResult(answer="")
    max_calls = settings.max_tool_rounds * settings.max_tool_calls_per_round

    for _ in range(settings.max_tool_rounds):
        message = _complete(client, settings, conversation, with_tools=True)
        calls = list(getattr(message, "tool_calls", None) or [])
        if not calls:
            return _finish(result, message)
        conversation.append({
            "role": "assistant",
            "content": getattr(message, "content", None),
            "tool_calls": [_echo_tool_call(c) for c in calls],
        })
        for call in calls:
            if len(result.tool_calls) >= max_calls:
                # every tool call needs an answer, or the next request would be invalid
                conversation.append({"role": "tool", "tool_call_id": call.id,
                                     "content": json.dumps({"error": "Too many tool calls in this turn."})})
                continue
            output = run_tool(call.function.name, call.function.arguments)
            result.tool_calls.append({
                "name": call.function.name,
                "arguments": _parse_arguments(call.function.arguments),
                "error": output.startswith('{"error"'),
            })
            conversation.append({"role": "tool", "tool_call_id": call.id, "content": output})

    _log("tool round limit reached, asking for a final answer without tools")
    return _finish(result, _complete(client, settings, conversation, with_tools=False))


def _echo_tool_call(call: Any) -> dict[str, Any]:
    """The tool call as the next request needs it. Gemini 3 puts a ``thought_signature`` into ``extra_content`` and
    rejects the request (400) if it is not sent back, so extra fields of the call are passed on unchanged."""
    echoed: dict[str, Any] = {
        "id": call.id,
        "type": "function",
        "function": {"name": call.function.name, "arguments": call.function.arguments},
    }
    extra = getattr(call, "model_extra", None)
    if isinstance(extra, dict):
        echoed.update(extra)
    return echoed


def _finish(result: AgentResult, message: Any) -> AgentResult:
    text = (getattr(message, "content", None) or "").strip()
    if not text:
        raise ChatError("empty", "The assistant gave no answer. Please ask again.")
    result.answer = text
    return result
