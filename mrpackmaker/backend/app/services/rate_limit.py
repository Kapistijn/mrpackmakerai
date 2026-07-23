"""Shared async request throttling for public catalog APIs."""
from __future__ import annotations
import asyncio
import random
import time
from collections.abc import Awaitable, Callable
import httpx

class CatalogRateLimiter:
    """Application-wide limiter with a retry count and hard per-request deadline."""
    def __init__(self, concurrency: int = 4, min_interval: float = 0.12, retries: int = 3, max_seconds: float = 20.0) -> None:
        self._semaphore = asyncio.Semaphore(concurrency)
        self._min_interval = min_interval
        self._retries = retries
        self._max_seconds = max_seconds
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    async def run(self, request: Callable[[], Awaitable[httpx.Response]]) -> httpx.Response:
        async with self._semaphore:
            started = time.monotonic()
            for attempt in range(self._retries + 1):
                remaining = self._max_seconds - (time.monotonic() - started)
                if remaining <= 0:
                    raise TimeoutError("Catalog request retry budget exceeded")
                async with self._lock:
                    loop = asyncio.get_running_loop()
                    wait = self._min_interval - (loop.time() - self._last_request)
                    if wait > 0:
                        await asyncio.sleep(min(wait, remaining))
                    self._last_request = loop.time()
                response = await asyncio.wait_for(request(), timeout=remaining)
                if response.status_code != 429:
                    return response
                retry_after = response.headers.get("Retry-After")
                try:
                    server_wait = float(retry_after) if retry_after else 0.0
                except ValueError:
                    server_wait = 0.0
                backoff = min(8.0, 0.5 * (2 ** attempt)) + random.uniform(0.0, 0.25)
                delay = max(server_wait, backoff)
                if attempt >= self._retries or time.monotonic() - started + delay >= self._max_seconds:
                    return response
                await asyncio.sleep(delay)
            return response

modrinth_limiter = CatalogRateLimiter(concurrency=3, min_interval=0.18, retries=3, max_seconds=20.0)
