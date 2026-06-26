import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.dependencies.auth import verify_api_key
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services import openai_service
from app.services.openai_service import (
    OpenAIStreamConnectionError,
    OpenAIStreamProtocolError,
    OpenAIStreamTimeoutError,
    OpenAIStreamUpstreamError,
)

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


def _sse_frame(payload: str) -> str:
    return f"data: {payload}\n\n"


async def _stream_chat_completions(body: ChatCompletionRequest) -> AsyncIterator[str]:
    try:
        async for chunk in openai_service.stream_complete(body):
            yield _sse_frame(json.dumps(chunk))
    except OpenAIStreamConnectionError as exc:
        raise HTTPException(status_code=503, detail="Ollama is not reachable") from exc
    except OpenAIStreamTimeoutError as exc:
        raise HTTPException(status_code=504, detail="Ollama streaming request timed out") from exc
    except OpenAIStreamUpstreamError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama returned an error: {exc.status_code}") from exc
    except OpenAIStreamProtocolError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    yield _sse_frame("[DONE]")


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    dependencies=[Depends(verify_api_key)],
)
async def chat_completions(body: ChatCompletionRequest) -> ChatCompletionResponse:
    if body.stream is False:
        return await openai_service.complete(body)

    return StreamingResponse(
        _stream_chat_completions(body),
        media_type="text/event-stream",
    )
