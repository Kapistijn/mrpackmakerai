from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class FrozenMap(Mapping[str, T], Generic[T]):
    """Hashable, immutable mapping backed by a sorted tuple of pairs."""

    _items: tuple[tuple[str, T], ...] = ()

    @classmethod
    def from_mapping(cls, values: Mapping[str, T] | None) -> "FrozenMap[T]":
        if values is None:
            return cls()
        items = tuple(sorted(((str(k), v) for k, v in values.items()), key=lambda p: p[0]))
        if len({key for key, _ in items}) != len(items):
            raise ValueError("duplicate mapping key")
        return cls(items)

    def __getitem__(self, key: str) -> T:
        for item_key, value in self._items:
            if item_key == key:
                return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return (key for key, _ in self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __hash__(self) -> int:
        return hash(self._items)

    def to_dict(self) -> dict[str, T]:
        return dict(self._items)


class Loader(str, Enum):
    FABRIC = "fabric"
    FORGE = "forge"
    QUILT = "quilt"
    NEOFORGE = "neoforge"

    @classmethod
    def from_str(cls, value: str) -> "Loader":
        normalized = value.strip().lower()
        for loader in cls:
            if loader.value == normalized:
                return loader
        raise ValueError(f"Unknown loader: {value!r}")


class ModSource(str, Enum):
    MODRINTH = "modrinth"
    CURSEFORGE = "curseforge"


class DependencyType(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    INCOMPATIBLE = "incompatible"
    EMBEDDED = "embedded"


class Environment(str, Enum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"


class PerformanceTarget(str, Enum):
    POTATO = "potato"
    BALANCED = "balanced"
    QUALITY = "quality"


class CompatibilityStatus(str, Enum):
    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"
