from datetime import datetime

from app.database import get_connection


async def save_request_log(
    timestamp: datetime,
    request_id: str | None,
    api_key_id: str | None,
    endpoint: str,
    method: str,
    model: str | None,
    status_code: int,
    latency_ms: float,
    client_ip: str | None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO request_logs (
                timestamp,
                request_id,
                api_key_id,
                endpoint,
                method,
                model,
                status_code,
                latency_ms,
                client_ip
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp.isoformat(),
                request_id,
                api_key_id,
                endpoint,
                method,
                model,
                status_code,
                latency_ms,
                client_ip,
            ),
        )
        connection.commit()
