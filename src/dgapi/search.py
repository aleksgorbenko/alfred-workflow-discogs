import os
import sys
from concurrent.futures import ThreadPoolExecutor

import discogs_api
import images
from alfred_items import TYPE_ICONS, emit, error_item, item
from discogs_api import DiscogsError

DISCOGS_BASE = "https://www.discogs.com"
DETAIL_WORKERS = 8
LIVE_TYPING_TIMEOUT_SECONDS = 2


def _first(value: list | str | None) -> str:
    if isinstance(value, list):
        return value[0] if value else ""
    return value or ""


def _joined(value: list | str | None) -> str:
    return ", ".join(value) if isinstance(value, list) else (value or "")


def _release_subtitle(entry: dict) -> str:
    year = str(entry.get("year") or entry.get("released") or "")[:4]
    genre_style = list(
        dict.fromkeys(
            (entry.get("genre") or entry.get("genres") or [])
            + (entry.get("style") or entry.get("styles") or [])
        )
    )
    parts = [
        year,
        entry.get("country", ""),
        _first(entry.get("label")),
        ", ".join(genre_style),
    ]
    return "・".join(part for part in parts if part)


def _artist_label_subtitle(entry: dict, detail: dict | None) -> str:
    if not detail:
        return entry["type"].title()

    if entry["type"] == "artist":
        return detail.get("realname") or "Artist"

    parent = (detail.get("parent_label") or {}).get("name")
    if parent:
        return f"Sub-label of {parent}"
    sublabels = detail.get("sublabels") or []
    if sublabels:
        return f"{len(sublabels)} sub-labels"
    return "Label"


def _subtitle(entry: dict, detail: dict | None) -> str:
    if entry["type"] in ("release", "master"):
        return _release_subtitle(entry)
    return _artist_label_subtitle(entry, detail)


def _fetch_details(entries: list[dict], token: str) -> dict[str, dict]:
    targets = [
        (str(entry["id"]), entry["type"])
        for entry in entries
        if entry["type"] in ("artist", "label")
    ]
    if not token or not targets:
        return {}

    details: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as executor:
        fetch = {"artist": discogs_api.get_artist, "label": discogs_api.get_label}
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


def build_items(entries: list[dict], token: str = "") -> list[dict]:
    if not entries:
        return [item(title="No results on Discogs", valid=False)]

    icons = images.warm(
        [entry.get("thumb") for entry in entries],
        timeout_seconds=LIVE_TYPING_TIMEOUT_SECONDS,
    )
    details = _fetch_details(entries, token)
    return [
        item(
            title=entry["title"],
            subtitle=_subtitle(entry, details.get(str(entry["id"]))),
            arg=f"{DISCOGS_BASE}{entry['uri']}",
            icon=icons.get(entry.get("thumb")) or TYPE_ICONS.get(entry["type"]),
            variables={"DG_TYPE": entry["type"], "DG_ID": str(entry["id"])},
        )
        for entry in entries
    ]


def main(argv: list[str]) -> None:
    query = argv[0].strip() if argv else ""
    if not query:
        emit([item(title="Type to search Discogs…", valid=False)])
        return

    token = os.environ.get("DISCOGS_API_TOKEN", "")
    if not token:
        emit([error_item("Set your Discogs API Token in the workflow configuration")])
        return

    try:
        entries = discogs_api.search(query, token)
    except DiscogsError as error:
        emit([error_item(str(error))])
        return

    emit(build_items(entries, token))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
