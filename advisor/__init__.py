"""Farmer advisor: file-based lookups and plain-language explanations over explorer.json and the scorer's
rotation_scores.csv.

No API, no LLM. Functions return plain dicts / lists (JSON-serializable).
"""

from advisor.data import DetailNotAvailableError, UnknownRotationError
from advisor.explain import explain_score, get_data_caveats, trade_offs
from advisor.glossary import UnknownTermError, explain_term, list_terms
from advisor.lookup import (
    compare_rotations,
    field_overview,
    get_rotation,
    list_top_rotations,
    monthly_table,
)
from advisor.rerank import rerank

__all__ = [
    "DetailNotAvailableError",
    "UnknownRotationError",
    "UnknownTermError",
    "compare_rotations",
    "explain_score",
    "explain_term",
    "field_overview",
    "get_data_caveats",
    "get_rotation",
    "list_terms",
    "list_top_rotations",
    "monthly_table",
    "rerank",
    "trade_offs",
]
