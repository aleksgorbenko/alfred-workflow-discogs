from collections import Counter
from dataclasses import dataclass

SEPARATOR = ">"

Ref = tuple[str, str]


@dataclass(frozen=True)
class Route:
    names: tuple[str, ...] = ()
    text: str = ""


def clean(name: str) -> str:
    return " ".join(name.replace(SEPARATOR, "-").split())


def parse(query: str) -> Route:
    parts = [part.strip() for part in query.split(SEPARATOR)]
    path = tuple(part for part in parts[:-1] if part)
    if not path:
        return Route(text=query.strip())
    return Route(names=path, text=parts[-1])


def path(names: tuple[str, ...]) -> str:
    return "".join(f"{clean(name)} {SEPARATOR} " for name in names)


def drill(current: str, name: str) -> str:
    return f"{current}{clean(name)} {SEPARATOR} "


def unique(entries: list[tuple[str, str]]) -> list[str]:
    totals = Counter(clean(title).casefold() for title, _ in entries)
    seen: Counter[str] = Counter()
    result: list[str] = []
    for title, qualifier in entries:
        name = clean(title)
        if totals[name.casefold()] > 1 and qualifier:
            name = f"{name} ({clean(qualifier)})"
        seen[name.casefold()] += 1
        if seen[name.casefold()] > 1:
            name = f"{name} #{seen[name.casefold()]}"
        result.append(name)
    return result


def matches(text: str, title: str) -> bool:
    words = text.lower().split()
    haystack = title.lower()
    return all(word in haystack for word in words)
