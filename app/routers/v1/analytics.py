from fastapi import APIRouter, Depends

from app.dependencies.auth import verify_api_key
from app.schemas.analytics import AnalyticsSummaryResponse
from app.services import analytics_service

router = APIRouter(prefix="/v1", tags=["OpenAI Compatible"])


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummaryResponse,
    dependencies=[Depends(verify_api_key)],
)
async def get_analytics_summary() -> AnalyticsSummaryResponse:
    return await analytics_service.get_summary()
