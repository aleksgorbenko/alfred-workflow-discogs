import json
import os
import sys
from typing import Any

import browse
import discogs_api
import names
import router
import search
import tracklist
from alfred_items import HINT_HEADER, error_item, item, with_hint
from async_view import finish, job_command, serve, settle
from cache import cache_dir
from discogs_api import DiscogsError
from router import Route

DISCOGS_BASE = "https://www.discogs.com"
SETUP_HINT = "Set your Discogs API Token in the workflow configuration"

Row = dict[str, Any]


def _header(title: str, subtitle: str, route: Route, ref: router.Ref) -> Row:
    return item(
        title=title,
        subtitle=with_hint(subtitle, HINT_HEADER),
        arg=f"{DISCOGS_BASE}/{ref[0]}/{ref[1]}",
        autocomplete=router.path(route.names[:-1]),
    )


def _filtered(rows: list[Row], text: str, kind: str) -> list[Row]:
    if not text:
        return rows
    kept = [row for row in rows if router.matches(text, row["title"])]
    return kept or [item(title=f"No {kind} matches '{text}'", valid=False)]


def _search(text: str, token: str) -> list[Row]:
    if not text:
        return [item(title="Type to search Discogs…", valid=False)]
    return search.build_items(discogs_api.search(text, token), token)


def _lookup(refs: list[router.Ref], name: str, token: str) -> router.Ref:
    if not refs:
        found = search.named(discogs_api.search(name, token))
    elif refs[-1][0] == "release":
        found = []
    else:
        kind, entity = refs[-1]
        found = browse.named(kind, browse.fetch(kind, entity, token))
    for _entry, label, ref in found:
        if label.casefold() == name.casefold():
            return ref
    if not refs and found:
        return found[0][2]
    msg = f"Could not find '{name}' on Discogs"
    raise DiscogsError(msg)


def _resolve(route: Route, token: str) -> list[router.Ref]:
    refs: list[router.Ref] = []
    for depth, name in enumerate(route.names):
        stored = names.recall(names.path_key(route.names[: depth + 1]))
        kind, _, entity = stored.partition("/")
        refs.append((kind, entity) if entity else _lookup(refs, name, token))
    return refs


def _releases(route: Route, refs: list[router.Ref], token: str) -> list[Row]:
    kind, entity = refs[-1]
    entries = browse.fetch(kind, entity, token)
    rows = browse.build_items(kind, entries, token, route.names)
    header = _header(route.names[-1], kind.title(), route, refs[-1])
    return [header, *_filtered(rows, route.text, "release")]


def _tracks(route: Route, refs: list[router.Ref], token: str) -> list[Row]:
    release = discogs_api.get_release(refs[-1][1], token)
    rows = tracklist.build_items(release)
    credited: list[dict[str, Any]] = release.get("artists") or []
    artists = ", ".join(str(artist.get("name", "")) for artist in credited)
    header = _header(route.names[-1], artists, route, refs[-1])
    return [header, *_filtered(rows, route.text, "track")]


def run(query: str, token: str) -> list[Row]:
    if not token:
        return [error_item(SETUP_HINT)]
    route = router.parse(query.strip())
    if not route.names:
        return _search(route.text, token)
    refs = _resolve(route, token)
    if refs[-1][0] == "release":
        return _tracks(route, refs, token)
    return _releases(route, refs, token)


def loading_label(query: str) -> str:
    route = router.parse(query.strip())
    if not route.names:
        return f"Searching Discogs for '{route.text}'…"
    return f"Loading {route.names[-1]}…"


def _payload(query: str, token: str) -> dict[str, Any]:
    try:
        return {"items": run(query, token)}
    except DiscogsError as error:
        return {"items": [error_item(str(error))]}


def _job(query: str, token: str) -> None:
    if not settle(cache_dir(), query):
        return
    try:
        payload = _payload(query, token)
    except Exception as error:  # noqa: BLE001
        payload = {"items": [error_item(str(error))]}
    finish(cache_dir(), query, payload)


def main(argv: list[str]) -> None:
    token = os.environ.get("DISCOGS_API_TOKEN", "")
    if argv[:1] == ["--job"]:
        _job(argv[1] if len(argv) > 1 else "", token)
        return
    query = argv[0] if argv else ""
    payload = (
        serve(
            query,
            directory=cache_dir(),
            command=job_command(__file__, query),
            label=loading_label(query),
        )
        if query.strip() and token
        else _payload(query, token)
    )
    json.dump(payload, sys.stdout, ensure_ascii=False)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
