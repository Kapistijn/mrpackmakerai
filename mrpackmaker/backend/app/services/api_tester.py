"""Connection tests for the Modrinth and CurseForge APIs.

Each test uses a live, cheap request, measures latency and maps common failures
(bad key, unreachable host) to an actionable message.  Keys come from the
encrypted config; they are never returned to the caller.
"""

from __future__ import annotations

import time

import httpx

from app.schemas.settings import ApiTestResult
from app.services.curseforge import BASE_URL as CF_BASE_URL, GAME_ID
from app.services.modrinth import BASE_URL as MR_BASE_URL, USER_AGENT


async def test_modrinth(api_key: str) -> ApiTestResult:
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = api_key
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=MR_BASE_URL, headers=headers, timeout=15.0) as client:
            resp = await client.get("/search", params={"limit": 1, "query": "sodium"})
            latency = int((time.monotonic() - start) * 1000)
            resp.raise_for_status()
            data = resp.json()
        return ApiTestResult(
            ok=True,
            service="modrinth",
            status_code=200,
            latency_ms=latency,
            detail="Modrinth API works",
            info={"mods_found": str(data.get("total_hits", 0))},
        )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        reason = "Invalid API key" if code in (401, 403) else f"HTTP {code}"
        return ApiTestResult(ok=False, service="modrinth", status_code=code, detail=reason)
    except httpx.HTTPError as exc:
        return ApiTestResult(ok=False, service="modrinth", detail=f"Could not reach Modrinth: {exc}")


async def test_curseforge(api_key: str) -> ApiTestResult:
    if not api_key:
        return ApiTestResult(
            ok=False,
            service="curseforge",
            detail="No CurseForge API key configured. Enter one and save first.",
        )
    headers = {"Accept": "application/json", "x-api-key": api_key}
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(base_url=CF_BASE_URL, headers=headers, timeout=15.0) as client:
            # Listing the Minecraft categories is a light, auth-protected call.
            resp = await client.get("/categories", params={"gameId": GAME_ID})
            latency = int((time.monotonic() - start) * 1000)
            resp.raise_for_status()
            data = resp.json()
        return ApiTestResult(
            ok=True,
            service="curseforge",
            status_code=200,
            latency_ms=latency,
            detail="CurseForge API works",
            info={"categories": str(len(data.get("data", [])))},
        )
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        reason = "Invalid API key" if code in (401, 403) else f"HTTP {code}"
        return ApiTestResult(ok=False, service="curseforge", status_code=code, detail=reason)
    except httpx.HTTPError as exc:
        return ApiTestResult(ok=False, service="curseforge", detail=f"Could not reach CurseForge: {exc}")
