"""Regression tests for the export gate and extensible catalog boundary."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models.project import Project
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.dependency_graph import DependencyGraph
from app.services.mrpack_validation import validate_export_inputs
from app.services.source_registry import ModSourceRegistry


def complete_mod(*, source: str = "example", mod_id: str = "one", filename: str = "one.jar") -> ModEntry:
    return ModEntry(
        id=mod_id,
        source=source,
        name="Example Mod",
        slug="example-mod",
        file_name=filename,
        file_size=42,
        download_url="https://catalog.example/mods/one.jar",
        hashes=ModHash(sha1="a" * 40),
    )


def project() -> Project:
    return Project(
        name="Test Pack",
        description="Test description",
        minecraft_version="1.20.1",
        loader="fabric",
        theme="technology",
        difficulty="normal",
        performance_preference="balanced",
        resolved_loader_version="0.15.11",
    )


class ExportValidationTests(unittest.TestCase):
    def test_complete_mod_is_exportable(self) -> None:
        self.assertEqual(validate_export_inputs(project(), [complete_mod()]), [])

    def test_invalid_files_are_not_silently_skipped(self) -> None:
        bad = complete_mod(filename="../outside.jar")
        messages = [issue.code for issue in validate_export_inputs(project(), [bad])]
        self.assertIn("unsafe_file_name", messages)

    def test_loader_version_is_required(self) -> None:
        pack = project()
        pack.resolved_loader_version = None
        messages = [issue.code for issue in validate_export_inputs(pack, [complete_mod()])]
        self.assertIn("loader_version_missing", messages)


class DependencyGraphTests(unittest.TestCase):
    def test_optional_dependency_does_not_block_export(self) -> None:
        mod = complete_mod()
        mod.dependencies = [ModDependency(project_id="optional-lib", dependency_type="optional", source="example")]
        graph = DependencyGraph()
        graph.add_mod(mod)
        self.assertEqual(graph.get_missing_required(), [])


class RegistryTests(unittest.IsolatedAsyncioTestCase):
    async def test_custom_catalog_can_be_registered_without_core_changes(self) -> None:
        class DemoCatalog:
            source_id = "demo-catalog"
            available = True

            async def search(self, *args, **kwargs):
                return [complete_mod(source=self.source_id)], 1

            async def get_mod_detail(self, *args, **kwargs):
                return complete_mod(source=self.source_id)

            async def close(self):
                return None

        registry = ModSourceRegistry([DemoCatalog()])
        self.assertEqual(registry.ids(), ["demo-catalog"])
        mod = await registry.get("demo-catalog").get_mod_detail("one", "1.20.1", "fabric")
        self.assertEqual(mod.source, "demo-catalog")
        await registry.close()
