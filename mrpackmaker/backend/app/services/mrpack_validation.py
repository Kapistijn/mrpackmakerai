"""Strict validation shared by compatibility checks and MRPack export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

from app.models.project import Project
from app.schemas.mod import ModEntry


@dataclass(frozen=True)
class ExportIssue:
    code: str
    message: str


class MrpackValidationError(ValueError):
    def __init__(self, issues: list[ExportIssue]) -> None:
        self.issues = issues
        super().__init__("; ".join(issue.message for issue in issues))


def mod_key(mod: ModEntry) -> str:
    return f"{mod.source}:{mod.id}"


def _safe_mod_filename(filename: str) -> bool:
    path = PurePosixPath(filename.replace("\\", "/"))
    return (
        path.name == filename
        and filename not in {"", ".", ".."}
        and ".." not in path.parts
        and not path.is_absolute()
    )


def validate_export_inputs(project: Project, mods: list[ModEntry]) -> list[ExportIssue]:
    """Return every reason a pack cannot safely be exported.

    This intentionally validates the *selected* files, rather than silently
    excluding an invalid mod.  A pack that installs only part of the requested
    dependency graph is worse than a clear, fixable export error.
    """
    issues: list[ExportIssue] = []
    if not project.resolved_loader_version:
        issues.append(ExportIssue("loader_version_missing", "The selected loader version has not been resolved."))
    if not mods:
        issues.append(ExportIssue("no_mods", "At least one compatible mod is required for export."))

    seen_keys: set[str] = set()
    seen_paths: set[str] = set()
    for mod in mods:
        key = mod_key(mod)
        if key in seen_keys:
            issues.append(ExportIssue("duplicate_mod", f"Mod '{key}' is selected more than once."))
        seen_keys.add(key)

        if not mod.file_name:
            issues.append(ExportIssue("file_missing", f"{mod.name} has no resolved file."))
            continue
        if not _safe_mod_filename(mod.file_name):
            issues.append(ExportIssue("unsafe_file_name", f"{mod.name} has an unsafe file name."))
            continue
        pack_path = f"mods/{mod.file_name}"
        if pack_path in seen_paths:
            issues.append(ExportIssue("duplicate_file", f"Multiple mods use '{pack_path}'."))
        seen_paths.add(pack_path)

        if not mod.download_url:
            issues.append(ExportIssue("download_missing", f"{mod.name} has no download URL."))
        else:
            parsed = urlparse(mod.download_url)
            if parsed.scheme not in {"https", "http"} or not parsed.netloc:
                issues.append(ExportIssue("download_invalid", f"{mod.name} has an invalid download URL."))
        if not (mod.hashes.sha1 or mod.hashes.sha512):
            issues.append(ExportIssue("hash_missing", f"{mod.name} has no SHA-1 or SHA-512 hash."))
        if not mod.file_size or mod.file_size <= 0:
            issues.append(ExportIssue("size_missing", f"{mod.name} has no valid file size."))
    return issues
