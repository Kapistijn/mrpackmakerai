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
MOD_CLASS_ID = 6  # Minecraft > Mods (excludes resource packs, worlds, plugins)

LOADER_MAP = {
    LoaderType.FORGE: 1,
    LoaderType.FABRIC: 4,
    LoaderType.NEOFORGE: 6,
}


def _newest(files: list[dict[str, Any]]) -> dict[str, Any]:
    # Newest first by ISO fileDate; empty dates sort last.
    return sorted(files, key=lambda f: f.get("fileDate", ""), reverse=True)[0]


def _pick_best_file(
    files: list[dict[str, Any]], mc_version: str, loader: LoaderType
) -> dict[str, Any] | None:
    """Choose the newest file that actually matches the MC version AND loader.

    CurseForge's ``gameVersion``/``modLoaderType`` query is a coarse pre-filter,
    so ``files[0]`` can still be a wrong-loader or older build. We select in
    tiers so the most precise match always wins:

    1. Files whose own ``gameVersions`` list contains both the MC version and
       the loader name (the ideal, unambiguous match).
    2. Failing that, files that at least match the MC version -- this avoids
       shipping a jar built for a different Minecraft version just because its
       loader label was missing from the list.
    3. Only as a last resort do we trust the API's coarse pre-filter and take
       the newest returned file.
    """
    if not files:
        return None
    loader_name = loader.value.lower()
    mc = mc_version.lower()

    def versions_of(file_data: dict[str, Any]) -> list[str]:
        return [str(v).lower() for v in file_data.get("gameVersions", [])]

    exact = [f for f in files if mc in versions_of(f) and loader_name in versions_of(f)]
    if exact:
        return _newest(exact)
    version_only = [f for f in files if mc in versions_of(f)]
    if version_only:
        return _newest(version_only)
    return _newest(files)


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
            # Restrict to actual mods; without classId the search also returns
            # modpacks, resource packs, worlds and Bukkit plugins.
            "classId": MOD_CLASS_ID,
            "searchFilter": query,
            "gameVersion": mc_version,
            "modLoaderType": LOADER_MAP.get(loader, 4),
            "pageSize": limit,
            "index": offset,
            "sortField": 2,  # Popularity
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
                    icon_url=mod.get("logo", {}).get("thumbnailUrl") if mod.get("logo") else None,
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
            "pageSize": 50,
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
        file_data = _pick_best_file(files, mc_version, loader)
        if not file_data:
            return None

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
            icon_url=mod.get("logo", {}).get("thumbnailUrl") if mod.get("logo") else None,
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
