"""HTTP API of the chatbot (FastAPI): ``POST /chat`` and ``GET /health``.

    uv run uvicorn chatbot.api:app

The web app keeps the conversation and sends it with every request. The LLM key stays on the server.

Environment (all optional except the key, which is read by ``chatbot.config``):
    CHAT_ALLOWED_ORIGINS  comma separated origins of the web app for CORS (default: none, so no cross-origin access)
    CHAT_RATE_PER_MIN     requests per client and minute (default 20)
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any, Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from advisor.rerank import validate_weights
from chatbot.agent import ChatError, answer
from chatbot.config import Settings

MAX_MESSAGES = 20
MAX_MESSAGE_CHARS = 2000
CRITERIA = ("water", "risk", "soil_health", "nitrogen")
STATUS = {"rate_limited": 429, "timeout": 504, "unavailable": 503, "empty": 502}


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChatMessage(_Strict):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=MAX_MESSAGE_CHARS)


class ChatContext(_Strict):
    """What the farmer sees on the page, so 'this rotation' or 'my settings' in a question has a meaning."""

    rotation_id: str | None = Field(default=None, max_length=120, pattern=r"^[a-z0-9_+\-]+$")
    weights: dict[str, float] | None = None

    @field_validator("weights")
    @classmethod
    def _valid_weights(cls, weights: dict[str, float] | None) -> dict[str, float] | None:
        if weights is not None:
            validate_weights(weights)  # unknown criteria, negative, all zero -> ValueError -> 422
        return weights


class ChatRequest(_Strict):
    messages: list[ChatMessage] = Field(min_length=1, max_length=MAX_MESSAGES)
    context: ChatContext | None = None

    @field_validator("messages")
    @classmethod
    def _last_is_user(cls, messages: list[ChatMessage]) -> list[ChatMessage]:
        if messages[-1].role != "user":
            raise ValueError("the last message must be from the user")
        return messages


class ToolCall(_Strict):
    name: str
    arguments: dict[str, Any]
    error: bool


class ChatResponse(_Strict):
    answer: str
    tool_calls: list[ToolCall]  # what the answer is based on, for a "based on" line in the UI
    caveats_shown: bool  # the model looked up the data caveats in this turn


class ErrorBody(_Strict):
    code: str
    message: str


class ErrorResponse(_Strict):
    error: ErrorBody


class RateLimiter:
    """Sliding window per client, in memory. On a serverless host each instance counts for itself, so it only
    slows down abuse, it is not an exact limit. Use a shared store if a hard limit is needed."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, client: str, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        hits = self._hits[client]
        while hits and now - hits[0] > 60:
            hits.popleft()
        if len(hits) >= self.per_minute:
            return False
        hits.append(now)
        if len(self._hits) > 10_000:  # forget idle clients
            for key in [k for k, v in self._hits.items() if not v or now - v[-1] > 60]:
                del self._hits[key]
        return True


def _client_id(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def create_app(client: Any = None, settings: Settings | None = None, rate_per_minute: int | None = None) -> FastAPI:
    """The app. ``client`` is the model client (None = the real Gemini client, created on the first request)."""
    app = FastAPI(title="Field Shift chatbot", docs_url=None, redoc_url=None, openapi_url=None)
    limiter = RateLimiter(rate_per_minute or int(os.environ.get("CHAT_RATE_PER_MIN", "20")))
    origins = [o.strip() for o in os.environ.get("CHAT_ALLOWED_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["POST", "GET"], allow_headers=["Content-Type"])

    def error(code: str, message: str, status: int) -> JSONResponse:
        return JSONResponse(ErrorResponse(error=ErrorBody(code=code, message=message)).model_dump(), status_code=status)

    @app.exception_handler(RequestValidationError)
    async def _invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        # pydantic's detail can echo the farmer's text, so only a short generic message goes back
        return error("invalid_request", "The request is not valid: check messages (the last one from the user) "
                     f"and context. Limits: {MAX_MESSAGES} messages, {MAX_MESSAGE_CHARS} characters each.", 422)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse, responses={422: {"model": ErrorResponse}})
    def chat(body: ChatRequest, request: Request):
        if not limiter.allow(_client_id(request)):
            return error("rate_limited", "Too many questions. Please wait a minute.", 429)
        try:
            result = answer(
                [m.model_dump() for m in body.messages],
                body.context.model_dump(exclude_none=True) if body.context else None,
                client=client,
                settings=settings,
            )
        except ChatError as failure:
            return error(failure.code, str(failure), STATUS.get(failure.code, 503))
        return ChatResponse(
            answer=result.answer,
            tool_calls=[ToolCall(**c) for c in result.tool_calls],
            caveats_shown=result.caveats_shown,
        )

    return app


app = create_app(settings=None)
