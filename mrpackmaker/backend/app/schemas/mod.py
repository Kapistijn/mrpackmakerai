"""Unified mod DTOs."""

from __future__ import annotations

from pydantic import BaseModel, Field

class ModDependency(BaseModel):
    project_id: str
    dependency_type: str = "required"
    # Source IDs are deliberately strings.  The source registry validates them
    # at runtime, so a future platform can be added without a database/schema
    # migration or a frontend redeploy just to extend an enum.
    source: str | None = None


class ModHash(BaseModel):
    sha1: str | None = None
    sha512: str | None = None


class ModEntry(BaseModel):
    id: str
    source: str
    name: str
    slug: str = ""
    icon_url: str | None = None
    summary: str = ""
    downloads: int = 0
    categories: list[str] = Field(default_factory=list)
    loaders: list[str] = Field(default_factory=list)
    dependencies: list[ModDependency] = Field(default_factory=list)
    project_url: str = ""
    selected_version: str | None = None
    version_id: str | None = None
    file_id: int | None = None
    file_name: str | None = None
    file_size: int | None = None
    download_url: str | None = None
    hashes: ModHash = Field(default_factory=ModHash)
    # Optional in-instance install location (e.g. shaderpacks/foo.zip). When
    # unset the export writer derives it from the mod's categories, defaulting
    # to mods/<file_name>.
    install_path: str | None = None


class ModSearchResult(BaseModel):
    hits: list[ModEntry]
    total: int
    source: str


class ModSearchResponse(BaseModel):
    results: list[ModEntry]
    total: int
    modrinth_available: bool = True
    curseforge_available: bool = True
    available_sources: dict[str, bool] = Field(default_factory=dict)
