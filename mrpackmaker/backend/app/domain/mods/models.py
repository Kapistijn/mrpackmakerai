from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from app.domain.common import Environment, FrozenMap, ModSource, to_json_safe


@dataclass(frozen=True, eq=False)
class CanonicalModIdentity:
    """Equality is identity deduplication by canonical_key, not full object equality."""
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
        normalized_sources = {(key.value if isinstance(key, ModSource) else str(key)): str(value) for key, value in self.sources.items()}
        object.__setattr__(self, "sources", FrozenMap.from_mapping(normalized_sources))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CanonicalModIdentity) and self.canonical_key == other.canonical_key

    def __hash__(self) -> int:
        return hash(self.canonical_key)

    def matches(self, other: "CanonicalModIdentity") -> bool:
        return self.canonical_key == other.canonical_key or bool(self.aliases & ({other.canonical_key} | other.aliases)) or any(src in other.sources and other.sources[src] == project_id for src, project_id in self.sources.items())

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"canonical_key": self.canonical_key, "display_name": self.display_name, "sources": self.sources, "aliases": self.aliases, "authors": self.authors, "confidence": self.confidence})


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
        object.__setattr__(self, "minecraft_versions", frozenset(str(x) for x in self.minecraft_versions))
        object.__setattr__(self, "loaders", frozenset(str(x).lower() for x in self.loaders))

    def supports(self, minecraft_version: str, loader: str) -> bool:
        return minecraft_version in self.minecraft_versions and loader.lower() in self.loaders

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"filename": self.filename, "url": self.url, "sha512": self.sha512, "size_bytes": self.size_bytes, "minecraft_versions": self.minecraft_versions, "loaders": self.loaders})


@dataclass(frozen=True, eq=False)
class ModCandidate:
    """Equality is catalog deduplication by (source, project_id), not full object equality."""
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
        for field_name in ("client_side", "server_side"):
            value = getattr(self, field_name)
            if not isinstance(value, Environment):
                try:
                    object.__setattr__(self, field_name, Environment(str(value).lower()))
                except ValueError as exc:
                    raise ValueError(f"invalid {field_name}: {value!r}") from exc
        object.__setattr__(self, "categories", frozenset(str(x).strip().lower() for x in self.categories))
        object.__setattr__(self, "files", tuple(self.files))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ModCandidate) and (self.source, self.project_id) == (other.source, other.project_id)

    def __hash__(self) -> int:
        return hash((self.source, self.project_id))

    def file_for(self, minecraft_version: str, loader: str) -> ModFile | None:
        return next((item for item in self.files if item.supports(minecraft_version, loader)), None)

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"identity": self.identity, "source": self.source, "project_id": self.project_id, "slug": self.slug, "name": self.name, "description": self.description, "downloads": self.downloads, "categories": self.categories, "files": self.files, "client_side": self.client_side, "server_side": self.server_side})
