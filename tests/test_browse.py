from unittest.mock import MagicMock, patch

from browse import build_items
from discogs_api import DiscogsError


@patch("browse.images.warm", return_value={})
def test_build_items_empty_list_shows_message(mock_warm: MagicMock) -> None:
    items = build_items("label", [])
    mock_warm.assert_not_called()
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch(
    "browse.images.warm",
    new=MagicMock(return_value={"https://img/a.jpg": "/cache/a.jpg"}),
)
def test_build_items_label_entries_are_releases() -> None:
    entries = [
        {
            "id": 10,
            "title": "A Release",
            "year": 1999,
            "country": "US",
            "label": "Some Label",
            "format": "Vinyl, LP",
            "thumb": "https://img/a.jpg",
        }
    ]
    result = build_items("label", entries)[0]
    assert result["title"] == "A Release"
    assert result["subtitle"] == "1999・US・Some Label・Vinyl, LP · ⌥↩ Open in browser"
    assert result["mods"]["alt"]["arg"] == "https://www.discogs.com/release/10"
    assert result["icon"] == {"path": "/cache/a.jpg"}
    assert result["autocomplete"] == "A Release > "


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_sorts_by_year_descending() -> None:
    entries = [
        {"id": 1, "title": "Oldest", "year": 1990},
        {"id": 2, "title": "Newest", "year": 2020},
        {"id": 3, "title": "Middle", "year": 2000},
    ]
    titles = [row["title"] for row in build_items("label", entries)]
    assert titles == ["Newest", "Middle", "Oldest"]


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_uses_released_field_when_year_missing() -> None:
    entries = [{"id": 1, "title": "A Pressing", "released": "1959-08-17"}]
    result = build_items("master", entries)[0]
    assert result["subtitle"].startswith("1959")


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_sorts_entries_with_missing_year_last() -> None:
    entries = [
        {"id": 1, "title": "No Year"},
        {"id": 2, "title": "Has Year", "year": 2000},
    ]
    titles = [row["title"] for row in build_items("label", entries)]
    assert titles == ["Has Year", "No Year"]


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_uses_only_first_label() -> None:
    entries = [{"id": 10, "title": "A Release", "label": ["Warp", "Rephlex"]}]
    result = build_items("label", entries)[0]
    assert "Warp" in result["subtitle"]
    assert "Rephlex" not in result["subtitle"]


@patch(
    "browse.discogs_api.get_release",
    return_value={"genres": ["Electronic"], "styles": ["Ambient", "Techno"]},
)
@patch("browse.images.warm", return_value={})
def test_build_items_enriches_release_rows_with_genres_and_styles(
    mock_warm: MagicMock, mock_get_release: MagicMock
) -> None:
    entries = [{"id": 10, "title": "A Release", "year": 1999}]
    result = build_items("label", entries, token="token")[0]
    assert "Electronic" in result["subtitle"]
    assert "Ambient" in result["subtitle"]
    assert "Techno" in result["subtitle"]
    mock_get_release.assert_called_once_with("10", "token")
    mock_warm.assert_called_once()


@patch(
    "browse.discogs_api.get_release", new=MagicMock(side_effect=DiscogsError("boom"))
)
@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_falls_back_when_detail_fetch_fails() -> None:
    entries = [{"id": 10, "title": "A Release", "year": 1999}]
    result = build_items("label", entries, token="token")[0]
    assert result["subtitle"] == "1999 · ⌥↩ Open in browser"


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_skips_detail_fetch_without_token() -> None:
    entries = [{"id": 10, "title": "A Release", "year": 1999}]
    result = build_items("label", entries)[0]
    assert result["subtitle"] == "1999 · ⌥↩ Open in browser"


@patch("browse.discogs_api.get_release", return_value={})
@patch("browse.images.warm", return_value={})
def test_build_items_skips_detail_fetch_for_master_rows(
    mock_warm: MagicMock, mock_get_release: MagicMock
) -> None:
    entries = [{"id": 40, "type": "master", "title": "Grouped Master"}]
    build_items("artist", entries, token="token")
    mock_warm.assert_called_once()
    mock_get_release.assert_not_called()


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_master_entries_are_releases() -> None:
    entries = [{"id": 20, "title": "A Pressing", "year": 2001}]
    result = build_items("master", entries)[0]
    assert result["mods"]["alt"]["arg"] == "https://www.discogs.com/release/20"
    assert result["autocomplete"] == "A Pressing > "


@patch("browse.images.warm", return_value={})
def test_build_items_artist_entries_pass_through_own_type(mock_warm: MagicMock) -> None:
    entries = [
        {"id": 30, "type": "release", "title": "Solo Release"},
        {"id": 40, "type": "master", "title": "Grouped Master"},
    ]
    release_row, master_row = build_items("artist", entries)
    mock_warm.assert_called_once()
    assert release_row["autocomplete"] == "Solo Release > "
    assert master_row["mods"]["alt"]["arg"] == "https://www.discogs.com/master/40"
    assert master_row["autocomplete"] == "Grouped Master > "


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_joins_artist_prefix_when_present() -> None:
    entries = [{"id": 50, "title": "A Release", "artist": "Some Artist"}]
    result = build_items("label", entries)[0]
    assert result["title"] == "Some Artist - A Release"


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_extend_the_current_path() -> None:
    entries = [{"id": 50, "title": "A Release"}]
    result = build_items("artist", entries, parent=("Artist",))[0]
    assert result["autocomplete"] == "Artist > A Release > "
