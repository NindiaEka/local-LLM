from typing import Literal

from pydantic import BaseModel


class ContentPart(BaseModel):
    type: Literal["text"] | str
    text: str | None = None


class Message(BaseModel):
    role: str
    content: str | list[ContentPart]


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[Message]
    stream: bool = False


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Literal["stop", "length", "tool_calls", "content_filter"]


class ChatCompletionResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: list[Choice]
    usage: Usage
    system_fingerprint: str | None = None
