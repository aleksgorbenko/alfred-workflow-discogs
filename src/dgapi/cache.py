import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


PRIVATE_UMASK = 0o077
PRIVATE_DIRECTORY = 0o700


def cache_dir() -> Path:
    os.umask(PRIVATE_UMASK)
    base = os.environ.get("alfred_workflow_cache")  # noqa: SIM112
    path = Path(base) if base else Path(tempfile.gettempdir()) / "alfred-discogs"
    path.mkdir(mode=PRIVATE_DIRECTORY, parents=True, exist_ok=True)
    path.chmod(PRIVATE_DIRECTORY)
    return path


def _cache_path(key: str) -> Path:
    digest = hashlib.sha256(key.encode()).hexdigest()
    return cache_dir() / f"{digest}.json"


def cached[T](key: str, ttl_seconds: int, fetch: Callable[[], T]) -> T:
    path = _cache_path(key)
    if path.exists() and (time.time() - path.stat().st_mtime) < ttl_seconds:
        return json.loads(path.read_text())

    value = fetch()
    path.write_text(json.dumps(value))
    return value
