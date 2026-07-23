from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from app.domain.common import Environment, FrozenMap, ModSource


@dataclass(frozen=True, eq=False)
class CanonicalModIdentity:
    canonical_key: str
    display_name: str
    sources: Mapping[ModSource, str] = field(default_factory=dict)
    aliases: frozenset[str] = field(default_factory=frozenset)
    authors: frozenset[str] = field(default_factory=frozenset)
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.canonical_key.strip() or not 0 <= self.confidence <= 1:
            raise ValueError("invalid canonical identity")
        object.__setattr__(self, "canonical_key", self.canonical_key.strip().lower())
        object.__setattr__(self, "aliases", frozenset(str(x).strip().lower() for x in self.aliases))
        object.__setattr__(self, "authors", frozenset(str(x).strip().lower() for x in self.authors))
        object.__setattr__(self, "sources", FrozenMap.from_mapping({str(k): str(v) for k, v in self.sources.items()}))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CanonicalModIdentity) and self.canonical_key == other.canonical_key

    def __hash__(self) -> int:
        return hash(self.canonical_key)

    def matches(self, other: "CanonicalModIdentity") -> bool:
        return self.canonical_key == other.canonical_key or bool(self.aliases & ({other.canonical_key} | other.aliases)) or any(src in other.sources and other.sources[src] == project_id for src, project_id in self.sources.items())

    def to_dict(self) -> dict[str, object]:
        return {"canonical_key": self.canonical_key, "display_name": self.display_name, "sources": self.sources.to_dict(), "aliases": sorted(self.aliases), "authors": sorted(self.authors), "confidence": self.confidence}


@dataclass(frozen=True)
class ModFile:
    filename: str
    url: str
    sha512: str
    size_bytes: int
    minecraft_versions: frozenset[str]
    loaders: frozenset[str]

    def __post_init__(self) -> None:
        if not self.filename.strip() or not self.url.strip() or not self.sha512.strip() or self.size_bytes < 0:
            raise ValueError("invalid mod file")
        object.__setattr__(self, "minecraft_versions", frozenset(self.minecraft_versions))
        object.__setattr__(self, "loaders", frozenset(str(x).lower() for x in self.loaders))

    def supports(self, minecraft_version: str, loader: str) -> bool:
        return minecraft_version in self.minecraft_versions and loader.lower() in self.loaders

    def to_dict(self) -> dict[str, object]:
        return {"filename": self.filename, "url": self.url, "sha512": self.sha512, "size_bytes": self.size_bytes, "minecraft_versions": sorted(self.minecraft_versions), "loaders": sorted(self.loaders)}


@dataclass(frozen=True, eq=False)
class ModCandidate:
    identity: CanonicalModIdentity
    source: ModSource
    project_id: str
    slug: str
    name: str
    description: str
    downloads: int
    categories: frozenset[str]
    files: tuple[ModFile, ...] = ()
    client_side: Environment = Environment.UNKNOWN
    server_side: Environment = Environment.UNKNOWN

    def __post_init__(self) -> None:
        if not self.project_id.strip() or self.downloads < 0:
            raise ValueError("invalid mod candidate")
        if not isinstance(self.source, ModSource):
            object.__setattr__(self, "source", ModSource(str(self.source).lower()))
        object.__setattr__(self, "categories", frozenset(str(x).strip().lower() for x in self.categories))
        object.__setattr__(self, "files", tuple(self.files))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ModCandidate) and (self.source, self.project_id) == (other.source, other.project_id)

    def __hash__(self) -> int:
        return hash((self.source, self.project_id))

    def file_for(self, minecraft_version: str, loader: str) -> ModFile | None:
        return next((item for item in self.files if item.supports(minecraft_version, loader)), None)

    def to_dict(self) -> dict[str, object]:
        return {"identity": self.identity.to_dict(), "source": self.source.value, "project_id": self.project_id, "slug": self.slug, "name": self.name, "description": self.description, "downloads": self.downloads, "categories": sorted(self.categories), "files": [item.to_dict() for item in self.files], "client_side": self.client_side.value, "server_side": self.server_side.value}
