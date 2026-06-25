import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException

from app.database import get_connection
from app.schemas.key import CreateKeyResponse, KeyInfoResponse


def _hash_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()


def create_key(name: str) -> CreateKeyResponse:
    plain_key = "sk_local_" + secrets.token_urlsafe(32)
    key_hash = _hash_key(plain_key)
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO api_keys (name, key_hash, is_active, created_at)
            VALUES (?, ?, 1, ?)
            """,
            (name, key_hash, created_at),
        )
        connection.commit()
        key_id = cursor.lastrowid

    return CreateKeyResponse(id=key_id, name=name, key=plain_key)


def list_keys() -> list[KeyInfoResponse]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, is_active, created_at
            FROM api_keys
            ORDER BY id ASC
            """
        ).fetchall()

    return [
        KeyInfoResponse(
            id=row["id"],
            name=row["name"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def revoke_key(key_id: int) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE api_keys
            SET is_active = 0
            WHERE id = ?
            """,
            (key_id,),
        )
        connection.commit()

    return cursor.rowcount > 0


def validate_key(plain_key: str) -> None:
    key_hash = _hash_key(plain_key)

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT is_active FROM api_keys
            WHERE key_hash = ?
            """,
            (key_hash,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if not row["is_active"]:
        raise HTTPException(status_code=403, detail="API key has been revoked")
