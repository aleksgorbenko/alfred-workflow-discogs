import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path


def _cache_dir() -> Path:
    base = os.environ.get("alfred_workflow_cache", tempfile.gettempdir())  # noqa: SIM112
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode()).hexdigest()
    return _cache_dir() / f"{digest}.json"


def cached[T](key: str, ttl_seconds: int, fetch: Callable[[], T]) -> T:
    path = _cache_path(key)
    if path.exists() and (time.time() - path.stat().st_mtime) < ttl_seconds:
        return json.loads(path.read_text())

    value = fetch()
    path.write_text(json.dumps(value))
    return value
