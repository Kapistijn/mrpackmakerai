"""Validated Modrinth MRPack ZIP generator."""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import config
from app.models.enums import LoaderType
from app.models.project import Project
from app.schemas.mod import ModEntry
from app.services.mrpack_validation import MrpackValidationError, validate_export_inputs

logger = logging.getLogger(__name__)

LOADER_DEPENDENCY_KEYS = {
    LoaderType.FABRIC: "fabric-loader",
    LoaderType.FORGE: "forge",
    LoaderType.NEOFORGE: "neoforge",
}


def _sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^\w\s-]", "", name).strip().replace(" ", "-")
    return safe or "modpack"


class MrpackGenerator:
    def build_index(self, project: Project, mods: list[ModEntry]) -> dict[str, Any]:
        loader_key = LOADER_DEPENDENCY_KEYS[LoaderType(project.loader)]
        index: dict[str, Any] = {
            "formatVersion": 1,
            "game": "minecraft",
            "versionId": datetime.now(timezone.utc).strftime("%Y.%m.%d-%H%M%S"),
            "name": project.name,
            "summary": project.description,
            "files": [],
            "dependencies": {
                "minecraft": project.minecraft_version,
                loader_key: project.resolved_loader_version,
            },
        }
        for mod in mods:
            hashes = {
                algorithm: value
                for algorithm, value in {
                    "sha1": mod.hashes.sha1,
                    "sha512": mod.hashes.sha512,
                }.items()
                if value
            }
            index["files"].append(
                {
                    "path": f"mods/{mod.file_name}",
                    "hashes": hashes,
                    "downloads": [mod.download_url],
                    "fileSize": mod.file_size,
                }
            )
        return index

    def _validate_archive(self, path: Path) -> None:
        with zipfile.ZipFile(path, "r") as archive:
            corrupt_file = archive.testzip()
            if corrupt_file:
                raise RuntimeError(f"Corrupt ZIP member: {corrupt_file}")
            members = archive.namelist()
            if "modrinth.index.json" not in members:
                raise RuntimeError("Missing modrinth.index.json")
            if any(name.startswith(("/", "\\")) or ".." in Path(name).parts for name in members):
                raise RuntimeError("Archive contains an unsafe path")
            index = json.loads(archive.read("modrinth.index.json"))
            if index.get("formatVersion") != 1 or index.get("game") != "minecraft":
                raise RuntimeError("Invalid MRPack metadata")
            if not index.get("dependencies", {}).get("minecraft"):
                raise RuntimeError("MRPack is missing a Minecraft dependency")
            for file_entry in index.get("files", []):
                if not file_entry.get("hashes") or not file_entry.get("downloads"):
                    raise RuntimeError("MRPack contains an unresolved file")

    def generate(self, project: Project) -> Path:
        mods = [ModEntry.model_validate(raw) for raw in json.loads(project.mods_json or "[]")]
        issues = validate_export_inputs(project, mods)
        if issues:
            raise MrpackValidationError(issues)

        index = self.build_index(project, mods)
        config.output_dir.mkdir(parents=True, exist_ok=True)
        output_path = config.output_dir / f"{_sanitize_filename(project.name)}.mrpack"

        # The completed archive is atomically moved into place only after it
        # passes validation, so a failed export never replaces a usable pack.
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{_sanitize_filename(project.name)}-", suffix=".mrpack", dir=config.output_dir
        )
        os.close(descriptor)
        temporary_path = Path(temporary_name)
        try:
            with zipfile.ZipFile(temporary_path, "w", zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("modrinth.index.json", json.dumps(index, indent=2))
            self._validate_archive(temporary_path)
            temporary_path.replace(output_path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink(missing_ok=True)

        logger.info("Generated and validated MRPack: %s", output_path)
        return output_path
