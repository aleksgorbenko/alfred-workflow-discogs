from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

from discogs_api import DiscogsError
from tracklist import build_items, main

if TYPE_CHECKING:
    import pytest


def test_build_items_empty_tracklist_shows_message() -> None:
    items = build_items({"id": 1, "tracklist": []})
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
def test_build_items_track_rows_are_valid_and_show_duration() -> None:
    release: dict[str, Any] = {
        "id": 1,
        "tracklist": [
            {
                "position": "A1",
                "title": "Track One",
                "duration": "3:32",
                "type_": "track",
            }
        ],
    }
    result = build_items(release)[0]
    assert result["valid"] is True
    assert "Track One" in result["title"]
    assert result["subtitle"] == "3:32"
    assert result["arg"] == "https://www.discogs.com/release/1"


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
def test_build_items_heading_rows_are_not_valid() -> None:
    release: dict[str, Any] = {
        "id": 1,
        "tracklist": [{"position": "", "title": "Side A", "type_": "heading"}],
    }
    result = build_items(release)[0]
    assert result["valid"] is False


@patch(
    "tracklist.images.warm",
    return_value={"https://img/cover.jpg": "/cache/cover.jpg"},
)
def test_build_items_uses_release_cover_art_for_every_track(
    mock_warm: MagicMock,
) -> None:
    release: dict[str, Any] = {
        "id": 1,
        "thumb": "https://img/cover.jpg",
        "tracklist": [
            {"position": "A1", "title": "Track One", "type_": "track"},
            {"position": "A2", "title": "Track Two", "type_": "track"},
        ],
    }
    rows = build_items(release)
    assert all(row["icon"] == {"path": "/cache/cover.jpg"} for row in rows)
    mock_warm.assert_called_once_with(["https://img/cover.jpg"])


@patch("tracklist.images.warm", new=MagicMock(return_value={}))
def test_build_items_falls_back_to_track_icon_without_cover() -> None:
    release: dict[str, Any] = {
        "id": 1,
        "tracklist": [{"position": "A1", "title": "Track One", "type_": "track"}],
    }
    result = build_items(release)[0]
    assert result["icon"] == {"path": "icons/icon_track.png"}


@patch("tracklist.images.warm", return_value={})
def test_build_items_appends_videos_after_tracks(mock_warm: MagicMock) -> None:
    release: dict[str, Any] = {
        "id": 1,
        "tracklist": [{"position": "A1", "title": "Track One", "type_": "track"}],
        "videos": [
            {"title": "Betke - Paris", "uri": "https://www.youtube.com/watch?v=abc"}
        ],
    }
    rows = build_items(release)
    mock_warm.assert_not_called()
    assert len(rows) == len(release["tracklist"]) + len(release["videos"])
    video_row = rows[-1]
    assert video_row["title"] == "Betke - Paris"
    assert video_row["subtitle"] == "📽️ YouTube・https://www.youtube.com/watch?v=abc"
    assert video_row["arg"] == "https://www.youtube.com/watch?v=abc"
    assert video_row["valid"] is True


@patch("tracklist.images.warm", return_value={})
def test_build_items_shows_videos_when_tracklist_empty(mock_warm: MagicMock) -> None:
    release: dict[str, Any] = {
        "id": 1,
        "tracklist": [],
        "videos": [{"title": "A Video", "uri": "https://www.youtube.com/watch?v=x"}],
    }
    rows = build_items(release)
    mock_warm.assert_not_called()
    assert len(rows) == 1
    assert rows[0]["title"] == "A Video"


@patch("tracklist.images.warm", return_value={})
def test_build_items_skips_videos_missing_uri(mock_warm: MagicMock) -> None:
    release: dict[str, Any] = {
        "id": 1,
        "tracklist": [{"position": "A1", "title": "Track One", "type_": "track"}],
        "videos": [{"title": "No URI"}],
    }
    rows = build_items(release)
    mock_warm.assert_not_called()
    assert len(rows) == 1


@patch.dict("os.environ", {}, clear=True)
def test_main_errors_when_token_missing(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    out = capsys.readouterr().out
    assert "token" in out.lower()


@patch.dict("os.environ", {"DISCOGS_API_TOKEN": "token"}, clear=True)
def test_main_errors_when_dg_id_missing(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    out = capsys.readouterr().out
    assert "release" in out.lower() or "selection" in out.lower()


@patch.dict("os.environ", {"DISCOGS_API_TOKEN": "token", "DG_ID": "1"}, clear=True)
@patch("tracklist.discogs_api.get_release", side_effect=DiscogsError("boom"))
def test_main_surfaces_discogs_error(
    mock_get: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    main()
    mock_get.assert_called_once()
    out = capsys.readouterr().out
    assert "boom" in out


@patch.dict("os.environ", {"DISCOGS_API_TOKEN": "token", "DG_ID": "1"}, clear=True)
@patch("tracklist.discogs_api.get_release", return_value={"id": 1, "tracklist": []})
def test_main_dispatches_with_dg_id(mock_get: MagicMock) -> None:
    main()
    mock_get.assert_called_once_with("1", "token")
