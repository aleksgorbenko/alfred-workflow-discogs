import json
from typing import TYPE_CHECKING, cast

from cache import cache_dir

if TYPE_CHECKING:
    from pathlib import Path

FILE = "names.json"
PRIVATE_FILE = 0o600


def _path() -> Path:
    return cache_dir() / FILE


def _load() -> dict[str, str]:
    try:
        data: object = json.loads(_path().read_text())
    except OSError, ValueError:
        return {}
    if not isinstance(data, dict):
        return {}
    mapping = cast("dict[object, object]", data)
    return {str(key): str(value) for key, value in mapping.items()}


def remember(entries: dict[str, str]) -> None:
    known = _load()
    if all(known.get(key) == value for key, value in entries.items()):
        return
    path = _path()
    path.write_text(json.dumps(known | entries))
    path.chmod(PRIVATE_FILE)


def recall(key: str) -> str:
    return _load().get(key, "")


def path_key(names: tuple[str, ...]) -> str:
    return "|".join(name.casefold() for name in names)
