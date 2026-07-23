from __future__ import annotations

from collections.abc import Sequence

from app.adapters.errors import InvalidResponseError
from app.domain.common import Loader, PerformanceTarget
from app.domain.mods.models import ModCandidate
from app.domain.providers.protocols import AIProvider, SelectionResult
from app.domain.requirements.models import GenerationBrief, RequirementProfile
from app.schemas.ai import ModRanking
from app.services.ai_provider import OpenAICompatibleProvider
from app.services.prompt_pipeline import optimize_prompt
from app.services.requirements import parse_requirements


class OpenAICompatibleAdapter:
    """Expose the existing provider and deterministic requirement services as
    the new capability-oriented domain contracts. No provider logic is copied.
    """

    def __init__(self, provider: OpenAICompatibleProvider, *, minecraft_version: str, loader: Loader, theme: str = "custom", difficulty: str = "normal", performance_preference: str = "balanced") -> None:
        self._provider = provider
        self._minecraft_version = minecraft_version
        self._loader = loader
        self._theme = theme
        self._difficulty = difficulty
        self._performance_preference = performance_preference

    @property
    def name(self) -> str:
        return self._provider.provider_id

    async def analyze_requirements(self, raw_prompt: str) -> RequirementProfile:
        requirements = parse_requirements(raw_prompt, theme=self._theme)
        if requirements.warnings:
            raise InvalidResponseError("; ".join(requirements.warnings))
        target = requirements.minimum_mods or 0
        return RequirementProfile(
            raw_prompt=raw_prompt,
            minecraft_version=self._minecraft_version,
            loader=self._loader,
            theme=self._theme,
            features=frozenset(requirements.required_features),
            exclusions=frozenset(requirements.forbidden_features),
            min_mods=target,
            max_mods=requirements.maximum_mods,
            min_downloads=requirements.minimum_downloads,
            multiplayer=requirements.multiplayer,
            server=requirements.multiplayer,
            performance_target=PerformanceTarget.BALANCED,
        )

    async def build_brief(self, profile: RequirementProfile) -> GenerationBrief:
        prompt = optimize_prompt(profile.raw_prompt, minecraft_version=profile.minecraft_version, loader=profile.loader.value, theme=profile.theme or self._theme, difficulty=self._difficulty, performance_preference=self._performance_preference)
        target = profile.max_mods or profile.min_mods or 40
        return GenerationBrief(profile=profile, enriched_intent=prompt.normalized_request, category_quotas={"requested": target}, seed=0)

    async def select(self, brief: GenerationBrief, candidates: Sequence[ModCandidate]) -> tuple[SelectionResult, ...]:
        if not candidates:
            return ()
        candidate_payload = [item.to_dict() for item in candidates]
        ranking = await self._provider.chat_json(
            system_prompt="Select only candidates from the supplied list. Never invent IDs.",
            user_prompt=f"Brief:\n{brief.to_dict()}\nCandidates:\n{candidate_payload}",
            schema=ModRanking,
        )
        by_id = {item.project_id: item for item in candidates}
        selected: list[SelectionResult] = []
        for index, project_id in enumerate(ranking.selected_ids):
            candidate = by_id.get(project_id)
            if candidate is None:
                raise InvalidResponseError(f"AI selected unknown candidate: {project_id}")
            score = max(0.0, 1.0 - index / max(1, len(ranking.selected_ids)))
            selected.append(SelectionResult(candidate=candidate, score=score, reason=ranking.reasoning or "Selected by existing AI provider"))
        return tuple(selected)

    async def close(self) -> None:
        await self._provider.close()
