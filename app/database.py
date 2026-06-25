import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "keys.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                key_hash   TEXT    NOT NULL UNIQUE,
                is_active  INTEGER NOT NULL DEFAULT 1,
                created_at TEXT    NOT NULL
            )
        """)
        connection.commit()
