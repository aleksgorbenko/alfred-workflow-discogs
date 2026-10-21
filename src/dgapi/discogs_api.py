import http
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from cache import cached
from sqlite_cache import cached_sqlite

API_BASE = "https://api.discogs.com"
USER_AGENT = "AlfredDiscogsWorkflow/1.0 +https://github.com/aleksgorbenko/alfred-workflow-discogs"

ONE_HOUR = 3600
ONE_MONTH = 2592000


class DiscogsError(Exception):
    pass


class DiscogsAuthError(DiscogsError):
    pass


def _get(url: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(  # noqa: S310
        url,
        headers={
            "Authorization": f"Discogs token={token}",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == http.HTTPStatus.UNAUTHORIZED:
            msg = "Invalid or missing Discogs API token"
            raise DiscogsAuthError(msg) from error
        msg = f"Discogs API returned HTTP {error.code} for {url}"
        raise DiscogsError(msg) from error
    except urllib.error.URLError as error:
        msg = f"Could not reach Discogs API ({url}): {error.reason}"
        raise DiscogsError(msg) from error


def search(query: str, token: str, per_page: int = 20) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"q": query, "per_page": per_page})
    url = f"{API_BASE}/database/search?{params}"
    return cached(url, ONE_HOUR, lambda: _get(url, token))["results"]


def _fetch_paginated(
    path: str, token: str, list_key: str, params: dict[str, str]
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path}" + (f"?{query}" if query else "")
    while url:
        body = _get(url, token)
        entries.extend(body[list_key])
        url = body["pagination"]["urls"].get("next")
    return entries


def _get_list(
    path: str, token: str, list_key: str, ttl_seconds: int, **params: str
) -> list[dict[str, Any]]:
    query = urllib.parse.urlencode(params)
    cache_key = f"{API_BASE}/{path}" + (f"?{query}" if query else "")

    def fetch() -> list[dict[str, Any]]:
        return _fetch_paginated(path, token, list_key, params)

    return cached(cache_key, ttl_seconds, fetch)


def get_label_releases(label_id: str, token: str) -> list[dict[str, Any]]:
    return _get_list(
        f"labels/{label_id}/releases", token, "releases", ONE_MONTH, per_page="100"
    )


def get_artist_releases(artist_id: str, token: str) -> list[dict[str, Any]]:
    return _get_list(
        f"artists/{artist_id}/releases", token, "releases", ONE_MONTH, per_page="100"
    )


def get_master_versions(master_id: str, token: str) -> list[dict[str, Any]]:
    return _get_list(
        f"masters/{master_id}/versions", token, "versions", ONE_MONTH, per_page="100"
    )


def get_release(release_id: str, token: str) -> dict[str, Any]:
    url = f"{API_BASE}/releases/{release_id}"
    return cached_sqlite(url, ONE_MONTH, lambda: _get(url, token))


def get_artist(artist_id: str, token: str) -> dict[str, Any]:
    url = f"{API_BASE}/artists/{artist_id}"
    return cached_sqlite(url, ONE_MONTH, lambda: _get(url, token))


def get_label(label_id: str, token: str) -> dict[str, Any]:
    url = f"{API_BASE}/labels/{label_id}"
    return cached_sqlite(url, ONE_MONTH, lambda: _get(url, token))
