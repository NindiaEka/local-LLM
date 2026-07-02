from datetime import datetime

from pydantic import BaseModel


class OverviewSummary(BaseModel):
    total_requests: int
    success_requests: int
    error_requests: int
    success_rate: float


class LatencySummary(BaseModel):
    average_ms: float
    minimum_ms: float
    maximum_ms: float


class CountByKey(BaseModel):
    key: str
    count: int


class CountByStatusCode(BaseModel):
    status_code: int
    count: int


class ApiKeyUsage(BaseModel):
    api_key_id: str
    count: int


class UsageBreakdown(BaseModel):
    by_endpoint: list[CountByKey]
    by_model: list[CountByKey]
    by_status_code: list[CountByStatusCode]
    top_api_keys: list[ApiKeyUsage]


class AnalyticsSummaryResponse(BaseModel):
    generated_at: datetime
    overview: OverviewSummary
    latency: LatencySummary
    usage_breakdown: UsageBreakdown
