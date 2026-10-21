import time

from cache import cached


def test_calls_fetch_on_cache_miss() -> None:
    calls: list[int] = []

    def fetch() -> dict[str, int]:
        calls.append(1)
        return {"value": 1}

    result = cached("key-a", 3600, fetch)

    assert result == {"value": 1}
    assert len(calls) == 1


def test_reuses_cached_value_within_ttl() -> None:
    calls: list[int] = []

    def fetch() -> dict[str, int]:
        calls.append(1)
        return {"value": len(calls)}

    first = cached("key-b", 3600, fetch)
    second = cached("key-b", 3600, fetch)

    assert first == second == {"value": 1}
    assert len(calls) == 1


def test_refetches_after_ttl_expires() -> None:
    calls: list[int] = []

    def fetch() -> dict[str, int]:
        calls.append(1)
        return {"value": len(calls)}

    cached("key-c", ttl_seconds=0, fetch=fetch)
    time.sleep(0.01)
    cached("key-c", ttl_seconds=0, fetch=fetch)

    expected_calls = 2
    assert len(calls) == expected_calls


def test_different_keys_are_cached_independently() -> None:
    result_a = cached("key-d", 3600, lambda: {"value": "a"})
    result_b = cached("key-e", 3600, lambda: {"value": "b"})

    assert result_a == {"value": "a"}
    assert result_b == {"value": "b"}
