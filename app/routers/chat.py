from fastapi import APIRouter, Depends

from app.dependencies.auth import verify_api_key
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ollama_service import ask_ollama

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(body: ChatRequest):
    reply = await ask_ollama(model=body.model, message=body.message)
    return ChatResponse(response=reply)
