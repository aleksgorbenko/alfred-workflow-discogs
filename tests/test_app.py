import json
from typing import Any
from unittest.mock import MagicMock, patch

import app
import names
import pytest
from discogs_api import DiscogsError

TOKEN = "token"
RELEASES = [
    {"id": 1, "title": "First", "year": 2001},
    {"id": 2, "title": "Second", "year": 2000},
]
RELEASE: dict[str, Any] = {
    "id": 9,
    "title": "The Album",
    "artists": [{"name": "Artist"}],
    "tracklist": [
        {"position": "A1", "title": "Alpha", "type_": "track"},
        {"position": "A2", "title": "Beta", "type_": "track"},
    ],
}


def titles(rows: list[dict[str, Any]]) -> list[str]:
    return [row["title"] for row in rows]


def test_missing_token_asks_for_setup() -> None:
    assert "API Token" in titles(app.run("lofi", ""))[0]


def test_empty_query_prompts() -> None:
    assert titles(app.run("", TOKEN)) == ["Type to search Discogs…"]


@patch("app.discogs_api.search", return_value=[])
def test_plain_text_searches(mock_search: MagicMock) -> None:
    assert titles(app.run("lofi", TOKEN)) == ["No results on Discogs"]
    mock_search.assert_called_once_with("lofi", TOKEN)


@pytest.fixture
def known() -> None:
    names.remember(
        {
            names.path_key(("Aphex",)): "artist/5",
            names.path_key(("Aphex", "First")): "release/9",
            names.path_key(("Label",)): "label/5",
            names.path_key(("Master",)): "master/5",
        }
    )


@pytest.mark.usefixtures("known")
@patch("browse.images.warm", new=MagicMock(return_value={}))
@patch("browse.discogs_api.get_release", new=MagicMock(return_value={}))
@patch("app.browse.fetch", return_value=RELEASES)
def test_artist_page_lists_releases_under_a_header(mock_fetch: MagicMock) -> None:
    rows = app.run("Aphex > ", TOKEN)
    mock_fetch.assert_called_once_with("artist", "5", TOKEN)
    assert titles(rows) == ["Aphex", "First", "Second"]
    assert rows[0]["arg"] == "https://www.discogs.com/artist/5"
    assert rows[0]["autocomplete"] == ""
    assert rows[1]["autocomplete"] == "Aphex > First > "


@pytest.mark.usefixtures("known")
@patch("browse.images.warm", new=MagicMock(return_value={}))
@patch("browse.discogs_api.get_release", new=MagicMock(return_value={}))
@patch("app.browse.fetch", new=MagicMock(return_value=RELEASES))
def test_master_page_filters_releases() -> None:
    assert titles(app.run("Master > sec", TOKEN)) == ["Master", "Second"]
    assert titles(app.run("Master > zzz", TOKEN))[1] == "No release matches 'zzz'"


@pytest.mark.usefixtures("known")
@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("app.discogs_api.get_release", return_value=RELEASE)
def test_release_page_lists_tracks_under_a_header(mock_get: MagicMock) -> None:
    rows = app.run("Aphex > First > ", TOKEN)
    mock_get.assert_called_once_with("9", TOKEN)
    assert titles(rows) == ["First", "A1 Alpha", "A2 Beta"]
    assert rows[0]["arg"] == "https://www.discogs.com/release/9"
    assert rows[0]["autocomplete"] == "Aphex > "
    assert rows[0]["subtitle"].startswith("Artist")


@pytest.mark.usefixtures("known")
@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("app.discogs_api.get_release", new=MagicMock(return_value=RELEASE))
def test_release_page_filters_tracks() -> None:
    assert titles(app.run("Aphex > First > bet", TOKEN)) == ["First", "A2 Beta"]
    assert titles(app.run("Aphex > First > zzz", TOKEN))[1] == (
        "No track matches 'zzz'"
    )


