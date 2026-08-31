from unittest.mock import patch

from discogs_api import DiscogsError
from search import build_items, main


@patch("search.images.warm", return_value={})
def test_build_items_empty_list_shows_no_results(_mock_warm):
    items = build_items([])
    assert len(items) == 1
    assert items[0]["valid"] is False


@patch("search.images.warm", return_value={"https://img/a.jpg": "/tmp/a.jpg"})
def test_build_items_shape(_mock_warm):
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
    assert len(items) == 1
    result = items[0]
    assert result["title"] == "Selected Ambient Works"
    assert result["subtitle"] == "1992・UK・Apollo・Ambient, Techno"
    assert (
        result["arg"]
        == "https://www.discogs.com/release/1-Aphex-Twin-Selected-Ambient-Works"
    )
    assert result["icon"] == {"path": "/tmp/a.jpg"}
    assert result["variables"] == {"DG_TYPE": "release", "DG_ID": "1"}


@patch("search.images.warm", return_value={})
def test_build_items_master_subtitle_same_as_release(_mock_warm):
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


@patch("search.images.warm", return_value={})
def test_build_items_falls_back_to_type_icon_when_no_thumb(_mock_warm):
    entries = [{"id": 2, "type": "artist", "title": "Aphex Twin", "uri": "/artist/2"}]
    result = build_items(entries)[0]
    assert result["icon"] == {"path": "icons/icon_artist.png"}
    assert result["variables"] == {"DG_TYPE": "artist", "DG_ID": "2"}
    assert result["subtitle"] == "Artist"


@patch("search.images.warm", return_value={})
def test_build_items_uses_only_first_label(_mock_warm):
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
def test_build_items_enriches_artist_row_with_realname(_mock_warm, mock_get_artist):
    entries = [{"id": 2, "type": "artist", "title": "Aphex Twin", "uri": "/artist/2"}]
    result = build_items(entries, token="token")[0]
    assert result["subtitle"] == "Richard D. James"
    mock_get_artist.assert_called_once_with("2", "token")


@patch(
    "search.discogs_api.get_label",
    return_value={"parent_label": {"name": "Warp Records"}},
)
@patch("search.images.warm", return_value={})
def test_build_items_enriches_label_row_with_parent_label(_mock_warm, mock_get_label):
    entries = [{"id": 4, "type": "label", "title": "Apollo", "uri": "/label/4"}]
    result = build_items(entries, token="token")[0]
    assert "Warp Records" in result["subtitle"]
    mock_get_label.assert_called_once_with("4", "token")


@patch("search.discogs_api.get_artist", side_effect=DiscogsError("boom"))
@patch("search.images.warm", return_value={})
def test_build_items_falls_back_when_artist_detail_fetch_fails(_mock_warm, _mock_get):
    entries = [{"id": 2, "type": "artist", "title": "Aphex Twin", "uri": "/artist/2"}]
    result = build_items(entries, token="token")[0]
    assert result["subtitle"] == "Artist"


def test_main_prompts_on_empty_query(capsys):
    main([""])
    out = capsys.readouterr().out
    assert "Type to search" in out


@patch.dict("os.environ", {}, clear=True)
def test_main_errors_when_token_missing(capsys):
    main(["query"])
    out = capsys.readouterr().out
    assert "token" in out.lower()


@patch.dict("os.environ", {"DISCOGS_API_TOKEN": "token"})
@patch("search.discogs_api.search", side_effect=DiscogsError("boom"))
def test_main_surfaces_discogs_error(_mock_search, capsys):
    main(["query"])
    out = capsys.readouterr().out
    assert "boom" in out
