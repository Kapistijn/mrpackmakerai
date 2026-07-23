"""Shared async request throttling for public catalog APIs."""
from __future__ import annotations
import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar
import httpx
T = TypeVar("T")

class CatalogRateLimiter:
    def __init__(self, concurrency: int = 4, min_interval: float = 0.12, retries: int = 4) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._min_interval = min_interval
        self._retries = retries
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def run(self, request: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response:
        async with self._semaphore:
            for attempt in range(self._retries + 1):
                async with self._lock:
                    loop = asyncio.get_running_loop()
                    wait = self._min_interval - (loop.time() - self._last_request)
                    if wait > 0:
                        await asyncio.sleep(wait)
                    self._last_request = loop.time()
                response = await request()
                if response.status_code != 429:
                    return response
                retry_after = response.headers.get("Retry-After")
                try:
                    server_wait = float(retry_after) if retry_after else 0.0
                except ValueError:
                    server_wait = 0.0
                delay = max(server_wait, min(8.0, 0.5 * (2 ** attempt))) + random.uniform(0.0, 0.25)
                if attempt >= self._retries:
                    return response
                await asyncio.sleep(delay)
            return response

modrinth_limiter = CatalogRateLimiter(concurrency=3, min_interval=0.18, retries=4)
