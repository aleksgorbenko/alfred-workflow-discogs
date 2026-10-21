from typing import TYPE_CHECKING

from cache import PRIVATE_DIRECTORY, cache_dir, cached

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

PRIVATE_FILE = 0o600
ONE_HOUR = 3600


def test_cached_value_is_written_privately(tmp_path: Path) -> None:
    tmp_path.chmod(0o755)
    cached("k", ONE_HOUR, lambda: {"a": 1})
    written = next(tmp_path.glob("*.json"))
    assert written.stat().st_mode & 0o777 == PRIVATE_FILE
    assert tmp_path.stat().st_mode & 0o777 == PRIVATE_DIRECTORY


def test_missing_cache_folder_falls_back_to_a_private_temp_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("alfred_workflow_cache")
    assert cache_dir().stat().st_mode & 0o777 == PRIVATE_DIRECTORY
