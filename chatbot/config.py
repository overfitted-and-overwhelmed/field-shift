"""Settings of the chatbot, read from the environment (and from .env in the repo root, like the NASS fetch script).

The key is read on the server only. It is never put into code, responses or logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
DEFAULT_MODEL = "gemini-3-flash-preview"  # the "-latest" alias hung without an answer in the spike


class MissingApiKeyError(RuntimeError):
    """LLM_API_KEY is not set (neither in the environment nor in .env)."""


def _env_file_value(name: str, env_file: Path) -> str:
    if not env_file.is_file():
        return ""
    for line in env_file.read_text().splitlines():
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip().strip("'\"")
    return ""


def _get(name: str, default: str = "", env_file: Path = REPO_ROOT / ".env") -> str:
    return os.environ.get(name) or _env_file_value(name, env_file) or default


def api_key(env_file: Path = REPO_ROOT / ".env") -> str:
    """The Gemini key. On Vercel it is an environment variable, locally a line in .env."""
    key = _get("LLM_API_KEY", env_file=env_file)
    if not key or key.startswith("$"):  # an unexpanded '$LLM_API_KEY' placeholder is not a key
        raise MissingApiKeyError("LLM_API_KEY is missing: set it as an environment variable or in .env")
    return key


@dataclass(frozen=True)
class Settings:
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    temperature: float = 0.3  # low: the answers should stay close to the tool results
    max_tokens: int = 700
    request_timeout_s: float = 40.0
    max_tool_rounds: int = 5
    max_tool_calls_per_round: int = 4


def load_settings(env_file: Path = REPO_ROOT / ".env") -> Settings:
    """Defaults, with LLM_BASE_URL, CHAT_MODEL, CHAT_MAX_TOKENS and CHAT_TIMEOUT_S as optional overrides."""
    base = Settings()
    return Settings(
        base_url=_get("LLM_BASE_URL", base.base_url, env_file),
        model=_get("CHAT_MODEL", base.model, env_file),
        max_tokens=int(_get("CHAT_MAX_TOKENS", str(base.max_tokens), env_file)),
        request_timeout_s=float(_get("CHAT_TIMEOUT_S", str(base.request_timeout_s), env_file)),
    )


def make_client(settings: Settings | None = None):
    """The OpenAI-compatible client for the Gemini endpoint. Imported here so tests need no network or key."""
    from openai import OpenAI

    settings = settings or load_settings()
    return OpenAI(base_url=settings.base_url, api_key=api_key(), timeout=settings.request_timeout_s, max_retries=1)
