from datetime import datetime

from pydantic import BaseModel


class RequestLogEntry(BaseModel):
    id: int
    timestamp: datetime
    api_key_id: str | None
    endpoint: str
    method: str
    model: str | None
    status_code: int
    latency_ms: float
    client_ip: str | None
