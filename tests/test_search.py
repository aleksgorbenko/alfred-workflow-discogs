from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from discogs_api import DiscogsError
from search import build_items, main

if TYPE_CHECKING:
    import pytest


@patch("search.images.warm", return_value={})
def test_build_items_empty_list_shows_no_results(mock_warm: MagicMock) -> None:
    items = build_items([])
    mock_warm.assert_not_called()
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch("search.images.warm", return_value={"https://img/a.jpg": "/cache/a.jpg"})
def test_build_items_shape(mock_warm: MagicMock) -> None:
    entries = [
        {
            "id": 1,
            "type": "release",
            "title": "Selected Ambient Works",
            "year": "1992",
            "country": "UK",
            "label": "Apollo",
            "style": ["Ambient", "Techno"],
            "uri": "/release/1-Aphex-Twin-Selected-Ambient-Works",
            "thumb": "https://img/a.jpg",
        }
    ]
    items = build_items(entries)
    mock_warm.assert_called_once()
    assert len(items) == 1
    result = items[0]
    assert result["title"] == "Selected Ambient Works"
    assert result["subtitle"] == "1992・UK・Apollo・Ambient, Techno"
    assert (
        result["arg"]
        == "https://www.discogs.com/release/1-Aphex-Twin-Selected-Ambient-Works"
    )
    assert result["icon"] == {"path": "/cache/a.jpg"}
    assert result["variables"] == {"DG_TYPE": "release", "DG_ID": "1"}


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_master_subtitle_same_as_release() -> None:
    entries = [
        {
            "id": 3,
            "type": "master",
            "title": "A Master",
            "year": "1959",
            "country": "US",
            "uri": "/master/3",
        }
    ]
    result = build_items(entries)[0]
    assert result["subtitle"] == "1959・US"


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_falls_back_to_type_icon_when_no_thumb() -> None:
    entries = [{"id": 2, "type": "artist", "title": "Aphex Twin", "uri": "/artist/2"}]
    result = build_items(entries)[0]
    assert result["icon"] == {"path": "icons/icon_artist.png"}
    assert result["variables"] == {"DG_TYPE": "artist", "DG_ID": "2"}
    assert result["subtitle"] == "Artist"


@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_uses_only_first_label() -> None:
    entries = [
        {
            "id": 1,
            "type": "release",
            "title": "A Release",
            "label": ["Warp", "Rephlex"],
            "uri": "/release/1",
        }
    ]
    result = build_items(entries)[0]
    assert "Warp" in result["subtitle"]
    assert "Rephlex" not in result["subtitle"]


@patch("search.discogs_api.get_artist", return_value={"realname": "Richard D. James"})
@patch("search.images.warm", return_value={})
def test_build_items_enriches_artist_row_with_realname(
    mock_warm: MagicMock, mock_get_artist: MagicMock
) -> None:
    entries = [{"id": 2, "type": "artist", "title": "Aphex Twin", "uri": "/artist/2"}]
    result = build_items(entries, token="token")[0]
    assert result["subtitle"] == "Richard D. James"
    mock_get_artist.assert_called_once_with("2", "token")
    mock_warm.assert_called_once()


@patch(
    "search.discogs_api.get_label",
    return_value={"parent_label": {"name": "Warp Records"}},
)
@patch("search.images.warm", return_value={})
def test_build_items_enriches_label_row_with_parent_label(
    mock_warm: MagicMock, mock_get_label: MagicMock
) -> None:
    entries = [{"id": 4, "type": "label", "title": "Apollo", "uri": "/label/4"}]
    result = build_items(entries, token="token")[0]
    assert "Warp Records" in result["subtitle"]
    mock_get_label.assert_called_once_with("4", "token")
    mock_warm.assert_called_once()


@patch("search.discogs_api.get_artist", new=MagicMock(side_effect=DiscogsError("boom")))
@patch("search.images.warm", new=MagicMock(return_value={}))
def test_build_items_falls_back_when_artist_detail_fetch_fails() -> None:
    entries = [{"id": 2, "type": "artist", "title": "Aphex Twin", "uri": "/artist/2"}]
    result = build_items(entries, token="token")[0]
    assert result["subtitle"] == "Artist"


def test_main_prompts_on_empty_query(capsys: pytest.CaptureFixture[str]) -> None:
    main([""])
    out = capsys.readouterr().out
    assert "Type to search" in out


@patch.dict("os.environ", {}, clear=True)
def test_main_errors_when_token_missing(capsys: pytest.CaptureFixture[str]) -> None:
    main(["query"])
    out = capsys.readouterr().out
    assert "token" in out.lower()


@patch.dict("os.environ", {"DISCOGS_API_TOKEN": "token"})
@patch("search.discogs_api.search", side_effect=DiscogsError("boom"))
def test_main_surfaces_discogs_error(
    mock_search: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    main(["query"])
    mock_search.assert_called_once()
    out = capsys.readouterr().out
    assert "boom" in out
