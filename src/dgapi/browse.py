import os
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import discogs_api
from alfred_items import TYPE_ICONS, emit, error_item, item
from discogs_api import DiscogsError

import images

DISCOGS_BASE = "https://www.discogs.com"
DETAIL_WORKERS = 8

_FETCHERS = ("label", "artist", "master")


def _entry_type(dg_type: str, entry: dict[str, Any]) -> str:
    return entry.get("type", "release") if dg_type == "artist" else "release"


def _title(entry: dict[str, Any]) -> str:
    artist = entry.get("artist")
    return f"{artist} - {entry['title']}" if artist else entry["title"]


def _year(entry: dict[str, Any]) -> int:
    value = str(entry.get("year") or entry.get("released") or "")[:4]
    return int(value) if value.isdigit() else 0


def _first(value: list[Any] | str | None) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _genres_and_styles(detail: dict[str, Any] | None) -> str:
    if not detail:
        return ""
    genres: list[str] = detail.get("genres") or []
    styles: list[str] = detail.get("styles") or []
    combined = list(dict.fromkeys(genres + styles))
    return ", ".join(combined)


def _subtitle(entry: dict[str, Any], detail: dict[str, Any] | None) -> str:
    year = _year(entry)
    fmt: list[str] | str | None = entry.get("format")
    parts = [
        str(year) if year else "",
        entry.get("country", ""),
        _first(entry.get("label")),
        ", ".join(fmt) if isinstance(fmt, list) else (fmt or ""),
        _genres_and_styles(detail),
    ]
    return "・".join(part for part in parts if part)


def _fetch_details(
    dg_type: str, entries: list[dict[str, Any]], token: str
) -> dict[str, dict[str, Any]]:
    release_ids = [
        str(entry["id"])
        for entry in entries
        if _entry_type(dg_type, entry) == "release"
    ]
    if not token or not release_ids:
        return {}

    details: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        future_to_id = {
            executor.submit(discogs_api.get_release, release_id, token): release_id
            for release_id in release_ids
        }
        for future, release_id in future_to_id.items():
            try:
                details[release_id] = future.result()
            except DiscogsError:
                continue
    return details


def build_items(
    dg_type: str, entries: list[dict[str, Any]], token: str = ""
) -> list[dict[str, Any]]:
    if not entries:
        return [item(title="No releases found", valid=False)]

    entries = sorted(entries, key=_year, reverse=True)
    icons = images.warm([entry.get("thumb") for entry in entries])
    details = _fetch_details(dg_type, entries, token)
    items: list[dict[str, Any]] = []
    for entry in entries:
        entry_type = _entry_type(dg_type, entry)
        entry_id = str(entry["id"])
        items.append(
            item(
                title=_title(entry),
                subtitle=_subtitle(entry, details.get(entry_id)),
                arg=f"{DISCOGS_BASE}/{entry_type}/{entry_id}",
                icon=icons.get(entry.get("thumb") or "") or TYPE_ICONS.get(entry_type),
                variables={"DG_TYPE": entry_type, "DG_ID": entry_id},
            )
        )
    return items


def _fetch(dg_type: str, dg_id: str, token: str) -> list[dict[str, Any]]:
    if dg_type == "label":
        return discogs_api.get_label_releases(dg_id, token)
    if dg_type == "artist":
        return discogs_api.get_artist_releases(dg_id, token)
    return discogs_api.get_master_versions(dg_id, token)


def main() -> None:
    token = os.environ.get("DISCOGS_API_TOKEN", "")
    if not token:
        emit([error_item("Set your Discogs API Token in the workflow configuration")])
        return

    dg_type = os.environ.get("DG_TYPE", "")
    dg_id = os.environ.get("DG_ID", "")
    if not dg_id or dg_type not in _FETCHERS:
        emit([error_item("No selection to browse")])
        return

    try:
        entries = _fetch(dg_type, dg_id, token)
    except DiscogsError as error:
        emit([error_item(str(error))])
        return

    emit(build_items(dg_type, entries, token))


if __name__ == "__main__":
    sys.exit(main())
