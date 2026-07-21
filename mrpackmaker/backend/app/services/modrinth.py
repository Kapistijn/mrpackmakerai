"""Async Modrinth API client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.models.enums import LoaderType, ModSource
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.cache import detail_cache, search_cache

logger = logging.getLogger(__name__)

BASE_URL = "https://api.modrinth.com/v2"
USER_AGENT = "mrpackmaker/1.0.0 (local-app)"


class ModrinthClient:
    source_id = "modrinth"

    def __init__(self, api_key: str = "") -> None:
        headers = {"User-Agent": USER_AGENT}
        if api_key:
            headers["Authorization"] = api_key
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers=headers,
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    @property
    def available(self) -> bool:
        # Modrinth's public API does not need a token; a token only raises rate
        # limits for deployments that have one.
        return True

    async def search(
        self,
        query: str,
        mc_version: str,
        loader: LoaderType,
        category: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[ModEntry], int]:
        cache_key = f"modrinth:search:{query}:{mc_version}:{loader}:{category}:{limit}:{offset}"
        cached = search_cache.get(cache_key)
        if cached is not None:
            return cached

        facets: list[str] = [
            '["project_type:mod"]',
            f'["versions:{mc_version}"]',
            f'["loaders:{loader.value}"]',
        ]
        if category:
            facets.append(f'["categories:{category}"]')

        params: dict[str, Any] = {
            "query": query,
            "facets": facets,
            "limit": limit,
            "offset": offset,
            "index": "relevance",
        }

        try:
            resp = await self._client.get("/search", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Modrinth search failed: %s", exc)
            return [], 0

        hits: list[ModEntry] = []
        for hit in data.get("hits", []):
            hits.append(
                ModEntry(
                    id=hit.get("project_id", hit.get("slug", "")),
                    source=ModSource.MODRINTH,
                    name=hit.get("title", ""),
                    slug=hit.get("slug", ""),
                    icon_url=hit.get("icon_url"),
                    summary=hit.get("description", ""),
                    downloads=hit.get("downloads", 0),
                    categories=hit.get("categories", []),
                    loaders=hit.get("loaders", []),
                    project_url=f"https://modrinth.com/mod/{hit.get('slug', '')}",
                )
            )

        total = data.get("total_hits", len(hits))
        result = (hits, total)
        search_cache.set(cache_key, result)
        return result

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        cache_key = f"modrinth:project:{project_id}"
        cached = detail_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = await self._client.get(f"/project/{project_id}")
            resp.raise_for_status()
            data = resp.json()
            detail_cache.set(cache_key, data)
            return data
        except httpx.HTTPError as exc:
            logger.error("Modrinth get project failed: %s", exc)
            return None

    async def get_versions(
        self,
        project_id: str,
        mc_version: str,
        loader: LoaderType,
    ) -> list[dict[str, Any]]:
        cache_key = f"modrinth:versions:{project_id}:{mc_version}:{loader}"
        cached = detail_cache.get(cache_key)
        if cached is not None:
            return cached

        params = {"loaders": json_dumps([loader.value]), "game_versions": json_dumps([mc_version])}
        try:
            resp = await self._client.get(f"/project/{project_id}/version", params=params)
            resp.raise_for_status()
            data = resp.json()
            detail_cache.set(cache_key, data)
            return data
        except httpx.HTTPError as exc:
            logger.error("Modrinth get versions failed: %s", exc)
            return []

    async def get_version(self, version_id: str) -> dict[str, Any] | None:
        cache_key = f"modrinth:version:{version_id}"
        cached = detail_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            resp = await self._client.get(f"/version/{version_id}")
            resp.raise_for_status()
            data = resp.json()
            detail_cache.set(cache_key, data)
            return data
        except httpx.HTTPError as exc:
            logger.error("Modrinth get version failed: %s", exc)
            return None

    async def get_mod_detail(
        self,
        project_id: str,
        mc_version: str,
        loader: LoaderType,
    ) -> ModEntry | None:
        project = await self.get_project(project_id)
        if not project:
            return None

        versions = await self.get_versions(project_id, mc_version, loader)
        if not versions:
            return None

        version = versions[0]
        version_id = version.get("id", "")
        files = version.get("files", [])
        primary_file = files[0] if files else {}
        hashes_raw = primary_file.get("hashes", {})

        deps: list[ModDependency] = []
        for dep in version.get("dependencies", []):
            deps.append(
                ModDependency(
                    project_id=dep.get("project_id") or dep.get("version_id", ""),
                    dependency_type=dep.get("dependency_type", "required"),
                    source=ModSource.MODRINTH,
                )
            )

        return ModEntry(
            id=project.get("id", project_id),
            source=ModSource.MODRINTH,
            name=project.get("title", ""),
            slug=project.get("slug", ""),
            icon_url=project.get("icon_url"),
            summary=project.get("description", ""),
            downloads=project.get("downloads", 0),
            categories=project.get("categories", []),
            loaders=version.get("loaders", []),
            dependencies=deps,
            project_url=f"https://modrinth.com/mod/{project.get('slug', '')}",
            selected_version=version.get("version_number"),
            version_id=version_id,
            file_name=primary_file.get("filename"),
            file_size=primary_file.get("size"),
            download_url=primary_file.get("url"),
            hashes=ModHash(
                sha1=hashes_raw.get("sha1"),
                sha512=hashes_raw.get("sha512"),
            ),
        )

    async def search_loader_version(self, loader: LoaderType, mc_version: str) -> str | None:
        loader_project_map = {
            LoaderType.FABRIC: "fabric-loader",
            LoaderType.FORGE: "forge",
            LoaderType.NEOFORGE: "neoforge",
        }
        project_id = loader_project_map.get(loader)
        if not project_id:
            return None

        versions = await self.get_versions(project_id, mc_version, loader)
        if not versions:
            return None
        return versions[0].get("version_number")


def json_dumps(obj: Any) -> str:
    import json
    return json.dumps(obj)
