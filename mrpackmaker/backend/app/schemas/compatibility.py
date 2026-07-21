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


class CompatibilityReport(BaseModel):
    status: CompatStatus
    mods: list[CompatCheckItem] = Field(default_factory=list)
    dependencies: list[CompatCheckItem] = Field(default_factory=list)
    conflicts: list[CompatCheckItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    missing_libraries: list[str] = Field(default_factory=list)
    export_ready: bool = False
    errors: list[str] = Field(default_factory=list)
