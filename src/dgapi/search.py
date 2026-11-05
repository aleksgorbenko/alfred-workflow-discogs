from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import discogs_api
import names
import router
from alfred_items import HINT_OPEN, TYPE_ICONS, item, open_mod, with_hint
from discogs_api import DiscogsError

import images

if TYPE_CHECKING:
    from collections.abc import Callable

DISCOGS_BASE = "https://www.discogs.com"
DETAIL_WORKERS = 8
LIVE_TYPING_TIMEOUT_SECONDS = 2


def _first(value: list[Any] | str | None) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _release_subtitle(entry: dict[str, Any]) -> str:
    year = str(entry.get("year") or entry.get("released") or "")[:4]
    genres: list[str] = entry.get("genre") or entry.get("genres") or []
    styles: list[str] = entry.get("style") or entry.get("styles") or []
    genre_style = list(dict.fromkeys(genres + styles))
    parts = [
        year,
        entry.get("country", ""),
        _first(entry.get("label")),
        ", ".join(genre_style),
    ]
    return "・".join(part for part in parts if part)


def _artist_label_subtitle(entry: dict[str, Any], detail: dict[str, Any] | None) -> str:
    if not detail:
        return entry["type"].title()

    if entry["type"] == "artist":
        return detail.get("realname") or "Artist"

    parent_label: dict[str, Any] = detail.get("parent_label") or {}
    parent = parent_label.get("name")
    if parent:
        return f"Sub-label of {parent}"
    sublabels: list[Any] = detail.get("sublabels") or []
    if sublabels:
        return f"{len(sublabels)} sub-labels"
    return "Label"


def _subtitle(entry: dict[str, Any], detail: dict[str, Any] | None) -> str:
    if entry["type"] in ("release", "master"):
        return _release_subtitle(entry)
    return _artist_label_subtitle(entry, detail)


def _fetch_details(
    entries: list[dict[str, Any]], token: str
) -> dict[str, dict[str, Any]]:
    targets = [
        (str(entry["id"]), entry["type"])
        for entry in entries
        if entry["type"] in ("artist", "label")
    ]
    if not token or not targets:
        return {}

    details: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        fetch: dict[str, Callable[[str, str], dict[str, Any]]] = {
            "artist": discogs_api.get_artist,
            "label": discogs_api.get_label,
        }
        future_to_id = {
            executor.submit(fetch[entry_type], entry_id, token): entry_id
            for entry_id, entry_type in targets
        }
        for future, entry_id in future_to_id.items():
            try:
                details[entry_id] = future.result()
            except DiscogsError:
                continue
    return details


def named(
    entries: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str, router.Ref]]:
    labels = router.unique([(entry["title"], entry["type"]) for entry in entries])
    return [
        (entry, label, (entry["type"], str(entry["id"])))
        for entry, label in zip(entries, labels, strict=True)
    ]


def build_items(entries: list[dict[str, Any]], token: str = "") -> list[dict[str, Any]]:
    if not entries:
        return [item(title="No results on Discogs", valid=False)]

    listed = named(entries)
    names.remember(
        {
            names.path_key((label,)): f"{kind}/{entry_id}"
            for _entry, label, (kind, entry_id) in listed
        }
    )
    icons = images.warm(
        [entry.get("thumb") for entry in entries],
        timeout_seconds=LIVE_TYPING_TIMEOUT_SECONDS,
    )
    details = _fetch_details(entries, token)
    return [
        item(
            title=entry["title"],
            subtitle=with_hint(
                _subtitle(entry, details.get(str(entry["id"]))), HINT_OPEN
            ),
            valid=False,
            autocomplete=router.drill("", label),
            icon=icons.get(entry.get("thumb") or "") or TYPE_ICONS.get(kind),
            mods=open_mod(f"{DISCOGS_BASE}{entry['uri']}"),
        )
        for entry, label, (kind, _entry_id) in listed
    ]
