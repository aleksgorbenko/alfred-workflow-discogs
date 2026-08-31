import urllib.error
from pathlib import Path
from unittest.mock import patch

from images import TIMEOUT_SECONDS, warm

CUSTOM_TIMEOUT_SECONDS = 2


@patch("images.urllib.request.urlopen")
def test_warm_returns_local_path_for_each_url(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"jpegbytes"
    result = warm(["https://img.example.com/a.jpg", "https://img.example.com/b.jpg"])

    assert set(result.keys()) == {
        "https://img.example.com/a.jpg",
        "https://img.example.com/b.jpg",
    }
    for path in result.values():
        assert Path(path).is_file()
        assert Path(path).read_bytes() == b"jpegbytes"


def test_warm_skips_none_urls():
    result = warm([None, ""])
    assert result == {}


@patch("images.urllib.request.urlopen")
def test_warm_skips_on_download_failure(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("no network")
    result = warm(["https://img.example.com/broken.jpg"])
    assert result == {}


@patch("images.urllib.request.urlopen")
def test_warm_does_not_redownload_already_cached_url(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"jpegbytes"
    url = "https://img.example.com/cached.jpg"
    first = warm([url])
    assert mock_urlopen.call_count == 1
    Path(first[url]).write_bytes(b"jpegbytes")

    second = warm([url])
    assert second == first
    assert mock_urlopen.call_count == 1


@patch("images.urllib.request.urlopen")
def test_warm_sends_user_agent_header(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"x"
    warm(["https://img.example.com/ua.jpg"])

    request = mock_urlopen.call_args[0][0]
    assert request.get_header("User-agent")


@patch("images.urllib.request.urlopen")
def test_warm_uses_default_timeout(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"x"
    warm(["https://img.example.com/default-timeout.jpg"])

    assert mock_urlopen.call_args.kwargs["timeout"] == TIMEOUT_SECONDS


@patch("images.urllib.request.urlopen")
def test_warm_uses_custom_timeout(mock_urlopen):
    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"x"
    warm(
        ["https://img.example.com/custom-timeout.jpg"],
        timeout_seconds=CUSTOM_TIMEOUT_SECONDS,
    )

    assert mock_urlopen.call_args.kwargs["timeout"] == CUSTOM_TIMEOUT_SECONDS
