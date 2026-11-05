from typing import Any

OPEN_LABEL = "Open in browser"
HINT_OPEN = f"⌥↩ {OPEN_LABEL}"
HINT_HEADER = f"↩ {OPEN_LABEL}"

TYPE_ICONS = {
    "release": "icons/icon_release.png",
    "master": "icons/icon_master.png",
    "artist": "icons/icon_artist.png",
    "label": "icons/icon_label.png",
}


def item(  # noqa: PLR0913
    title: str,
    *,
    subtitle: str = "",
    arg: str | None = None,
    valid: bool = True,
    icon: str | None = None,
    variables: dict[str, str] | None = None,
    autocomplete: str | None = None,
    mods: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {"title": title, "subtitle": subtitle, "valid": valid}
    if arg is not None:
        result["arg"] = arg
    if icon is not None:
        result["icon"] = {"path": icon}
    if variables is not None:
        result["variables"] = variables
    if autocomplete is not None:
        result["autocomplete"] = autocomplete
    if mods is not None:
        result["mods"] = mods
    return result


def with_hint(subtitle: str, hint: str) -> str:
    return f"{subtitle} · {hint}" if subtitle else hint


def open_mod(url: str) -> dict[str, dict[str, Any]]:
    return {"alt": {"valid": True, "arg": url, "subtitle": OPEN_LABEL}}


def error_item(message: str) -> dict[str, Any]:
    return item(title=message, valid=False)
