from fastapi import APIRouter, Depends

from app.dependencies.auth import verify_api_key
from app.schemas.openai import ChatCompletionRequest, ChatCompletionResponse
from app.services import openai_service

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    dependencies=[Depends(verify_api_key)],
)
async def chat_completions(body: ChatCompletionRequest) -> ChatCompletionResponse:
    return await openai_service.complete(body)
