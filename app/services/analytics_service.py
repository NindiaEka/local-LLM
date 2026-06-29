from datetime import datetime, timezone

from app.database import get_connection
from app.schemas.analytics import (
    AnalyticsSummaryResponse,
    ApiKeyUsage,
    CountByKey,
    CountByStatusCode,
    LatencySummary,
    OverviewSummary,
    UsageBreakdown,
)


def _fetch_scalar(query: str, params: tuple = ()) -> float:
    with get_connection() as connection:
        row = connection.execute(query, params).fetchone()
    if row is None:
        return 0.0

    value = row[0]
    if value is None:
        return 0.0
    return float(value)


def _fetch_count_by_key(query: str, params: tuple = ()) -> list[CountByKey]:
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        CountByKey(key=str(row["key"]), count=int(row["count"]))
        for row in rows
    ]


def _fetch_count_by_status_code(query: str, params: tuple = ()) -> list[CountByStatusCode]:
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        CountByStatusCode(status_code=int(row["status_code"]), count=int(row["count"]))
        for row in rows
    ]


def _fetch_api_key_usage(query: str, params: tuple = ()) -> list[ApiKeyUsage]:
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        ApiKeyUsage(api_key_id=str(row["api_key_id"]), count=int(row["count"]))
        for row in rows
    ]


async def get_summary() -> AnalyticsSummaryResponse:
    total_requests = int(_fetch_scalar("SELECT COUNT(*) FROM request_logs"))
    success_requests = int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM request_logs
            WHERE status_code >= ? AND status_code < ?
            """,
            (200, 400),
        )
    )
    error_requests = int(
        _fetch_scalar(
            """
            SELECT COUNT(*)
            FROM request_logs
            WHERE status_code >= ?
            """,
            (400,),
        )
    )

    success_rate = 0.0
    if total_requests > 0:
        success_rate = success_requests / total_requests

    with get_connection() as connection:
        latency_row = connection.execute(
            """
            SELECT
                AVG(latency_ms) AS average_ms,
                MIN(latency_ms) AS minimum_ms,
                MAX(latency_ms) AS maximum_ms
            FROM request_logs
            """
        ).fetchone()

    average_ms = 0.0
    minimum_ms = 0.0
    maximum_ms = 0.0
    if latency_row is not None:
        average_ms = float(latency_row["average_ms"] or 0.0)
        minimum_ms = float(latency_row["minimum_ms"] or 0.0)
        maximum_ms = float(latency_row["maximum_ms"] or 0.0)

    by_endpoint = _fetch_count_by_key(
        """
        SELECT endpoint AS key, COUNT(*) AS count
        FROM request_logs
        GROUP BY endpoint
        ORDER BY count DESC, key ASC
        """
    )

    by_model = _fetch_count_by_key(
        """
        SELECT COALESCE(model, ?) AS key, COUNT(*) AS count
        FROM request_logs
        GROUP BY COALESCE(model, ?)
        ORDER BY count DESC, key ASC
        """,
        ("unknown", "unknown"),
    )

    by_status_code = _fetch_count_by_status_code(
        """
        SELECT status_code, COUNT(*) AS count
        FROM request_logs
        GROUP BY status_code
        ORDER BY status_code ASC
        """
    )

    top_api_keys = _fetch_api_key_usage(
        """
        SELECT COALESCE(api_key_id, ?) AS api_key_id, COUNT(*) AS count
        FROM request_logs
        GROUP BY COALESCE(api_key_id, ?)
        ORDER BY count DESC, api_key_id ASC
        LIMIT ?
        """,
        ("unknown", "unknown", 10),
    )

    return AnalyticsSummaryResponse(
        generated_at=datetime.now(timezone.utc),
        overview=OverviewSummary(
            total_requests=total_requests,
            success_requests=success_requests,
            error_requests=error_requests,
            success_rate=success_rate,
        ),
        latency=LatencySummary(
            average_ms=average_ms,
            minimum_ms=minimum_ms,
            maximum_ms=maximum_ms,
        ),
        usage_breakdown=UsageBreakdown(
            by_endpoint=by_endpoint,
            by_model=by_model,
            by_status_code=by_status_code,
            top_api_keys=top_api_keys,
        ),
    )
