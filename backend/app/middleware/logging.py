from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import Message

from app.services.logging_service import save_request_log


async def _extract_model(request: Request) -> str | None:
    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return None

    body_bytes = await request.body()
    if not body_bytes:
        return None

    sent = False

    async def _receive() -> Message:
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    request._receive = _receive  # type: ignore[attr-defined]

    try:
        payload: Any = json.loads(body_bytes)
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        raw_model = payload.get("model")
        if isinstance(raw_model, str):
            return raw_model
    return None


async def _safe_save_log(**kwargs: Any) -> None:
    try:
        await save_request_log(**kwargs)
    except Exception:
        # Logging failures must not impact request handling.
        return


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        timestamp = datetime.now(timezone.utc)
        request_id = f"req_{uuid.uuid4().hex}"
        request.state.request_id = request_id

        model = await _extract_model(request)

        endpoint = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else None

        start = time.perf_counter()
        try:
            response = await call_next(request)
            api_key_id = getattr(request.state, "api_key_id", None)
            latency_ms = (time.perf_counter() - start) * 1000
            await _safe_save_log(
                timestamp=timestamp,
                request_id=request_id,
                api_key_id=api_key_id,
                endpoint=endpoint,
                method=method,
                model=model,
                status_code=response.status_code,
                latency_ms=latency_ms,
                client_ip=client_ip,
            )
            return response
        except Exception:
            api_key_id = getattr(request.state, "api_key_id", None)
            latency_ms = (time.perf_counter() - start) * 1000
            await _safe_save_log(
                timestamp=timestamp,
                request_id=request_id,
                api_key_id=api_key_id,
                endpoint=endpoint,
                method=method,
                model=model,
                status_code=500,
                latency_ms=latency_ms,
                client_ip=client_ip,
            )
            raise
