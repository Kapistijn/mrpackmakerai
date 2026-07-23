from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass, is_dataclass
from enum import Enum
from typing import Any, Generic, TypeVar

T = TypeVar("T")


def freeze(value: T) -> T:
    """Recursively copy mutable containers into immutable equivalents."""
    if isinstance(value, FrozenMap):
        return value  # type: ignore[return-value]
    if isinstance(value, Mapping):
        return FrozenMap.from_mapping(value)  # type: ignore[return-value]
    if isinstance(value, list):
        return tuple(freeze(item) for item in value)  # type: ignore[return-value]
    if isinstance(value, tuple):
        return tuple(freeze(item) for item in value)  # type: ignore[return-value]
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze(item) for item in value)  # type: ignore[return-value]
    return value


def to_json_safe(value: Any) -> Any:
    """Convert domain values recursively to JSON-compatible primitives.

    Sets and frozensets are recursively converted and then sorted by
    ``(type(item).__name__, repr(item))``. This gives deterministic output
    without relying on object or hash iteration order, including for mixed
    JSON-safe item types.
    """
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, FrozenMap):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, Mapping):
        return {str(key): to_json_safe(item) for key, item in value.items()}
    if isinstance(value, (set, frozenset)):
        converted = [to_json_safe(item) for item in value]
        return sorted(converted, key=lambda item: (type(item).__name__, repr(item)))
    if isinstance(value, (tuple, list)):
        return [to_json_safe(item) for item in value]
    if hasattr(value, "to_dict"):
        return to_json_safe(value.to_dict())
    if is_dataclass(value):
        return to_json_safe({key: getattr(value, key) for key in value.__dataclass_fields__})
    return value


@dataclass(frozen=True)
class FrozenMap(Mapping[str, T], Generic[T]):
    """Deeply immutable and hashable mapping backed by sorted tuple pairs."""

    _items: tuple[tuple[str, T], ...] = ()

    @classmethod
    def from_mapping(cls, values: Mapping[object, T] | None) -> "FrozenMap[T]":
        if values is None:
            return cls()
        items = tuple(sorted(((str(key), freeze(value)) for key, value in values.items()), key=lambda pair: pair[0]))
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
        return {key: value for key, value in self._items}


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
