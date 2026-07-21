"""Compatibility report builder and export gate."""

from __future__ import annotations

import json
import logging

from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.compatibility import CompatCheckItem, CompatStatus, CompatibilityReport
from app.schemas.mod import ModEntry
from app.services.curseforge import CurseForgeClient
from app.services.dependency_graph import DependencyGraph
from app.services.mod_resolver import ModResolver
from app.services.modrinth import ModrinthClient
from app.services.mrpack_validation import validate_export_inputs
from app.services.source_registry import UnknownModSourceError

logger = logging.getLogger(__name__)

REQUIRED_LIBRARIES = {LoaderType.FABRIC: ["fabric-api"], LoaderType.FORGE: [], LoaderType.NEOFORGE: []}


class CompatibilityService:
    def __init__(self, modrinth: ModrinthClient, curseforge: CurseForgeClient) -> None:
        self.resolver = ModResolver(modrinth, curseforge)

    async def check_project(self, project: Project) -> CompatibilityReport:
        selected_mods = [ModEntry.model_validate(data) for data in json.loads(project.mods_json or "[]")]
        loader = LoaderType(project.loader)
        graph = DependencyGraph()
        mod_items: list[CompatCheckItem] = []
        errors: list[str] = []
        resolved_mods: list[ModEntry] = []

        for mod in selected_mods:
            try:
                fresh = await self.resolver.resolve_mod(
                    mod.source, mod.id, project.minecraft_version, loader
                )
            except UnknownModSourceError:
                fresh = None
                errors.append(f"{mod.name} uses an unknown source: {mod.source}")
            resolved = fresh or mod
            if fresh and fresh.file_name and fresh.download_url:
                resolved_mods.append(fresh)
                graph.add_mod(fresh)
                mod_items.append(CompatCheckItem(name=fresh.name, status=CompatStatus.OK, message="Version and loader match"))
            else:
                errors.append(f"{mod.name} has no compatible {project.minecraft_version} {loader.value} file")
                mod_items.append(CompatCheckItem(name=mod.name, status=CompatStatus.ERROR, message="No compatible file"))

        dependency_items: list[CompatCheckItem] = []
        missing_libraries: list[str] = []
        for library in REQUIRED_LIBRARIES[loader]:
            if not any(library in mod.slug.lower() or library in mod.name.lower() for mod in resolved_mods):
                missing_libraries.append(library)
                errors.append(f"Missing required library: {library}")
                dependency_items.append(CompatCheckItem(name=library, status=CompatStatus.ERROR, message="Missing required library"))

        for dependency_key in graph.get_missing_required():
            errors.append(f"Missing required dependency: {dependency_key}")
            dependency_items.append(CompatCheckItem(name=dependency_key, status=CompatStatus.ERROR, message="Missing required dependency"))

        present = set(graph.nodes)
        for dependency_key in sorted(graph.get_all_dependency_keys() & present):
            dependency_items.append(CompatCheckItem(name=dependency_key, status=CompatStatus.OK, message="Present"))

        conflicts: list[CompatCheckItem] = []
        for left, right in graph.get_conflicts():
            errors.append(f"Incompatible mods: {left} and {right}")
            conflicts.append(CompatCheckItem(name=f"{left} ↔ {right}", status=CompatStatus.ERROR, message="Declared incompatible"))
        if not conflicts:
            conflicts.append(CompatCheckItem(name="none", status=CompatStatus.OK, message="No declared conflicts"))

        # Export validation is intentionally performed on freshly resolved
        # files.  It catches duplicate paths, missing hashes and an unresolved
        # loader before the user can download a partial archive.
        export_issues = validate_export_inputs(project, resolved_mods)
        errors.extend(issue.message for issue in export_issues)
        warnings: list[str] = []
        if len(resolved_mods) > 80:
            warnings.append(f"Large modpack ({len(resolved_mods)} mods) may need extra memory.")
        if not project.resolved_loader_version:
            warnings.append("Loader version has not been resolved.")

        unique_errors = list(dict.fromkeys(errors))
        status = CompatStatus.ERROR if unique_errors else CompatStatus.WARN if warnings else CompatStatus.OK
        return CompatibilityReport(
            status=status,
            mods=mod_items,
            dependencies=dependency_items,
            conflicts=conflicts,
            warnings=warnings,
            missing_libraries=missing_libraries,
            export_ready=not unique_errors,
            errors=unique_errors,
        )

    async def close(self) -> None:
        await self.resolver.close()
