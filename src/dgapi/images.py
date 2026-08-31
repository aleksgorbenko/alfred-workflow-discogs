import functools
import hashlib
import os
import tempfile
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from discogs_api import USER_AGENT

TIMEOUT_SECONDS = 5
MAX_WORKERS = 8


def _cache_dir() -> Path:
    base = os.environ.get("alfred_workflow_cache", tempfile.gettempdir())  # noqa: SIM112
    path = Path(base) / "covers"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode()).hexdigest()
    return _cache_dir() / f"{digest}.jpg"


def _fetch_one(url: str, timeout_seconds: int) -> str | None:
    path = _cache_path(url)
    if path.exists():
        return str(path)

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            path.write_bytes(response.read())
    except urllib.error.URLError, TimeoutError:
        return None
    return str(path)


def warm(
    urls: list[str | None],
    max_workers: int = MAX_WORKERS,
    timeout_seconds: int = TIMEOUT_SECONDS,
) -> dict[str, str]:
    unique_urls = {url for url in urls if url}
    if not unique_urls:
        return {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        fetch = functools.partial(_fetch_one, timeout_seconds=timeout_seconds)
        paths = executor.map(fetch, unique_urls)
        return {
            url: path
            for url, path in zip(unique_urls, paths, strict=True)
            if path is not None
        }
