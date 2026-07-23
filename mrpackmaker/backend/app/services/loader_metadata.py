"""Resolve Minecraft loader versions from their official metadata sources."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Awaitable, Callable

import httpx

from app.models.enums import LoaderType


class LoaderMetadataError(RuntimeError):
    pass


@dataclass(frozen=True)
class LoaderVersion:
    loader: LoaderType
    minecraft_version: str
    version: str
    source: str
    stable: bool = True


FetchText = Callable[[str], Awaitable[str]]


class OfficialLoaderResolver:
    """Resolver backed only by Fabric Meta and official Forge/NeoForge Maven."""

    def __init__(self, fetch_text: FetchText | None = None) -> None:
        self._fetch_text = fetch_text or self._fetch

    @staticmethod
    async def _fetch(url: str) -> str:
        async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "mrpackmaker/1.0.0"}) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text

    async def list_versions(self, loader: LoaderType, minecraft_version: str) -> tuple[LoaderVersion, ...]:
        if not minecraft_version.strip():
            raise LoaderMetadataError("Minecraft version is required")
        if loader is LoaderType.FABRIC:
            return await self._fabric(minecraft_version)
        if loader is LoaderType.FORGE:
            return await self._forge(minecraft_version)
        if loader is LoaderType.NEOFORGE:
            return await self._neoforge(minecraft_version)
        raise LoaderMetadataError(f"Unsupported loader: {loader.value}")

    async def resolve(self, loader: LoaderType, minecraft_version: str, requested: str | None = None) -> LoaderVersion:
        versions = await self.list_versions(loader, minecraft_version)
        if requested:
            match = next((item for item in versions if item.version == requested), None)
            if match is None:
                raise LoaderMetadataError(f"{requested} is not compatible with Minecraft {minecraft_version}")
            return match
        if not versions:
            raise LoaderMetadataError(f"No {loader.value} version found for Minecraft {minecraft_version}")
        return versions[0]

    async def _fabric(self, mc: str) -> tuple[LoaderVersion, ...]:
        url = f"https://meta.fabricmc.net/v2/versions/loader/{mc}"
        try:
            data = __import__("json").loads(await self._fetch_text(url))
        except (ValueError, httpx.HTTPError) as exc:
            raise LoaderMetadataError("Fabric Meta request failed") from exc
        return tuple(
            LoaderVersion(LoaderType.FABRIC, mc, item["loader"]["version"], "fabric-meta", bool(item["loader"].get("stable", False)))
            for item in data
            if item.get("loader", {}).get("version")
        )

    async def _forge(self, mc: str) -> tuple[LoaderVersion, ...]:
        return self._maven_versions(LoaderType.FORGE, mc, "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml", rf"^{re.escape(mc)}-(?P<version>[^-]+)$", "forge-maven")

    async def _neoforge(self, mc: str) -> tuple[LoaderVersion, ...]:
        # NeoForge's official Maven metadata does not encode Minecraft in every
        # artifact version. The version listing is still sourced from the
        # official repository; callers must verify compatibility before export.
        return self._maven_versions(LoaderType.NEOFORGE, mc, "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml", r"^(?P<version>\d+\.\d+\.\d+.*)$", "neoforge-maven")

    async def _maven_versions(self, loader: LoaderType, mc: str, url: str, pattern: str, source: str) -> tuple[LoaderVersion, ...]:
        try:
            root = ET.fromstring(await self._fetch_text(url))
        except (ET.ParseError, httpx.HTTPError) as exc:
            raise LoaderMetadataError(f"{source} request failed") from exc
        found: list[LoaderVersion] = []
        for element in root.findall(".//version"):
            raw = (element.text or "").strip()
            match = re.match(pattern, raw)
            if match:
                found.append(LoaderVersion(loader, mc, match.group("version"), source, "alpha" not in raw.lower() and "beta" not in raw.lower()))
        return tuple(reversed(found))
