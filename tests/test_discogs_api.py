import urllib.error
from email.message import Message
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from discogs_api import (
    DiscogsAuthError,
    DiscogsError,
    get_artist,
    get_artist_releases,
    get_label,
    get_label_releases,
    get_master_versions,
    get_release,
    search,
)


@patch("discogs_api.urllib.request.urlopen")
def test_search_sends_auth_and_user_agent_headers(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {"results": []}
    with patch("discogs_api.json.load", return_value=payload):
        search("query", "secret-token")

    request = mock_urlopen.call_args[0][0]
    assert request.get_header("Authorization") == "Discogs token=secret-token"
    assert request.get_header("User-agent")


@patch("discogs_api.urllib.request.urlopen")
def test_search_raises_auth_error_on_401(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="", code=401, msg="Unauthorized", hdrs=Message(), fp=None
    )
    with pytest.raises(DiscogsAuthError):
        search("query", "bad-token")


@patch("discogs_api.urllib.request.urlopen")
def test_search_raises_discogs_error_on_other_http_error(
    mock_urlopen: MagicMock,
) -> None:
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="", code=500, msg="Server Error", hdrs=Message(), fp=None
    )
    with pytest.raises(DiscogsError, match="database/search"):
        search("query", "token")


@patch("discogs_api.urllib.request.urlopen")
def test_search_raises_discogs_error_on_url_error(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = urllib.error.URLError("no network")
    with pytest.raises(DiscogsError):
        search("query", "token")


@patch("discogs_api.urllib.request.urlopen")
def test_search_returns_results_list(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {
        "pagination": {"page": 1, "pages": 1},
        "results": [{"id": 1, "type": "release", "title": "Foo"}],
    }
    with patch("discogs_api.json.load", return_value=payload):
        result = search("foo", "token")
    mock_urlopen.assert_called_once()
    assert result == [{"id": 1, "type": "release", "title": "Foo"}]


@patch("discogs_api.urllib.request.urlopen")
def test_search_sends_query_and_per_page(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {"results": []}
    with patch("discogs_api.json.load", return_value=payload):
        search("aphex twin", "token", per_page=5)

    request = mock_urlopen.call_args[0][0]
    assert "q=aphex+twin" in request.full_url
    assert "per_page=5" in request.full_url


@patch("discogs_api.urllib.request.urlopen")
def test_get_label_releases_returns_list(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {
        "pagination": {"urls": {}},
        "releases": [{"id": 1, "title": "A Release", "artist": "Someone"}],
    }
    with patch("discogs_api.json.load", return_value=payload):
        result = get_label_releases("100", "token")
    assert result == [{"id": 1, "title": "A Release", "artist": "Someone"}]

    request = mock_urlopen.call_args[0][0]
    assert "/labels/100/releases" in request.full_url


@patch("discogs_api.urllib.request.urlopen")
def test_get_artist_releases_follows_pagination(mock_urlopen: MagicMock) -> None:
    page_one: dict[str, Any] = {
        "pagination": {"urls": {"next": "https://api.discogs.com/next-page"}},
        "releases": [{"id": 1, "type": "release", "title": "A"}],
    }
    page_two: dict[str, Any] = {
        "pagination": {"urls": {}},
        "releases": [{"id": 2, "type": "master", "title": "B"}],
    }
    with patch("discogs_api.json.load", side_effect=[page_one, page_two]):
        result = get_artist_releases("200", "token")
    assert result == [
        {"id": 1, "type": "release", "title": "A"},
        {"id": 2, "type": "master", "title": "B"},
    ]

    request = mock_urlopen.call_args_list[0][0][0]
    assert "/artists/200/releases" in request.full_url


@patch("discogs_api.urllib.request.urlopen")
def test_get_master_versions_returns_list(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {
        "pagination": {"urls": {}},
        "versions": [{"id": 5, "title": "A Pressing"}],
    }
    with patch("discogs_api.json.load", return_value=payload):
        result = get_master_versions("300", "token")
    assert result == [{"id": 5, "title": "A Pressing"}]

    request = mock_urlopen.call_args[0][0]
    assert "/masters/300/versions" in request.full_url


@patch("discogs_api.urllib.request.urlopen")
def test_get_release_returns_raw_resource(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {
        "id": 400,
        "title": "A Release",
        "tracklist": [{"position": "A1", "title": "Track One", "duration": "3:00"}],
    }
    with patch("discogs_api.json.load", return_value=payload):
        result = get_release("400", "token")
    assert result == payload

    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.discogs.com/releases/400"


@patch("discogs_api.urllib.request.urlopen")
def test_get_release_is_cached_across_calls(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {"id": 401, "title": "Cached Release"}
    with patch("discogs_api.json.load", return_value=payload):
        get_release("401", "token")
        get_release("401", "token")
    assert mock_urlopen.call_count == 1


@patch("discogs_api.urllib.request.urlopen")
def test_get_artist_returns_raw_resource(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {"id": 500, "name": "An Artist", "realname": "Real Name"}
    with patch("discogs_api.json.load", return_value=payload):
        result = get_artist("500", "token")
    assert result == payload

    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.discogs.com/artists/500"


@patch("discogs_api.urllib.request.urlopen")
def test_get_label_returns_raw_resource(mock_urlopen: MagicMock) -> None:
    payload: dict[str, Any] = {"id": 600, "name": "A Label"}
    with patch("discogs_api.json.load", return_value=payload):
        result = get_label("600", "token")
    assert result == payload

    request = mock_urlopen.call_args[0][0]
    assert request.full_url == "https://api.discogs.com/labels/600"
