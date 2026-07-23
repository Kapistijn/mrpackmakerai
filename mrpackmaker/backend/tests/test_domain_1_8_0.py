import json

import pytest

from app.domain.common import CompatibilityStatus, FrozenMap, Loader, ModSource
from app.domain.compatibility.models import CompatibilityIssue, CompatibilityReport, MeasuredMetrics
from app.domain.mods.models import CanonicalModIdentity, ModCandidate, ModFile
from app.domain.providers.protocols import DependencyResolutionResult, DependencyResolver, ModCatalogProvider, SelectionResult
from app.domain.requirements.models import GenerationBrief, RequirementProfile


def identity() -> CanonicalModIdentity:
    return CanonicalModIdentity("sodium", "Sodium", {ModSource.MODRINTH: "sodium"}, {"rubidium"}, {"jellysquid"})


def candidate(**changes: object) -> ModCandidate:
    file = ModFile("sodium.jar", "https://example.invalid/sodium.jar", "hash", 10, {"1.20.1"}, {"fabric"})
    values = {"identity": identity(), "source": ModSource.MODRINTH, "project_id": "sodium", "slug": "sodium", "name": "Sodium", "description": "fast", "downloads": 1000, "categories": {"performance"}, "files": (file,)}
    values.update(changes)
    return ModCandidate(**values)


def test_frozen_map_recursively_freezes_and_copies_input() -> None:
    source = {"nested": {"values": [1, {"tags": {"a", "b"}}]}}
    frozen = FrozenMap.from_mapping(source)
    source["nested"]["values"].append(99)
    source["nested"]["values"][1]["tags"].add("changed")
    assert frozen["nested"]["values"] == (1, FrozenMap.from_mapping({"tags": frozenset({"a", "b"})}))
    assert hash(frozen) is not None
    with pytest.raises(TypeError):
        frozen["nested"]["values"][1]["tags"] = frozenset()


def test_all_value_objects_are_hashable() -> None:
    profile = RequirementProfile("horror", "1.20.1", Loader.FABRIC, min_mods=1)
    brief = GenerationBrief(profile, "horror", {"horror": 1}, 7)
    report = CompatibilityReport("1.20.1", Loader.FABRIC)
    values = (FrozenMap.from_mapping({"x": 1}), profile, brief, identity(), candidate(), MeasuredMetrics(), CompatibilityIssue("WARN", "warning"), report)
    assert all(isinstance(hash(value), int) for value in values)


def test_nested_collections_cannot_be_mutated() -> None:
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


def test_every_domain_object_serializes_as_json_safe() -> None:
    profile = RequirementProfile("horror", "1.20.1", Loader.FABRIC, min_mods=1)
    brief = GenerationBrief(profile, "horror", {"horror": 1}, 7)
    mod_identity = identity()
    mod_file = candidate().files[0]
    mod_candidate = candidate()
    issue = CompatibilityIssue("WARN", "warning")
    metrics = MeasuredMetrics(min_ram_mb=2048)
    report = CompatibilityReport("1.20.1", Loader.FABRIC, issues=(issue,), metrics=metrics)
    selection = SelectionResult(mod_candidate, 0.8, "matches performance requirement")
    dependency = DependencyResolutionResult(resolved=(mod_candidate,), success=True)
    objects = (profile, brief, mod_identity, mod_file, mod_candidate, issue, metrics, report, selection, dependency)
    for obj in objects:
        payload = json.dumps(obj.to_dict(), sort_keys=True)
        assert isinstance(json.loads(payload), dict)


def test_invalid_input_and_environment_normalization() -> None:
    with pytest.raises(ValueError):
        RequirementProfile("", "1.20.1", Loader.FABRIC)
    with pytest.raises(ValueError):
        RequirementProfile("x", "1.20.1", Loader.FABRIC, min_mods=3, max_mods=2)
    with pytest.raises(ValueError):
        ModFile("", "https://example.invalid/x", "hash", 1, set(), set())
    assert candidate(client_side="required", server_side=Environment.UNKNOWN).client_side.value == "required"
    with pytest.raises(ValueError):
        candidate(client_side="not-a-real-environment")


def test_compatibility_unknown_flows() -> None:
    report = CompatibilityReport("1.20.1", Loader.FABRIC)
    assert report.status is CompatibilityStatus.UNKNOWN
    assert not report.is_exportable
    with_warning = report.with_issue(CompatibilityIssue("WARN", "warning"))
    assert with_warning.status is CompatibilityStatus.UNKNOWN
    assert not with_warning.is_exportable
    evaluated = CompatibilityReport("1.20.1", Loader.FABRIC, issues=(CompatibilityIssue("WARN", "warning"),), evaluated=True)
    assert evaluated.status is CompatibilityStatus.COMPATIBLE and evaluated.is_exportable
    fatal = evaluated.with_issue(CompatibilityIssue("FATAL", "blocked", fatal=True))
    assert fatal.status is CompatibilityStatus.INCOMPATIBLE and not fatal.is_exportable


def test_dependency_result_contract_and_failure_combinations() -> None:
    mod = candidate()
    ok = DependencyResolutionResult(resolved=(mod,), success=True)
    assert ok.is_complete and hash(ok) is not None
    failed = DependencyResolutionResult(missing=("fabric-api",), conflicts=("a/b",), cycles=(("a", "b", "a"),), version_conflicts=("minecraft>=1.20",), success=False)
    assert not failed.is_complete
    assert json.loads(json.dumps(failed.to_dict()))["cycles"] == [["a", "b", "a"]]
    with pytest.raises(ValueError):
        DependencyResolutionResult(missing=("fabric-api",), success=True)


def test_catalog_and_dependency_protocol_conformance() -> None:
    class Catalog:
        async def search(self, query, *, minecraft_version, loader, limit=50, offset=0): return []
        async def get(self, project_id): return None

    class Resolver:
        async def resolve(self, selected, *, minecraft_version, loader): return DependencyResolutionResult(success=True)

    assert isinstance(Catalog(), ModCatalogProvider)
    assert isinstance(Resolver(), DependencyResolver)
