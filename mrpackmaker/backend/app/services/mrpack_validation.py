"""Strict validation shared by compatibility checks and MRPack export."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import urlparse

from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.mod_resolver import mod_identity

ALLOWED_DOWNLOAD_HOSTS = ("cdn.modrinth.com", "github.com", "raw.githubusercontent.com", "objects.githubusercontent.com", "gitlab.com", "codeberg.org")

# The Modrinth pack format copies files into the instance; only these target
# folders are permitted for downloadable entries.
ALLOWED_INSTALL_PREFIXES = ("mods/", "shaderpacks/", "resourcepacks/")


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


def install_path_for(mod: ModEntry) -> str | None:
    """Resolve the in-instance install path for a mod.

    Honors an explicit ``install_path`` when set, otherwise derives the target
    folder from the mod's categories (shaderpacks/ or resourcepacks/), falling
    back to mods/<file_name>.
    """
    if not mod.file_name:
        return None
    explicit = getattr(mod, "install_path", None)
    if explicit:
        return explicit
    category_text = " ".join(mod.categories).casefold()
    if "shader" in category_text:
        return f"shaderpacks/{mod.file_name}"
    if "resourcepack" in category_text or "resource pack" in category_text:
        return f"resourcepacks/{mod.file_name}"
    return f"mods/{mod.file_name}"


def _safe_mod_filename(filename: str) -> bool:
    path = PurePosixPath(filename.replace("\\", "/"))
    return path.name == filename and filename not in {"", ".", ".."} and ".." not in path.parts and not path.is_absolute()


def _host_allowed(netloc: str) -> bool:
    host = netloc.lower().split("@")[-1].split(":")[0]
    return any(host == allowed or host.endswith("." + allowed) for allowed in ALLOWED_DOWNLOAD_HOSTS)


def validate_export_inputs(project: Project, mods: list[ModEntry]) -> list[ExportIssue]:
    """Return every reason a pack cannot safely be exported.

    Validation is fail-closed: an archive with a partial dependency graph or
    duplicate project is worse than a clear error the user can fix.
    """
    issues: list[ExportIssue] = []
    selected_loader = getattr(project, "loader_version", None)
    resolved_loader = getattr(project, "resolved_loader_version", None)
    if not selected_loader and not resolved_loader:
        issues.append(ExportIssue("loader_version_missing", "The selected loader version has not been resolved."))
    if not mods:
        issues.append(ExportIssue("no_mods", "At least one compatible mod is required for export."))

    seen_keys: set[str] = set()
    seen_identities: dict[str, str] = {}
    seen_paths: set[str] = set()
    seen_hashes: dict[str, str] = {}
    for mod in mods:
        key = mod_key(mod)
        if key in seen_keys:
            issues.append(ExportIssue("duplicate_mod", f"Mod '{key}' is selected more than once."))
        seen_keys.add(key)

        identity = mod_identity(mod)
        previous = seen_identities.get(identity)
        if previous and previous != key:
            issues.append(ExportIssue("duplicate_project", f"'{mod.name}' duplicates project '{previous}' across catalog sources."))
        seen_identities[identity] = key

        if not mod.file_name:
            issues.append(ExportIssue("file_missing", f"{mod.name} has no resolved file."))
            continue
        if not _safe_mod_filename(mod.file_name):
            issues.append(ExportIssue("unsafe_file_name", f"{mod.name} has an unsafe file name."))
            continue
        pack_path = install_path_for(mod)
        if not pack_path or not pack_path.startswith(ALLOWED_INSTALL_PREFIXES):
            issues.append(ExportIssue("unsafe_install_path", f"{mod.name} has an unsupported install path."))
            continue
        if pack_path in seen_paths:
            issues.append(ExportIssue("duplicate_file", f"Multiple mods use '{pack_path}'."))
        seen_paths.add(pack_path)

        if not mod.download_url:
            issues.append(ExportIssue("download_missing", f"{mod.name} has no download URL."))
        else:
            parsed = urlparse(mod.download_url)
            if parsed.scheme != "https" or not parsed.netloc:
                issues.append(ExportIssue("download_invalid", f"{mod.name} must use a valid HTTPS download URL."))
            elif not _host_allowed(parsed.netloc):
                issues.append(ExportIssue("download_host_not_allowed", f"{mod.name} downloads from an unapproved host '{parsed.netloc}'."))
        for digest in (mod.hashes.sha1, mod.hashes.sha512):
            if digest:
                previous_hash = seen_hashes.get(digest.lower())
                if previous_hash and previous_hash != key:
                    issues.append(ExportIssue("duplicate_hash", f"{mod.name} shares a file hash with '{previous_hash}'."))
                seen_hashes[digest.lower()] = key
        if not (mod.hashes.sha1 or mod.hashes.sha512):
            issues.append(ExportIssue("hash_missing", f"{mod.name} has no SHA-1 or SHA-512 hash."))
        if not mod.file_size or mod.file_size <= 0:
            issues.append(ExportIssue("size_missing", f"{mod.name} has no valid file size."))
    return list(dict.fromkeys(issues))
