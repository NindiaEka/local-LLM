import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings

_TIMEOUT = 120.0


class OllamaError(RuntimeError):
    pass


class OllamaConnectionError(OllamaError):
    pass


class OllamaTimeoutError(OllamaError):
    pass


class OllamaUpstreamError(OllamaError):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"Ollama returned an error: {status_code}")


class OllamaResponseError(OllamaError):
    pass


class OllamaStreamError(OllamaError):
    pass


class OllamaStreamConnectionError(OllamaConnectionError, OllamaStreamError):
    pass


class OllamaStreamTimeoutError(OllamaTimeoutError, OllamaStreamError):
    pass


class OllamaStreamProtocolError(OllamaStreamError):
    pass


class OllamaStreamUpstreamError(OllamaUpstreamError, OllamaStreamError):
    pass


async def _post_ollama(payload: dict) -> dict:
    url = f"{settings.ollama_base_url}/api/chat"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=_TIMEOUT)
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError as exc:
        raise OllamaConnectionError("Ollama is not reachable") from exc
    except httpx.TimeoutException as exc:
        raise OllamaTimeoutError("Ollama did not respond in time") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaUpstreamError(exc.response.status_code) from exc


async def ask_ollama(model: str, message: str) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": message}],
        "stream": False,
    }
    try:
        data = await _post_ollama(payload)
        return data["message"]["content"]
    except KeyError:
        raise OllamaResponseError("Unexpected response structure from Ollama")


async def ask_ollama_raw(model: str, messages: list[dict]) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    return await _post_ollama(payload)


def _validate_optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int):
        raise OllamaStreamProtocolError(f"Invalid '{field_name}' in stream chunk")
    return value


def _normalize_ollama_stream_chunk(raw_chunk: object) -> dict:
    if not isinstance(raw_chunk, dict):
        raise OllamaStreamProtocolError("Invalid stream chunk: expected JSON object")

    done = raw_chunk.get("done")
    if not isinstance(done, bool):
        raise OllamaStreamProtocolError("Invalid stream chunk: missing boolean 'done'")

    model = raw_chunk.get("model")
    if model is not None and not isinstance(model, str):
        raise OllamaStreamProtocolError("Invalid stream chunk: 'model' must be a string when present")

    role: str | None = None
    content = ""
    message = raw_chunk.get("message")
    if message is None:
        if not done:
            raise OllamaStreamProtocolError("Invalid stream chunk: non-terminal chunk missing 'message'")
    elif isinstance(message, dict):
        raw_role = message.get("role")
        if raw_role is not None and not isinstance(raw_role, str):
            raise OllamaStreamProtocolError("Invalid stream chunk: message.role must be a string when present")

        raw_content = message.get("content", "")
        if not isinstance(raw_content, str):
            raise OllamaStreamProtocolError("Invalid stream chunk: message.content must be a string")

        role = raw_role
        content = raw_content
    else:
        raise OllamaStreamProtocolError("Invalid stream chunk: message must be an object when present")

    return {
        "model": model,
        "role": role,
        "content": content,
        "done": done,
        "done_reason": _validate_optional_done_reason(raw_chunk.get("done_reason")),
        "prompt_eval_count": _validate_optional_int(raw_chunk.get("prompt_eval_count"), "prompt_eval_count"),
        "eval_count": _validate_optional_int(raw_chunk.get("eval_count"), "eval_count"),
    }


def _validate_optional_done_reason(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise OllamaStreamProtocolError("Invalid 'done_reason' in stream chunk")
    return value


async def ask_ollama_stream(model: str, messages: list[dict]) -> AsyncIterator[dict]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    url = f"{settings.ollama_base_url}/api/chat"

    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, timeout=_TIMEOUT) as response:
                response.raise_for_status()

                saw_any_chunk = False
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    saw_any_chunk = True
                    try:
                        raw_chunk = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise OllamaStreamProtocolError("Received malformed JSON from Ollama stream") from exc

                    yield _normalize_ollama_stream_chunk(raw_chunk)

                if not saw_any_chunk:
                    raise OllamaStreamProtocolError("Ollama stream ended without emitting any chunks")

    except httpx.ConnectError as exc:
        raise OllamaStreamConnectionError("Ollama is not reachable") from exc
    except httpx.TimeoutException as exc:
        raise OllamaStreamTimeoutError("Ollama streaming request timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaStreamUpstreamError(exc.response.status_code) from exc
    except (httpx.ReadError, httpx.RemoteProtocolError) as exc:
        raise OllamaStreamProtocolError("Ollama stream was interrupted") from exc
