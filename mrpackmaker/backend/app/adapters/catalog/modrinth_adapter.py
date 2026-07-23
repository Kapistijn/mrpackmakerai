from __future__ import annotations

from app.adapters.errors import InvalidResponseError
from app.domain.common import Environment, Loader, ModSource
from app.domain.mods.models import CanonicalModIdentity, ModCandidate, ModFile
from app.domain.providers.protocols import ModrinthProvider
from app.models.enums import LoaderType
from app.schemas.mod import ModEntry
from app.services.modrinth import ModrinthClient


class ModrinthAdapter:
    """Translate the existing ModrinthClient DTOs into domain candidates."""

    def __init__(self, client: ModrinthClient, minecraft_version: str, loader: Loader) -> None:
        self._client = client
        self._minecraft_version = minecraft_version
        self._loader = loader

    @property
    def client(self) -> ModrinthClient:
        return self._client

    @staticmethod
    def _loader_type(loader: Loader) -> LoaderType:
        try:
            return LoaderType(loader.value)
        except ValueError as exc:
            raise InvalidResponseError(f"Unsupported Modrinth loader: {loader.value}") from exc

    @staticmethod
    def _file(entry: ModEntry) -> ModFile:
        if not entry.file_name or not entry.download_url or not entry.hashes.sha512:
            raise InvalidResponseError("Modrinth response is missing file name, URL, or sha512")
        return ModFile(
            filename=entry.file_name,
            url=entry.download_url,
            sha512=entry.hashes.sha512,
            size_bytes=entry.file_size or 0,
            minecraft_versions=frozenset({entry.selected_version or ""}) - {""},
            loaders=frozenset(entry.loaders),
        )

    @staticmethod
    def _candidate(entry: ModEntry, *, require_file: bool = False) -> ModCandidate:
        if not entry.id or not entry.name:
            raise InvalidResponseError("Modrinth response is missing id or name")
        files = ()
        if require_file:
            files = (ModrinthAdapter._file(entry),)
        elif entry.file_name:
            files = (ModrinthAdapter._file(entry),)
        identity = CanonicalModIdentity(
            canonical_key=f"modrinth:{entry.id}",
            display_name=entry.name,
            sources={ModSource.MODRINTH: entry.id},
            aliases=frozenset({entry.slug}) if entry.slug else frozenset(),
        )
        return ModCandidate(
            identity=identity,
            source=ModSource.MODRINTH,
            project_id=entry.id,
            slug=entry.slug,
            name=entry.name,
            description=entry.summary,
            downloads=entry.downloads,
            categories=frozenset(entry.categories),
            files=files,
            client_side=Environment.UNKNOWN,
            server_side=Environment.UNKNOWN,
        )

    async def search(self, query: str, *, minecraft_version: str, loader: Loader, limit: int = 50, offset: int = 0) -> tuple[ModCandidate, ...]:
        hits, _ = await self._client.search(query, minecraft_version, self._loader_type(loader), limit=limit, offset=offset)
        return tuple(self._candidate(hit) for hit in hits)

    async def get(self, project_id: str) -> ModCandidate | None:
        entry = await self._client.get_mod_detail(project_id, self._minecraft_version, self._loader_type(self._loader))
        return self._candidate(entry, require_file=True) if entry is not None else None