HITS = [
    {"id": 7, "title": "Aphex Live", "type": "label"},
    {"id": 5, "title": "Aphex", "type": "artist"},
]


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
@patch("browse.images.warm", new=MagicMock(return_value={}))
@patch("browse.discogs_api.get_release", new=MagicMock(return_value=RELEASE))
@patch("app.discogs_api.get_release", new=MagicMock(return_value=RELEASE))
@patch("app.browse.fetch", new=MagicMock(return_value=RELEASES))
@patch("app.discogs_api.search", return_value=HITS)
def test_unremembered_paths_are_resolved_by_name(mock_search: MagicMock) -> None:
    rows = app.run("aphex > first > ", TOKEN)
    mock_search.assert_called_once_with("aphex", TOKEN)
    assert rows[0]["title"] == "first"
    assert rows[0]["arg"] == "https://www.discogs.com/release/1"


@patch("app.discogs_api.search", new=MagicMock(return_value=[]))
def test_nothing_found_for_a_name_is_an_error() -> None:
    with pytest.raises(DiscogsError):
        app.run("Nobody > ", TOKEN)


@patch("app.discogs_api.search", new=MagicMock(return_value=HITS))
@patch("app.browse.fetch", new=MagicMock(return_value=RELEASES))
def test_unknown_names_are_errors() -> None:
    with pytest.raises(DiscogsError):
        app.run("Aphex > Missing > ", TOKEN)
    with pytest.raises(DiscogsError):
        app.run("Aphex > First > Deeper > ", TOKEN)


@patch("app.discogs_api.search", new=MagicMock(side_effect=DiscogsError("boom")))
@patch.dict("os.environ", {"DISCOGS_API_TOKEN": TOKEN}, clear=True)
def test_main_surfaces_discogs_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, Any] = {}

    def store(_directory: object, query: str, payload: dict[str, Any]) -> None:
        stored[query] = payload

    monkeypatch.setattr("app.finish", store)
    app.main(["--job", "query"])
    assert "boom" in stored["query"]["items"][0]["title"]


@patch.dict("os.environ", {}, clear=True)
def test_main_without_a_token_asks_for_setup(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app.main([])
    assert "API Token" in capsys.readouterr().out


def served(*_args: object, **_kwargs: object) -> dict[str, Any]:
    return {"items": [{"title": "x"}]}


def test_main_serves_the_view_for_a_query(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DISCOGS_API_TOKEN", TOKEN)
    monkeypatch.setattr("app.serve", served)
    app.main(["lofi"])
    assert json.loads(capsys.readouterr().out)["items"][0]["title"] == "x"


def test_job_stores_the_view(monkeypatch: pytest.MonkeyPatch) -> None:
    stored: dict[str, Any] = {}

    def store(_directory: object, query: str, payload: dict[str, Any]) -> None:
        stored[query] = payload

    monkeypatch.setenv("DISCOGS_API_TOKEN", TOKEN)
    monkeypatch.setattr("app.finish", store)
    app.main(["--job", ""])
    assert stored[""]["items"][0]["title"] == "Type to search Discogs…"


def test_job_stores_an_error_row_when_the_view_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored: dict[str, Any] = {}

    def store(_directory: object, query: str, payload: dict[str, Any]) -> None:
        stored[query] = payload

    def fail(*_args: object) -> list[dict[str, Any]]:
        msg = "boom"
        raise RuntimeError(msg)

    monkeypatch.setenv("DISCOGS_API_TOKEN", TOKEN)
    monkeypatch.setattr("app.finish", store)
    monkeypatch.setattr("app.run", fail)
    app.main(["--job", "q"])
    assert stored["q"]["items"][0]["title"] == "boom"


def test_loading_labels_name_what_is_loading() -> None:
    assert app.loading_label("lofi") == "Searching Discogs for 'lofi'…"
    assert app.loading_label("Aphex > First > ") == "Loading First…"
