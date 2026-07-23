"""Resolve Minecraft loader versions from their official metadata sources."""

from __future__ import annotations

import json
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
        try:
            async with httpx.AsyncClient(timeout=30.0, headers={"User-Agent": "mrpackmaker/1.0.0"}) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except httpx.HTTPError as exc:
            raise LoaderMetadataError(f"Loader metadata request failed: {url}") from exc

    async def list_versions(self, loader: LoaderType, minecraft_version: str) -> tuple[LoaderVersion, ...]:
        try:
            loader = loader if isinstance(loader, LoaderType) else LoaderType(str(loader).lower())
        except ValueError as exc:
            raise LoaderMetadataError(f"Unsupported loader: {loader}") from exc
        mc = minecraft_version.strip()
        if not mc:
            raise LoaderMetadataError("Minecraft version is required")
        if loader is LoaderType.FABRIC:
            return await self._fabric(mc)
        if loader is LoaderType.FORGE:
            return await self._forge(mc)
        if loader is LoaderType.NEOFORGE:
            return await self._neoforge(mc)
        raise LoaderMetadataError(f"Unsupported loader: {loader.value}")

    async def resolve(self, loader: LoaderType, minecraft_version: str, requested: str | None = None) -> LoaderVersion:
        versions = await self.list_versions(loader, minecraft_version)
        requested_version = requested.strip() if requested else None
        if requested_version:
            match = next((item for item in versions if item.version == requested_version), None)
            if match is None:
                raise LoaderMetadataError(f"{requested_version} is not compatible with Minecraft {minecraft_version}")
            return match
        if not versions:
            raise LoaderMetadataError(f"No {loader.value} version found for Minecraft {minecraft_version}")
        return versions[0]

    async def _fabric(self, mc: str) -> tuple[LoaderVersion, ...]:
        url = f"https://meta.fabricmc.net/v2/versions/loader/{mc}"
        try:
            data = json.loads(await self._fetch_text(url))
            if not isinstance(data, list):
                raise ValueError("Fabric metadata must be a list")
            return tuple(
                LoaderVersion(LoaderType.FABRIC, mc, item["loader"]["version"], "fabric-meta", bool(item["loader"].get("stable", False)))
                for item in data
                if isinstance(item, dict) and isinstance(item.get("loader"), dict) and item["loader"].get("version")
            )
        except (ValueError, TypeError, KeyError, json.JSONDecodeError, LoaderMetadataError) as exc:
            raise LoaderMetadataError("Fabric Meta request failed") from exc

    async def _forge(self, mc: str) -> tuple[LoaderVersion, ...]:
        return await self._maven_versions(
            LoaderType.FORGE,
            mc,
            "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml",
            rf"^{re.escape(mc)}-(?P<version>[^-]+)$",
            "forge-maven",
        )

    async def _neoforge(self, mc: str) -> tuple[LoaderVersion, ...]:
        # NeoForge's official Maven metadata does not encode Minecraft in every
        # artifact version. The version listing is sourced from the official
        # repository; compatibility is enforced by the selected project/version.
        return await self._maven_versions(
            LoaderType.NEOFORGE,
            mc,
            "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml",
            r"^(?P<version>\d+\.\d+\.\d+.*)$",
            "neoforge-maven",
        )

    async def _maven_versions(self, loader: LoaderType, mc: str, url: str, pattern: str, source: str) -> tuple[LoaderVersion, ...]:
        try:
            root = ET.fromstring(await self._fetch_text(url))
        except (ET.ParseError, LoaderMetadataError) as exc:
            raise LoaderMetadataError(f"{source} request failed") from exc
        found: list[LoaderVersion] = []
        for element in root.findall(".//version"):
            raw = (element.text or "").strip()
            match = re.fullmatch(pattern, raw)
            if match:
                found.append(LoaderVersion(loader, mc, match.group("version"), source, "alpha" not in raw.lower() and "beta" not in raw.lower()))
        return tuple(reversed(found))
