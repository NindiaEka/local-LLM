import time
import uuid

from fastapi import HTTPException

from app.schemas.openai import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
)
from app.services.ollama_service import ask_ollama_raw


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
