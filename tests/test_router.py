import router
from router import Route


def test_plain_text_is_a_search() -> None:
    assert router.parse("aphex twin") == Route(text="aphex twin")


def test_parse_a_page_with_a_filter() -> None:
    assert router.parse("Aphex Twin > ambient") == Route(
        names=("Aphex Twin",), text="ambient"
    )


def test_parse_nested_pages() -> None:
    parsed = router.parse("Aphex Twin > Drukqs > ")
    assert parsed == Route(names=("Aphex Twin", "Drukqs"), text="")


def test_path_and_drill_build_readable_paths() -> None:
    assert router.path(()) == ""
    assert router.path(("A", "B")) == "A > B > "
    assert router.drill("", "Label") == "Label > "
    assert router.drill("A > ", "B > C") == "A > B - C > "


def test_unique_qualifies_repeated_titles() -> None:
    assert router.unique([("Nevermind", "1991, US"), ("Nevermind", "1992, UK")]) == [
        "Nevermind (1991, US)",
        "Nevermind (1992, UK)",
    ]
    assert router.unique([("A", ""), ("A", "")]) == ["A", "A #2"]
    assert router.unique([("A", "x"), ("B", "x")]) == ["A", "B"]


def test_matches_requires_every_word() -> None:
    assert router.matches("ONE two", "Track one and Two")
    assert not router.matches("one three", "Track one and Two")
