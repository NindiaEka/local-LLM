from fastapi import APIRouter, Depends

from app.dependencies.auth import verify_api_key
from app.schemas.model import ModelsResponse
from app.services import openai_service

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.get(
    "/models",
    response_model=ModelsResponse,
    dependencies=[Depends(verify_api_key)],
)
async def list_models() -> ModelsResponse:
    return await openai_service.list_models()
