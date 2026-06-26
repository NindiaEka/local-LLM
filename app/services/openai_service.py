import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from app.schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
)
from app.services.ollama_service import (
    OllamaStreamConnectionError,
    OllamaStreamProtocolError,
    OllamaStreamTimeoutError,
    OllamaStreamUpstreamError,
    ask_ollama_raw,
    ask_ollama_stream,
)


class OpenAIStreamError(RuntimeError):
    pass


class OpenAIStreamConnectionError(OpenAIStreamError):
    pass


class OpenAIStreamTimeoutError(OpenAIStreamError):
    pass


class OpenAIStreamUpstreamError(OpenAIStreamError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Ollama returned an error: {status_code}")


class OpenAIStreamProtocolError(OpenAIStreamError):
    pass


@dataclass(frozen=True)
class _StreamRequestContext:
    request_id: str
    created: int
    model: str


async def complete(request: ChatCompletionRequest) -> ChatCompletionResponse:
    messages = [
        {"role": m.role, "content": m.content}
        for m in request.messages
    ]

    data = await ask_ollama_raw(model=request.model, messages=messages)

    raw_message = data.get("message")
    if not isinstance(raw_message, dict):
        raise HTTPException(
            status_code=502,
            detail="Unexpected response structure from Ollama",
        )

    reply_message = Message(
        role=raw_message.get("role", "assistant"),
        content=raw_message.get("content", ""),
    )

    choice = Choice(
        index=0,
        message=reply_message,
        finish_reason="stop",
    )

    usage = Usage(
        prompt_tokens=data.get("prompt_eval_count", 0),
        completion_tokens=data.get("eval_count", 0),
        total_tokens=data.get("prompt_eval_count", 0) + data.get("eval_count", 0),
    )

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        object="chat.completion",
        created=int(time.time()),
        model=data.get("model", request.model),
        choices=[choice],
        usage=usage,
    )


def _to_finish_reason(done: bool, done_reason: object) -> str | None:
    if not done:
        return None

    if isinstance(done_reason, str) and done_reason in {"stop", "length", "tool_calls", "content_filter"}:
        return done_reason

    return "stop"


def _to_openai_stream_chunk(
    context: _StreamRequestContext,
    internal_chunk: dict[str, Any],
) -> dict[str, Any]:
    done = bool(internal_chunk.get("done", False))

    delta: dict[str, str] = {}
    role = internal_chunk.get("role")
    if isinstance(role, str):
        delta["role"] = role

    content = internal_chunk.get("content")
    if isinstance(content, str) and content:
        delta["content"] = content

    return {
        "id": context.request_id,
        "object": "chat.completion.chunk",
        "created": context.created,
        "model": context.model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": _to_finish_reason(done, internal_chunk.get("done_reason")),
            }
        ],
    }


async def stream_complete(request: ChatCompletionRequest) -> AsyncIterator[dict[str, Any]]:
    messages = [
        {"role": m.role, "content": m.content}
        for m in request.messages
    ]

    context = _StreamRequestContext(
        request_id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=request.model,
    )

    saw_done = False

    try:
        async for internal_chunk in ask_ollama_stream(model=request.model, messages=messages):
            yield _to_openai_stream_chunk(context, internal_chunk)

            if internal_chunk.get("done") is True:
                saw_done = True
                break

    except OllamaStreamConnectionError:
        raise OpenAIStreamConnectionError("Ollama is not reachable")
    except OllamaStreamTimeoutError:
        raise OpenAIStreamTimeoutError("Ollama streaming request timed out")
    except OllamaStreamUpstreamError as exc:
        raise OpenAIStreamUpstreamError(exc.status_code)
    except OllamaStreamProtocolError as exc:
        raise OpenAIStreamProtocolError(str(exc))

    if not saw_done:
        raise OpenAIStreamProtocolError("Ollama stream ended before terminal chunk")
