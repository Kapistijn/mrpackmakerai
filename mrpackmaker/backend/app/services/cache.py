"""In-memory TTL + LRU cache for API responses."""

from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Generic, TypeVar

T = TypeVar("T")

DEFAULT_TTL = 300  # 5 minutes
DEFAULT_MAX_ENTRIES = 512


class TTLCache(Generic[T]):
    """A small time-and-size bounded cache.

    Entries expire after ``ttl`` seconds. Independently, the cache never holds
    more than ``max_entries`` items: on insertion the least-recently-used entry
    is evicted. Both bounds matter -- TTL alone let keys that were never read
    again pile up indefinitely, which slowly leaked memory on a long-lived
    server.
    """

    def __init__(self, ttl: int = DEFAULT_TTL, max_entries: int = DEFAULT_MAX_ENTRIES) -> None:
        self._ttl = ttl
        self._max_entries = max(1, max_entries)
        self._store: "OrderedDict[str, tuple[float, T]]" = OrderedDict()

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        # Mark as most-recently-used.
        self._store.move_to_end(key)
        return value

    def set(self, key: str, value: T) -> None:
        now = time.monotonic()
        # Opportunistically drop anything that has already expired so stale
        # entries do not count against the size bound.
        expired = [k for k, (expires_at, _) in self._store.items() if now > expires_at]
        for k in expired:
            del self._store[k]
        self._store[key] = (now + self._ttl, value)
        self._store.move_to_end(key)
        # Enforce the size bound with least-recently-used eviction.
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


search_cache: TTLCache[Any] = TTLCache()
detail_cache: TTLCache[Any] = TTLCache()
