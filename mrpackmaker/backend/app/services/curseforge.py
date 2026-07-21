"""Async CurseForge API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.models.enums import LoaderType, ModSource
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.cache import detail_cache, search_cache

logger = logging.getLogger(__name__)

BASE_URL = "https://api.curseforge.com/v1"
GAME_ID = 432  # Minecraft

LOADER_MAP = {
    LoaderType.FORGE: 1,
    LoaderType.FABRIC: 4,
    LoaderType.NEOFORGE: 6,
}


class CurseForgeClient:
    source_id = "curseforge"

    def __init__(self, api_key: str = "") -> None:
        self._api_key = api_key
        self._available = bool(api_key)
        headers = {"Accept": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    @property
    def available(self) -> bool:
        return self._available

    async def close(self) -> None:
        await self._client.aclose()

    async def search(
        self,
        query: str,
        mc_version: str,
        loader: LoaderType,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ModEntry], int]:
        if not self._available:
            return [], 0

        cache_key = f"curseforge:search:{query}:{mc_version}:{loader}:{category}:{limit}:{offset}"
        cached = search_cache.get(cache_key)
        if cached is not None:
            return cached

        params: dict[str, Any] = {
            "gameId": GAME_ID,
            "searchFilter": query,
            "gameVersion": mc_version,
            "modLoaderType": LOADER_MAP.get(loader, 4),
            "pageSize": limit,
            "index": offset,
            "sortField": 2,
            "sortOrder": "desc",
        }
        if category:
            params["categoryId"] = category

        try:
            resp = await self._client.get("/mods/search", params=params)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            pagination = resp.json().get("pagination", {})
        except httpx.HTTPError as exc:
            logger.error("CurseForge search failed: %s", exc)
            return [], 0

        hits: list[ModEntry] = []
        for mod in data:
            slug = mod.get("slug", "")
            mod_id = str(mod.get("id", ""))
            hits.append(
                ModEntry(
                    id=mod_id,
                    source=ModSource.CURSEFORGE,
                    name=mod.get("name", ""),
                    slug=slug,
                    icon_url=mod.get("logo", {}).get("thumbnailUrl"),
                    summary=mod.get("summary", ""),
                    downloads=mod.get("downloadCount", 0),
                    categories=[c.get("name", "") for c in mod.get("categories", [])],
                    loaders=[loader.value],
                    project_url=f"https://www.curseforge.com/minecraft/mc-mods/{slug}",
                )
            )

        total = pagination.get("totalCount", len(hits))
        result = (hits, total)
        search_cache.set(cache_key, result)
        return result

    async def get_mod(self, mod_id: str) -> dict[str, Any] | None:
        if not self._available:
            return None

        cache_key = f"curseforge:mod:{mod_id}"
        cached = detail_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = await self._client.get(f"/mods/{mod_id}")
            resp.raise_for_status()
            data = resp.json().get("data")
            if data:
                detail_cache.set(cache_key, data)
            return data
        except httpx.HTTPError as exc:
            logger.error("CurseForge get mod failed: %s", exc)
            return None

    async def get_files(
        self,
        mod_id: str,
        mc_version: str,
        loader: LoaderType,
    ) -> list[dict[str, Any]]:
        if not self._available:
            return []

        cache_key = f"curseforge:files:{mod_id}:{mc_version}:{loader}"
        cached = detail_cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "gameVersion": mc_version,
            "modLoaderType": LOADER_MAP.get(loader, 4),
            "pageSize": 10,
        }
        try:
            resp = await self._client.get(f"/mods/{mod_id}/files", params=params)
            resp.raise_for_status()
            data = resp.json().get("data", [])
            detail_cache.set(cache_key, data)
            return data
        except httpx.HTTPError as exc:
            logger.error("CurseForge get files failed: %s", exc)
            return []

    async def get_download_url(self, mod_id: str, file_id: int) -> str | None:
        if not self._available:
            return None

        cache_key = f"curseforge:download:{mod_id}:{file_id}"
        cached = detail_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = await self._client.get(f"/mods/{mod_id}/files/{file_id}/download-url")
            resp.raise_for_status()
            url = resp.json().get("data")
            if url:
                detail_cache.set(cache_key, url)
            return url
        except httpx.HTTPError as exc:
            logger.error("CurseForge download URL failed: %s", exc)
            return None

    async def get_mod_detail(
        self,
        mod_id: str,
        mc_version: str,
        loader: LoaderType,
    ) -> ModEntry | None:
        mod = await self.get_mod(mod_id)
        if not mod:
            return None

        files = await self.get_files(mod_id, mc_version, loader)
        if not files:
            return None

        file_data = files[0]
        file_id = file_data.get("id", 0)
        download_url = await self.get_download_url(mod_id, file_id)

        deps: list[ModDependency] = []
        for dep in file_data.get("dependencies", []):
            dep_mod_id = dep.get("modId")
            if dep_mod_id:
                deps.append(
                    ModDependency(
                        project_id=str(dep_mod_id),
                        dependency_type="required" if dep.get("relationType") == 3 else "optional",
                        source=ModSource.CURSEFORGE,
                    )
                )

        hashes = file_data.get("hashes", [])
        sha1 = next((h["value"] for h in hashes if h.get("algo") == 1), None)
        sha512 = next((h["value"] for h in hashes if h.get("algo") == 2), None)

        slug = mod.get("slug", "")
        return ModEntry(
            id=str(mod.get("id", mod_id)),
            source=ModSource.CURSEFORGE,
            name=mod.get("name", ""),
            slug=slug,
            icon_url=mod.get("logo", {}).get("thumbnailUrl"),
            summary=mod.get("summary", ""),
            downloads=mod.get("downloadCount", 0),
            categories=[c.get("name", "") for c in mod.get("categories", [])],
            loaders=[loader.value],
            dependencies=deps,
            project_url=f"https://www.curseforge.com/minecraft/mc-mods/{slug}",
            selected_version=file_data.get("displayName"),
            version_id=str(file_id),
            file_id=file_id,
            file_name=file_data.get("fileName"),
            file_size=file_data.get("fileLength"),
            download_url=download_url,
            hashes=ModHash(sha1=sha1, sha512=sha512),
        )
