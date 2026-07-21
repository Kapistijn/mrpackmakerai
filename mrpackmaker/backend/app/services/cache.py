"""In-memory TTL cache for API responses."""

from __future__ import annotations

import time
from typing import Any, Generic, TypeVar

T = TypeVar("T")

DEFAULT_TTL = 300  # 5 minutes


class TTLCache(Generic[T]):
    def __init__(self, ttl: int = DEFAULT_TTL) -> None:
        self._ttl = ttl
        self._store: dict[str, tuple[float, T]] = {}

    def get(self, key: str) -> T | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: T) -> None:
        self._store[key] = (time.monotonic() + self._ttl, value)

    def clear(self) -> None:
        self._store.clear()


search_cache: TTLCache[Any] = TTLCache()
detail_cache: TTLCache[Any] = TTLCache()
