from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from app.domain.common import Loader, to_json_safe


class LoaderSelectionSource(str, Enum):
    USER = "user"
    AUTO = "auto"
    LATEST = "latest"


@dataclass(frozen=True)
class LoaderSelection:
    loader: Loader
    minecraft_version: str
    loader_version: str | None = None
    source: LoaderSelectionSource = LoaderSelectionSource.USER
    resolved: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.loader, Loader):
            object.__setattr__(self, "loader", Loader.from_str(str(self.loader)))
        if not self.minecraft_version.strip():
            raise ValueError("minecraft_version is required")
        if not isinstance(self.source, LoaderSelectionSource):
            object.__setattr__(self, "source", LoaderSelectionSource(str(self.source).lower()))
        if self.resolved and not self.loader_version:
            raise ValueError("resolved loader selection requires loader_version")
        if self.loader_version is not None and not self.loader_version.strip():
            raise ValueError("loader_version cannot be blank")

    def to_dict(self) -> dict[str, object]:
        return to_json_safe({"loader": self.loader, "minecraft_version": self.minecraft_version, "loader_version": self.loader_version, "source": self.source, "resolved": self.resolved})


class LoaderResolutionError(RuntimeError):
    pass


@runtime_checkable
class LoaderResolver(Protocol):
    async def resolve(self, selection: LoaderSelection) -> LoaderSelection:
        """Resolve latest/manual loader version without changing MC version or loader."""
        ...
