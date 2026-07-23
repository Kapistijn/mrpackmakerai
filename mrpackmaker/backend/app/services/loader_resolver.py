"""Loader version resolution with explicit stable/manual semantics."""

from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import LoaderType
from app.services.modrinth import ModrinthClient


@dataclass(frozen=True)
class LoaderResolution:
    loader: LoaderType
    minecraft_version: str
    version: str | None
    source: str
    stable: bool


class LoaderResolutionError(RuntimeError):
    pass


class LoaderResolver:
    def __init__(self, client: ModrinthClient) -> None:
        self.client = client

    async def resolve(self, loader: LoaderType, minecraft_version: str, requested: str | None = None) -> LoaderResolution:
        project_id = {LoaderType.FABRIC: "fabric-loader", LoaderType.FORGE: "forge", LoaderType.NEOFORGE: "neoforge"}.get(loader)
        if not project_id:
            raise LoaderResolutionError(f"Loader {loader.value} is not supported by this resolver")
        versions = await self.client.get_versions(project_id, minecraft_version, loader)
        if requested:
            match = next((item for item in versions if item.get("version_number") == requested), None)
            if not match:
                raise LoaderResolutionError(f"Loader version {requested} is not compatible with Minecraft {minecraft_version}")
            return LoaderResolution(loader, minecraft_version, requested, "manual", match.get("version_type", "release") == "release")
        stable = [item for item in versions if item.get("version_type", "release") == "release"]
        selected = stable[0] if stable else (versions[0] if versions else None)
        if not selected:
            raise LoaderResolutionError(f"No {loader.value} version found for Minecraft {minecraft_version}")
        return LoaderResolution(loader, minecraft_version, selected.get("version_number"), "latest-stable" if stable else "latest", bool(stable))
