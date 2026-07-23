import asyncio
import json

import pytest

from app.domain.common import Loader
from app.domain.compatibility.models import CompatibilityReport
from app.domain.loader import LoaderResolutionError, LoaderSelection, LoaderSelectionSource
from app.domain.requirements.models import GenerationBrief, RequirementProfile
from app.domain.requirements.understanding import ConfidenceLevel, GenerationRevision, RequirementAnalysis, RequirementExplanation, RequirementUpdate


def profile(**changes):
    values = {"raw_prompt": "RPG modpack", "minecraft_version": "1.20.1", "loader": Loader.FABRIC}
    values.update(changes)
    return RequirementProfile(**values)


def test_extended_requirements_are_immutable_and_serializable():
    item = profile(desired_categories={"horror", "bosses"}, forbidden_categories={"tech"}, gameplay_loop="exploration", ram_budget_mb=8192, fps_priority=80, shaders=True, required_mods={"sodium"})
    payload = json.loads(json.dumps(item.to_dict()))
    assert payload["desired_categories"] == ["bosses", "horror"]
    with pytest.raises(AttributeError):
        item.desired_categories.add("magic")
    assert hash(item) is not None


def test_requirement_analysis_requires_questions_when_information_is_missing():
    analysis = RequirementAnalysis(profile(), ConfidenceLevel.MISSING_INFORMATION, RequirementExplanation(follow_up_questions=("Which Minecraft version?",)))
    assert analysis.confidence is ConfidenceLevel.MISSING_INFORMATION
    with pytest.raises(ValueError):
        RequirementAnalysis(profile(), ConfidenceLevel.MISSING_INFORMATION)


def test_requirement_analysis_supports_understood_and_uncertain_states():
    understood = RequirementAnalysis(profile(), ConfidenceLevel.UNDERSTOOD)
    uncertain = RequirementAnalysis(profile(), ConfidenceLevel.UNCERTAIN)
    assert understood.confidence is ConfidenceLevel.UNDERSTOOD
    assert uncertain.confidence is ConfidenceLevel.UNCERTAIN
    assert json.loads(json.dumps(understood.to_dict()))["confidence"] == "understood"
    assert json.loads(json.dumps(uncertain.to_dict()))["confidence"] == "uncertain"


def test_revision_updates_requirements_without_mutating_base():
    base = profile(features={"tech"})
    brief = GenerationBrief(base, "RPG", {"rpg": 1}, 1)
    revision = GenerationRevision(brief, RequirementUpdate(add_features={"magic"}, remove_features={"tech"}), "User requested more magic")
    assert revision.revised_profile.features == frozenset({"magic"})
    assert base.features == frozenset({"tech"})


def test_loader_selection_is_single_source_of_truth():
    selection = LoaderSelection(Loader.FABRIC, "1.20.1", "0.16.10", LoaderSelectionSource.LATEST, True)
    payload = json.loads(json.dumps(selection.to_dict()))
    assert payload == {"loader": "fabric", "minecraft_version": "1.20.1", "loader_version": "0.16.10", "source": "latest", "resolved": True}
    report = CompatibilityReport("1.20.1", Loader.FABRIC, "0.16.10", evaluated=True, loader_selection=selection)
    assert report.is_exportable
    with pytest.raises(ValueError):
        CompatibilityReport("1.20.1", Loader.FABRIC, "0.16.11", loader_selection=selection)


def test_loader_resolver_protocol_conformance():
    class Resolver:
        async def resolve(self, selection):
            return selection

    from app.domain.loader import LoaderResolver
    assert isinstance(Resolver(), LoaderResolver)


def test_loader_selection_rejects_unresolved_version_and_invalid_input():
    with pytest.raises(ValueError):
        LoaderSelection("not-a-loader", "1.20.1")
    with pytest.raises(ValueError):
        LoaderSelection(Loader.FABRIC, "1.20.1", resolved=True)
