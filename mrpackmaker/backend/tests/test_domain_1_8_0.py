import json
import pytest

from app.domain.common import CompatibilityStatus, FrozenMap, Loader, ModSource
from app.domain.compatibility.models import CompatibilityIssue, CompatibilityReport, MeasuredMetrics
from app.domain.mods.models import CanonicalModIdentity, ModCandidate, ModFile
from app.domain.providers.protocols import DependencyResolutionResult, DependencyResolver, ModCatalogProvider
from app.domain.requirements.models import GenerationBrief, RequirementProfile


def identity() -> CanonicalModIdentity:
    return CanonicalModIdentity("sodium", "Sodium", {ModSource.MODRINTH: "sodium"}, {"rubidium"}, {"jellysquid"})


def candidate() -> ModCandidate:
    file = ModFile("sodium.jar", "https://example.invalid/sodium.jar", "hash", 10, {"1.20.1"}, {"fabric"})
    return ModCandidate(identity(), ModSource.MODRINTH, "sodium", "sodium", "Sodium", "fast", 1000, {"performance"}, (file,))


def test_all_value_objects_are_hashable():
    profile = RequirementProfile("horror", "1.20.1", Loader.FABRIC, min_mods=1)
    brief = GenerationBrief(profile, "horror", FrozenMap.from_mapping({"horror": 1}), 7)
    report = CompatibilityReport("1.20.1", Loader.FABRIC)
    values = (FrozenMap.from_mapping({"x": 1}), profile, brief, identity(), candidate(), MeasuredMetrics(), CompatibilityIssue("WARN", "warning"), report)
    assert all(isinstance(hash(value), int) for value in values)


def test_nested_collections_cannot_be_mutated():
    obj = candidate()
    with pytest.raises(TypeError):
        obj.identity.sources["modrinth"] = "changed"
    with pytest.raises(AttributeError):
        obj.files += (obj.files[0],)
    with pytest.raises(AttributeError):
        obj.files[0].loaders.add("forge")
    profile = RequirementProfile("horror", "1.20.1", Loader.FABRIC, features={"qol"})
    with pytest.raises(AttributeError):
        profile.features.add("magic")


def test_generation_brief_is_serializable():
    profile = RequirementProfile("horror", "1.20.1", Loader.FABRIC, min_mods=1)
    brief = GenerationBrief(profile, "horror", {"horror": 1}, 7)
    payload = json.dumps(brief.to_dict(), sort_keys=True)
    assert json.loads(payload)["profile"]["loader"] == "fabric"


def test_invalid_input_is_rejected():
    with pytest.raises(ValueError):
        RequirementProfile("", "1.20.1", Loader.FABRIC)
    with pytest.raises(ValueError):
        RequirementProfile("x", "1.20.1", Loader.FABRIC, min_mods=3, max_mods=2)
    with pytest.raises(ValueError):
        ModFile("", "https://example.invalid/x", "hash", 1, set(), set())


def test_compatibility_defaults_to_unknown_and_blocks_export():
    report = CompatibilityReport("1.20.1", Loader.FABRIC)
    assert report.status is CompatibilityStatus.UNKNOWN
    assert not report.is_exportable
    evaluated = CompatibilityReport("1.20.1", Loader.FABRIC, evaluated=True)
    assert evaluated.is_exportable


def test_dependency_result_contract():
    mod = candidate()
    ok = DependencyResolutionResult(resolved=(mod,), success=True)
    assert ok.is_complete and hash(ok) is not None
    failed = DependencyResolutionResult(missing=("fabric-api",), success=False)
    assert not failed.is_complete
    with pytest.raises(ValueError):
        DependencyResolutionResult(missing=("fabric-api",), success=True)


def test_catalog_protocol_conformance():
    class Catalog:
        async def search(self, query, *, minecraft_version, loader, limit=50, offset=0): return []
        async def get(self, project_id): return None
    assert isinstance(Catalog(), ModCatalogProvider)


def test_dependency_protocol_conformance():
    class Resolver:
        async def resolve(self, selected, *, minecraft_version, loader):
            return DependencyResolutionResult(success=True)
    assert isinstance(Resolver(), DependencyResolver)
