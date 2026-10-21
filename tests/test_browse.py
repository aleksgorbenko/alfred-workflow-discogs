from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from browse import build_items, main
from discogs_api import DiscogsError

if TYPE_CHECKING:
    import pytest


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
    assert result["subtitle"] == "1999・US・Some Label・Vinyl, LP"
    assert result["arg"] == "https://www.discogs.com/release/10"
    assert result["icon"] == {"path": "/cache/a.jpg"}
    assert result["variables"] == {"DG_TYPE": "release", "DG_ID": "10"}


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
    assert result["subtitle"] == "1999"


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_skips_detail_fetch_without_token() -> None:
    entries = [{"id": 10, "title": "A Release", "year": 1999}]
    result = build_items("label", entries)[0]
    assert result["subtitle"] == "1999"


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
    assert result["arg"] == "https://www.discogs.com/release/20"
    assert result["variables"] == {"DG_TYPE": "release", "DG_ID": "20"}


@patch("browse.images.warm", return_value={})
def test_build_items_artist_entries_pass_through_own_type(mock_warm: MagicMock) -> None:
    entries = [
        {"id": 30, "type": "release", "title": "Solo Release"},
        {"id": 40, "type": "master", "title": "Grouped Master"},
    ]
    release_row, master_row = build_items("artist", entries)
    mock_warm.assert_called_once()
    assert release_row["arg"] == "https://www.discogs.com/release/30"
    assert release_row["variables"] == {"DG_TYPE": "release", "DG_ID": "30"}
    assert master_row["arg"] == "https://www.discogs.com/master/40"
    assert master_row["variables"] == {"DG_TYPE": "master", "DG_ID": "40"}


@patch("browse.images.warm", new=MagicMock(return_value={}))
def test_build_items_joins_artist_prefix_when_present() -> None:
    entries = [{"id": 50, "title": "A Release", "artist": "Some Artist"}]
    result = build_items("label", entries)[0]
    assert result["title"] == "Some Artist - A Release"


@patch.dict("os.environ", {}, clear=True)
def test_main_errors_when_token_missing(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    out = capsys.readouterr().out
    assert "token" in out.lower()


@patch.dict("os.environ", {"DISCOGS_API_TOKEN": "token", "DG_ID": "1"}, clear=True)
def test_main_errors_on_unrecognized_dg_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main()
    out = capsys.readouterr().out
    assert "selection" in out.lower() or "unrecognized" in out.lower()


@patch.dict(
    "os.environ",
    {"DISCOGS_API_TOKEN": "token", "DG_TYPE": "label"},
    clear=True,
)
def test_main_errors_when_dg_id_missing(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    out = capsys.readouterr().out
    assert "selection" in out.lower() or "unrecognized" in out.lower()


@patch.dict(
    "os.environ",
    {"DISCOGS_API_TOKEN": "token", "DG_TYPE": "label", "DG_ID": "5"},
    clear=True,
)
@patch("browse.discogs_api.get_label_releases", side_effect=DiscogsError("boom"))
def test_main_surfaces_discogs_error(
    mock_get: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    main()
    mock_get.assert_called_once()
    out = capsys.readouterr().out
    assert "boom" in out


@patch.dict(
    "os.environ",
    {"DISCOGS_API_TOKEN": "token", "DG_TYPE": "master", "DG_ID": "7"},
    clear=True,
)
@patch("browse.images.warm", return_value={})
@patch("browse.discogs_api.get_master_versions", return_value=[])
def test_main_dispatches_master_to_get_master_versions(
    mock_get: MagicMock, mock_warm: MagicMock
) -> None:
    main()
    mock_warm.assert_not_called()
    mock_get.assert_called_once_with("7", "token")
