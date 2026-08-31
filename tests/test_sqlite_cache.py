import time

from sqlite_cache import cached_sqlite


def test_calls_fetch_on_cache_miss():
    calls = []

    def fetch():
        calls.append(1)
        return {"value": 1}

    result = cached_sqlite("key-a", 3600, fetch)

    assert result == {"value": 1}
    assert len(calls) == 1


def test_reuses_cached_value_within_ttl():
    calls = []

    def fetch():
        calls.append(1)
        return {"value": len(calls)}

    first = cached_sqlite("key-b", 3600, fetch)
    second = cached_sqlite("key-b", 3600, fetch)

    assert first == second == {"value": 1}
    assert len(calls) == 1


def test_refetches_after_ttl_expires():
    calls = []

    def fetch():
        calls.append(1)
        return {"value": len(calls)}

    cached_sqlite("key-c", ttl_seconds=0, fetch=fetch)
    time.sleep(0.01)
    cached_sqlite("key-c", ttl_seconds=0, fetch=fetch)

    expected_calls = 2
    assert len(calls) == expected_calls


def test_different_keys_are_cached_independently():
    result_a = cached_sqlite("key-d", 3600, lambda: {"value": "a"})
    result_b = cached_sqlite("key-e", 3600, lambda: {"value": "b"})

    assert result_a == {"value": "a"}
    assert result_b == {"value": "b"}


def test_stale_value_is_overwritten_not_just_refetched():
    cached_sqlite("key-f", ttl_seconds=0, fetch=lambda: {"value": "old"})
    time.sleep(0.01)
    result = cached_sqlite("key-f", ttl_seconds=0, fetch=lambda: {"value": "new"})

    assert result == {"value": "new"}
