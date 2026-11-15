"""Glossary of the farmer advisor: plain-language terms and sentence templates, kept as data in glossary.json.

The same file feeds the web app (tooltips) and the explain functions, so the wording lives in one place.
Every term has ``reviewed: false`` until the agronomic review of the plan (Review TODO) is done.
"""

from __future__ import annotations

import json
from difflib import get_close_matches
from functools import cache
from pathlib import Path
from typing import Any

GLOSSARY_FILE = Path(__file__).with_name("glossary.json")


class UnknownTermError(ValueError):
    """The term is neither a glossary key nor an alias."""

    def __init__(self, term: str, close_matches: list[str]):
        self.term = term
        self.close_matches = close_matches
        hint = f" Close matches: {', '.join(close_matches)}." if close_matches else " Use list_terms() to see all terms."
        super().__init__(f"Unknown term '{term}'.{hint}")


@cache
def _load() -> dict[str, Any]:
    return json.loads(GLOSSARY_FILE.read_text(encoding="utf-8"))


def terms() -> dict[str, dict[str, Any]]:
    """All glossary entries by key. Do not modify the returned dicts."""
    return _load()["terms"]


def templates() -> dict[str, Any]:
    """Sentence templates for explain_score, trade-offs and caveats. Do not modify."""
    return _load()["templates"]


def normalize(term: str) -> str:
    """'Cold stress' -> 'cold_stress', so lookups ignore case, spaces and hyphens."""
    return str(term).strip().lower().replace(" ", "_").replace("-", "_")


@cache
def _index() -> dict[str, str]:
    """Normalised key / alias / title -> glossary key. A name used twice is a bug in glossary.json."""
    index: dict[str, str] = {}
    for key, entry in terms().items():
        for name in [key, entry["term"], *entry["aliases"]]:
            n = normalize(name)
            if index.setdefault(n, key) != key:
                raise ValueError(f"glossary name '{n}' is used by '{index[n]}' and '{key}'")
    return index


def explain_term(term: str) -> dict[str, Any]:
    """The glossary entry of a term. Accepts the key, an alias (also a data field name such as
    ``cold_stress_years_pct``) or the title, in any case.
    """
    index = _index()
    key = index.get(normalize(term))
    if key is None:
        raise UnknownTermError(term, get_close_matches(normalize(term), list(index), n=5, cutoff=0.6))
    return {"key": key} | terms()[key]


def list_terms() -> list[dict[str, Any]]:
    """Key, title and one-line explanation of every term, in glossary order."""
    return [
        {"key": key, "term": e["term"], "short": e["short"], "reviewed": e["reviewed"]}
        for key, e in terms().items()
    ]
