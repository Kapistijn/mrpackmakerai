"""Compatibility report schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class CompatStatus(str, Enum):
    OK = "OK"
    WARN = "WARN"
    ERROR = "ERROR"


class CompatCheckItem(BaseModel):
    name: str
    status: CompatStatus
    message: str = ""


class CompatibilityMetrics(BaseModel):
    """Stable metrics for the UI release-readiness dashboard.

    Values are deliberately nullable where the backend cannot know the user's
    Java/CPU/GPU environment. Returning null is safer than inventing precision.
    """

    minecraft_version: str
    loader: str
    loader_version: str | None = None
    java_version: str | None = None
    dependency_count: int = 0
    duplicate_count: int = 0
    missing_mod_count: int = 0
    missing_library_count: int = 0
    incompatible_count: int = 0
    client_only_count: int = 0
    server_only_count: int = 0
    deprecated_count: int = 0
    abandoned_count: int = 0
    outdated_count: int = 0
    security_issue_count: int = 0
    performance_score: int | None = Field(default=None, ge=0, le=100)
    estimated_ram_mb: int | None = None
    estimated_vram_mb: int | None = None
    estimated_cpu_load_percent: int | None = Field(default=None, ge=0, le=100)
    estimated_startup_seconds: int | None = None
    download_size_bytes: int = 0
    installed_size_bytes: int = 0


class CompatibilityReport(BaseModel):
    status: CompatStatus
    mods: list[CompatCheckItem] = Field(default_factory=list)
    dependencies: list[CompatCheckItem] = Field(default_factory=list)
    conflicts: list[CompatCheckItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_libraries: list[str] = Field(default_factory=list)
    export_ready: bool = False
    errors: list[str] = Field(default_factory=list)
    metrics: CompatibilityMetrics | None = None
