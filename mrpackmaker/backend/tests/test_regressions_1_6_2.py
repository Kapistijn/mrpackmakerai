"""Regression tests for the fixes shipped in 1.6.2.

These are intentionally dependency-light: they exercise pure helpers so they
run without a network connection, an AI provider or a database.
"""

from __future__ import annotations

import time

from app.models.enums import LoaderType
from app.services.cache import TTLCache
from app.services.curseforge import _pick_best_file


def test_pick_best_file_prefers_exact_version_and_loader():
    files = [
        {"id": 1, "gameVersions": ["1.19.2", "Forge"], "fileDate": "2024-01-01"},
        {"id": 2, "gameVersions": ["1.20.1", "Forge"], "fileDate": "2023-06-01"},
        {"id": 3, "gameVersions": ["1.20.1", "Fabric"], "fileDate": "2025-01-01"},
    ]
    best = _pick_best_file(files, "1.20.1", LoaderType.FORGE)
    assert best is not None and best["id"] == 2


def test_pick_best_file_falls_back_to_version_only_before_anything():
    # No file lists the loader, but one matches the requested MC version. That
    # must win over a newer file for a different version.
    files = [
        {"id": 1, "gameVersions": ["1.19.2"], "fileDate": "2025-01-01"},
        {"id": 2, "gameVersions": ["1.20.1"], "fileDate": "2024-01-01"},
    ]
    best = _pick_best_file(files, "1.20.1", LoaderType.FORGE)
    assert best is not None and best["id"] == 2


def test_pick_best_file_empty_returns_none():
    assert _pick_best_file([], "1.20.1", LoaderType.FORGE) is None


def test_ttl_cache_evicts_least_recently_used():
    cache: TTLCache[int] = TTLCache(ttl=60, max_entries=2)
    cache.set("a", 1)
    cache.set("b", 2)
    # Touch "a" so "b" becomes the least recently used.
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("a") == 1
    assert cache.get("c") == 3


def test_ttl_cache_expires_entries():
    cache: TTLCache[int] = TTLCache(ttl=0, max_entries=8)
    cache.set("a", 1)
    time.sleep(0.01)
    assert cache.get("a") is None
