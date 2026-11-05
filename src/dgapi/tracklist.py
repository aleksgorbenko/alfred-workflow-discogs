from typing import Any

from alfred_items import item

import images

DISCOGS_BASE = "https://www.discogs.com"
TRACK_ICON = "icons/icon_track.png"


def _title(track: dict[str, Any]) -> str:
    position = track.get("position", "")
    title = track.get("title", "")
    return f"{position} {title}".strip() if position else title


def _cover_icon(release: dict[str, Any]) -> str:
    thumb = release.get("thumb") or ""
    if not thumb:
        return TRACK_ICON
    return images.warm([thumb]).get(thumb) or TRACK_ICON


def _video_items(release: dict[str, Any], icon: str) -> list[dict[str, Any]]:
    videos: list[dict[str, Any]] = release.get("videos") or []
    return [
        item(
            title=video.get("title") or "Video",
            subtitle=f"📽️ YouTube・{video['uri']}",
            arg=video["uri"],
            icon=icon,
        )
        for video in videos
        if video.get("uri")
    ]


def build_items(release: dict[str, Any]) -> list[dict[str, Any]]:
    tracklist = release.get("tracklist", [])
    videos: list[Any] = release.get("videos") or []
    if not tracklist and not videos:
        return [item(title="No tracklist available", valid=False)]

    release_url = f"{DISCOGS_BASE}/release/{release['id']}"
    icon = _cover_icon(release)
    items = [
        item(
            title=_title(track),
            subtitle=track.get("duration", ""),
            arg=release_url,
            valid=track.get("type_") == "track",
            icon=icon,
        )
        for track in tracklist
    ]
    items.extend(_video_items(release, icon))
    return items
