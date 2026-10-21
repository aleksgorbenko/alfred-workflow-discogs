import json
import sqlite3
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Generator
    from pathlib import Path

from cache import cache_dir

DB_FILENAME = "discogs_details.sqlite3"


def _db_path() -> Path:
    return cache_dir() / DB_FILENAME


@contextmanager
def _connect() -> Generator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path(), timeout=10)
    try:
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL, cached_at REAL NOT NULL)"
            )
            yield conn
    finally:
        conn.close()


def cached_sqlite[T](key: str, ttl_seconds: int, fetch: Callable[[], T]) -> T:
    with _connect() as conn:
        row = conn.execute(
            "SELECT value, cached_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row and (time.time() - row[1]) < ttl_seconds:
            return json.loads(row[0])

    value = fetch()

    with _connect() as conn:
        conn.execute(
            "INSERT INTO cache (key, value, cached_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET "
            "value = excluded.value, cached_at = excluded.cached_at",
            (key, json.dumps(value), time.time()),
        )
    return value
