"""Checks for chatbot answers: are the numbers in an answer backed by the tool results of the same turn?

A heuristic for tests, not a proof. It catches an invented number, it cannot judge wording.
"""

from __future__ import annotations

import json
import re

NUMBER = re.compile(r"(?<![\w.])-?\d+(?:[.,]\d+)?")
SMALL_INT_MAX = 10  # 'place 1', 'three crops', 'top 3' are counting words, not data


def numbers(text: str) -> list[float]:
    """The numbers in a text. A decimal comma (German) counts as a point."""
    return [float(m.replace(",", ".")) for m in NUMBER.findall(text)]


def _grounded(value: float, sources: list[float]) -> bool:
    """The model may round (0.4999 -> 0.5) or turn a share into percent (0.75 -> 75)."""
    for s in sources:
        for candidate in (s, s * 100):
            if abs(value - candidate) <= max(0.01 * abs(candidate), 0.006):
                return True
    return False


def ungrounded_numbers(answer: str, tool_results: list[str], context: str = "") -> list[float]:
    """Numbers of the answer that appear in no tool result (nor in ``context``, e.g. the question's own numbers)."""
    sources: list[float] = []
    for result in tool_results:
        sources += numbers(json.dumps(json.loads(result), ensure_ascii=False))
    sources += numbers(context)
    return [
        v for v in numbers(answer)
        if not (float(v).is_integer() and abs(v) <= SMALL_INT_MAX) and not _grounded(v, sources)
    ]


def states_null_as_zero(answer: str, subject: str) -> bool:
    """True if the answer says that a value is zero where the data has none, e.g. 'nitrogen: 0 lb'.

    ``subject`` is a word like 'nitrogen'. Looks for the subject within 40 characters before a zero amount.
    """
    pattern = rf"{re.escape(subject)}[^.\n]{{0,40}}\b0(?:[.,]0+)?\s*(?:lb|lbs|pounds)\b"
    return re.search(pattern, answer, flags=re.IGNORECASE) is not None
