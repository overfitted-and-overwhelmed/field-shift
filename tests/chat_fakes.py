"""Helpers for the chatbot tests: a fake model client that follows a script, so no network and no key are needed."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


def text(content: str) -> SimpleNamespace:
    """A model message with a plain text answer."""
    return SimpleNamespace(content=content, tool_calls=None)


def calls(*specs: tuple[str, dict | str], extra: dict | None = None) -> SimpleNamespace:
    """A model message that asks for tools: ``calls(("explain_term", {"term": "p10"}), ...)``.

    ``extra`` is put on every call like the pydantic ``model_extra`` of the real client (Gemini: ``extra_content``).
    """
    tool_calls = [
        SimpleNamespace(
            id=f"call_{i}",
            function=SimpleNamespace(name=name, arguments=args if isinstance(args, str) else json.dumps(args)),
            model_extra=extra,
        )
        for i, (name, args) in enumerate(specs)
    ]
    return SimpleNamespace(content=None, tool_calls=tool_calls)


@dataclass
class FakeClient:
    """Answers with the scripted messages in order (an exception in the script is raised). Records every request."""

    script: list[Any]
    requests: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(json.loads(json.dumps(kwargs, default=str)))  # a copy: the agent keeps changing its list
        if not self.script:
            raise AssertionError("the model was called more often than the script has answers")
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return SimpleNamespace(choices=[SimpleNamespace(message=step)])

    def tool_results(self) -> list[str]:
        """Every tool result the model has seen in its last request."""
        return [m["content"] for m in self.requests[-1]["messages"] if m["role"] == "tool"]
