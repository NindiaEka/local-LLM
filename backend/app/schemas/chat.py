from pydantic import BaseModel


class ChatRequest(BaseModel):
    model: str
    message: str


class ChatResponse(BaseModel):
    response: str
