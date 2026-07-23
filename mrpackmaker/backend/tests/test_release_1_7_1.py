"""1.7.1 regression tests for release-readiness behavior."""

from types import SimpleNamespace

from app.models.enums import LoaderType
from app.schemas.compatibility import CompatStatus, CompatibilityMetrics
from app.schemas.mod import ModEntry, ModHash
from app.services.mod_resolver import ModResolver, mod_identity
from app.services.mrpack import MrpackGenerator


def test_metrics_accept_unknown_runtime_values_as_null():
    metrics = CompatibilityMetrics(minecraft_version="1.20.1", loader="forge")
    assert metrics.java_version is None
    assert metrics.estimated_vram_mb is None
    assert metrics.performance_score is None


def test_duplicate_identity_is_stable_across_sources():
    first = ModEntry(id="a", source="modrinth", name="Create", slug="create", hashes=ModHash())
    second = ModEntry(id="b", source="curseforge", name="Create Mod", slug="create", hashes=ModHash())
    assert mod_identity(first) == mod_identity(second)
    assert len(ModResolver.deduplicate([first, second])) == 1


def test_compat_status_enum_is_serializable():
    assert CompatStatus.OK.value == "OK"
    assert CompatStatus.ERROR.value == "ERROR"


def test_export_prefers_pinned_loader_version():
    mod = ModEntry(
        id="example", source="modrinth", name="Example", slug="example",
        file_name="example.jar", file_size=10,
        download_url="https://cdn.modrinth.com/example.jar",
        hashes=ModHash(sha1="abc"),
    )
    project = SimpleNamespace(
        loader=LoaderType.FORGE.value,
        loader_version="47.2.0",
        resolved_loader_version="47.3.0",
        minecraft_version="1.20.1",
        name="Pinned", description="Pinned runtime",
    )
    index = MrpackGenerator().build_index(project, [mod])
    assert index["dependencies"]["forge"] == "47.2.0"
