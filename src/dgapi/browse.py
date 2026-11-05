from concurrent.futures import ThreadPoolExecutor
from typing import Any

import discogs_api
import names
import router
from alfred_items import HINT_OPEN, TYPE_ICONS, item, open_mod, with_hint
from discogs_api import DiscogsError

import images

DISCOGS_BASE = "https://www.discogs.com"
DETAIL_WORKERS = 8


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


def _qualifier(entry: dict[str, Any]) -> str:
    year = _year(entry)
    return ", ".join(
        part for part in (str(year) if year else "", entry.get("country", "")) if part
    )


def named(
    dg_type: str, entries: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], str, router.Ref]]:
    ordered = sorted(entries, key=_year, reverse=True)
    labels = router.unique([(entry["title"], _qualifier(entry)) for entry in ordered])
    return [
        (entry, label, (_entry_type(dg_type, entry), str(entry["id"])))
        for entry, label in zip(ordered, labels, strict=True)
    ]


def build_items(
    dg_type: str,
    entries: list[dict[str, Any]],
    token: str = "",
    parent: tuple[str, ...] = (),
) -> list[dict[str, Any]]:
    if not entries:
        return [item(title="No releases found", valid=False)]

    listed = named(dg_type, entries)
    names.remember(
        {
            names.path_key((*parent, label)): f"{kind}/{entry_id}"
            for _entry, label, (kind, entry_id) in listed
        }
    )
    icons = images.warm([entry.get("thumb") for entry, _label, _ref in listed])
    details = _fetch_details(dg_type, [entry for entry, _label, _ref in listed], token)
    here = router.path(parent)
    return [
        item(
            title=_title(entry),
            subtitle=with_hint(_subtitle(entry, details.get(entry_id)), HINT_OPEN),
            valid=False,
            autocomplete=router.drill(here, label),
            icon=icons.get(entry.get("thumb") or "") or TYPE_ICONS.get(kind),
            mods=open_mod(f"{DISCOGS_BASE}/{kind}/{entry_id}"),
        )
        for entry, label, (kind, entry_id) in listed
    ]


def fetch(dg_type: str, dg_id: str, token: str) -> list[dict[str, Any]]:
    if dg_type == "label":
        return discogs_api.get_label_releases(dg_id, token)
    if dg_type == "artist":
        return discogs_api.get_artist_releases(dg_id, token)
    return discogs_api.get_master_versions(dg_id, token)
