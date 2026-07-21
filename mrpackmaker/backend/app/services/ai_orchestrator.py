"""Durable seven-step AI generation workflow with server-sent progress."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import config
from app.db.session import AsyncSessionLocal
from app.models.enums import LoaderType, ProjectStatus, ThemeType
from app.models.generation import GenerationRun
from app.models.project import Project
from app.schemas.ai import AIProgressEvent, CategoryPlan, FinalModList, GameplayAnalysis, ModRanking
from app.schemas.mod import ModEntry
from app.services.ai_provider import AIProviderError, create_ai_provider
from app.services.curseforge import CurseForgeClient
from app.services.mod_resolver import ModResolver
from app.services.modrinth import ModrinthClient
from app.services.source_registry import ModSourceRegistry, UnknownModSourceError

logger = logging.getLogger(__name__)

THEME_CATEGORIES = {
    ThemeType.TECHNOLOGY: ["technology", "storage", "utility"],
    ThemeType.ADVENTURE: ["adventure", "worldgen", "mobs"],
    ThemeType.MAGIC: ["magic", "adventure"],
    ThemeType.EXPLORATION: ["worldgen", "adventure", "utility"],
    ThemeType.SURVIVAL: ["food", "utility", "storage"],
    ThemeType.CUSTOM: [],
}


class AIOrchestrator:
    """Owns in-process jobs, not request-scoped database sessions.

    A generation uses its own database session.  This is vital: FastAPI closes
    dependency sessions as soon as the POST response finishes, whereas a pack
    generation can run for minutes.
    """

    def __init__(self) -> None:
        self._active: dict[int, asyncio.Task[None]] = {}
        self._events: dict[int, asyncio.Queue[AIProgressEvent | None]] = {}

    def _locked_context(self, project: Project) -> str:
        theme = f"{project.theme} ({project.theme_custom})" if project.theme_custom else project.theme
        return (
            "IMMUTABLE USER SETTINGS (DO NOT CHANGE):\n"
            f"- Minecraft Version: {project.minecraft_version}\n"
            f"- Loader: {project.loader}\n"
            f"- Modpack Name: {project.name}\n"
            f"- Description: {project.description}\n"
            f"- Theme: {theme}\n"
            f"- Difficulty: {project.difficulty}\n"
            f"- Performance preference: {project.performance_preference}\n"
        )

    async def _emit(
        self,
        project_id: int,
        event: AIProgressEvent,
        run: GenerationRun | None = None,
    ) -> None:
        queue = self._events.get(project_id)
        if queue:
            await queue.put(event)
        if run is not None:
            history = json.loads(run.event_log_json or "[]")
            history.append(event.model_dump(mode="json"))
            run.event_log_json = json.dumps(history)

    async def generate(self, project_id: int) -> None:
        queue = self._events[project_id]
        provider = create_ai_provider()
        registry = ModSourceRegistry(
            [
                ModrinthClient(config.apis.modrinth_key),
                CurseForgeClient(config.apis.curseforge_key),
            ]
        )
        resolver = ModResolver(registry=registry)

        try:
            async with AsyncSessionLocal() as db:
                project = await db.get(Project, project_id)
                if not project:
                    return

                run = GenerationRun(project_id=project_id, provider=provider.provider_id)
                db.add(run)
                project.status = ProjectStatus.GENERATING.value
                await db.flush()
                # Persist the job before the first network request.  A timeout
                # or restart can then be audited instead of silently losing the
                # attempted generation.
                await db.commit()

                loader = LoaderType(project.loader)
                mc_version = project.minecraft_version
                prompt = project.generation_prompt or project.description
                locked = self._locked_context(project)

                await self._emit(project_id, AIProgressEvent(step=1, message="Analyzing gameplay requirements..."), run)
                analysis = await provider.chat_json(
                    system_prompt=(
                        f"You are a Minecraft modpack expert. {locked}\n"
                        "Return JSON with gameplay_goals, must_have_features, avoid arrays."
                    ),
                    user_prompt=f"Analyze this modpack request: {prompt}",
                    schema=GameplayAnalysis,
                )

                await self._emit(project_id, AIProgressEvent(step=2, message="Determining mod categories..."), run)
                default_categories = THEME_CATEGORIES.get(ThemeType(project.theme), [])
                category_plan = await provider.chat_json(
                    system_prompt=(
                        f"You are a Minecraft modpack curator. {locked}\n"
                        "Return JSON with categories, search_queries, target_mod_count (30-50)."
                    ),
                    user_prompt=(
                        f"Plan mod categories for: {prompt}\n"
                        f"Suggested categories: {default_categories}\n"
                        f"Analysis: {analysis.model_dump_json()}"
                    ),
                    schema=CategoryPlan,
                )
                category_plan.target_mod_count = max(1, min(category_plan.target_mod_count, 80))
                if not category_plan.search_queries:
                    category_plan.search_queries = [prompt[:100]]

                await self._emit(project_id, AIProgressEvent(step=3, message="Searching configured mod sources..."), run)
                candidates: dict[str, ModEntry] = {}
                for query in category_plan.search_queries[:8]:
                    for source in registry.providers(available_only=True):
                        hits, _ = await source.search(query, mc_version, loader, limit=15)
                        for hit in hits:
                            candidates.setdefault(resolver.mod_key(hit), hit)

                candidate_list = list(candidates.values())[:100]
                if not candidate_list:
                    raise AIProviderError("No compatible mods were found in the configured catalog sources")
                candidate_summary = [
                    {"key": resolver.mod_key(mod), "name": mod.name, "summary": mod.summary[:200]}
                    for mod in candidate_list
                ]

                await self._emit(project_id, AIProgressEvent(step=4, message="Ranking mod candidates..."), run)
                try:
                    ranking = await provider.chat_json(
                        system_prompt=(
                            f"You are a Minecraft modpack curator. {locked}\n"
                            "Select only provided candidates. Return selected_ids as source:id keys, "
                            "rejected_ids and reasoning."
                        ),
                        user_prompt=(
                            f"Request: {prompt}\nTarget count: {category_plan.target_mod_count}\n"
                            f"Candidates: {json.dumps(candidate_summary)}"
                        ),
                        schema=ModRanking,
                    )
                    available_keys = set(candidates)
                    selected_keys = [key for key in ranking.selected_ids if key in available_keys]
                except AIProviderError:
                    logger.warning("AI ranking failed; selecting most downloaded compatible candidates")
                    selected_keys = [
                        resolver.mod_key(mod)
                        for mod in sorted(candidate_list, key=lambda item: item.downloads, reverse=True)[
                            : category_plan.target_mod_count
                        ]
                    ]
                if not selected_keys:
                    selected_keys = [resolver.mod_key(mod) for mod in candidate_list[:category_plan.target_mod_count]]

                await self._emit(project_id, AIProgressEvent(step=5, message="Resolving required dependencies..."), run)
                resolved_mods: list[ModEntry] = []
                resolved_keys: set[str] = set()
                pending_keys = list(dict.fromkeys(selected_keys))
                # Bounded traversal protects the job from a malformed circular
                # dependency response while still supporting deep real graphs.
                while pending_keys and len(resolved_mods) < 250:
                    key = pending_keys.pop(0)
                    if key in resolved_keys:
                        continue
                    try:
                        entry = await resolver.resolve_mod_by_key(key, mc_version, loader)
                    except UnknownModSourceError:
                        logger.warning("Skipping unknown catalog source in key '%s'", key)
                        continue
                    if not entry:
                        continue
                    resolved_mods.append(entry)
                    resolved_keys.add(resolver.mod_key(entry))
                    for dependency in entry.dependencies:
                        if dependency.dependency_type in {"required", "embedded"} and dependency.project_id:
                            dependency_key = f"{dependency.source or entry.source}:{dependency.project_id}"
                            if dependency_key not in resolved_keys:
                                pending_keys.append(dependency_key)

                resolved_mods = await resolver.inject_library_mods(resolved_mods, mc_version, loader)

                await self._emit(project_id, AIProgressEvent(step=6, message="Balancing the final mod list..."), run)
                try:
                    final = await provider.chat_json(
                        system_prompt=(
                            f"You are a Minecraft modpack curator. {locked}\n"
                            "Return source:id mod_ids to keep and a concise summary."
                        ),
                        user_prompt="\n".join(
                            f"{resolver.mod_key(mod)}|{mod.name}" for mod in resolved_mods
                        ),
                        schema=FinalModList,
                    )
                    keep_keys = set(final.mod_ids)
                    if keep_keys:
                        resolved_mods = [
                            mod for mod in resolved_mods if resolver.mod_key(mod) in keep_keys
                        ] or resolved_mods
                    summary = final.summary or f"Generated {len(resolved_mods)} compatible mods."
                except AIProviderError:
                    summary = f"Generated {len(resolved_mods)} compatible mods."

                loader_version = await resolver.resolve_loader_version(loader, mc_version)
                project.mods_json = json.dumps([mod.model_dump(mode="json") for mod in resolved_mods])
                project.resolved_loader_version = loader_version
                project.ai_summary = summary
                project.status = ProjectStatus.REVIEW.value
                run.status = "completed"
                run.summary = summary
                run.model = (await provider.connection_status()).active_model
                run.completed_at = datetime.now(timezone.utc)
                await self._emit(
                    project_id,
                    AIProgressEvent(
                        step=7,
                        message=f"Generation complete: {len(resolved_mods)} mods selected.",
                        status="complete",
                        data={"mod_count": len(resolved_mods), "summary": summary},
                    ),
                    run,
                )
                await db.commit()
        except asyncio.CancelledError:
            await self._mark_cancelled(project_id)
            await self._emit(project_id, AIProgressEvent(step=0, message="Generation cancelled.", status="cancelled"))
            raise
        except Exception as exc:
            logger.exception("Generation failed for project %d", project_id)
            await self._mark_failed(project_id, str(exc))
            await self._emit(
                project_id,
                AIProgressEvent(step=0, message="Generation failed. See the server log for details.", status="error"),
            )
        finally:
            await provider.close()
            await registry.close()
            await queue.put(None)
            self._active.pop(project_id, None)

    async def _mark_failed(self, project_id: int, message: str) -> None:
        async with AsyncSessionLocal() as db:
            project = await db.get(Project, project_id)
            if project:
                project.status = ProjectStatus.DRAFT.value
            # Most recent running job belongs to this in-process task.
            from sqlalchemy import select

            run = (await db.execute(
                select(GenerationRun)
                .where(GenerationRun.project_id == project_id, GenerationRun.status == "running")
                .order_by(GenerationRun.started_at.desc())
            )).scalars().first()
            if run:
                run.status = "failed"
                run.error = message[:4000]
                run.completed_at = datetime.now(timezone.utc)
            await db.commit()

    async def _mark_cancelled(self, project_id: int) -> None:
        await self._mark_failed(project_id, "Cancelled by user")

    def start_generation(self, project_id: int) -> None:
        if self.is_active(project_id):
            raise RuntimeError("Generation already in progress")
        self._events[project_id] = asyncio.Queue()
        self._active[project_id] = asyncio.create_task(self.generate(project_id))

    def is_active(self, project_id: int) -> bool:
        task = self._active.get(project_id)
        return bool(task and not task.done())

    async def stream_events(self, project_id: int) -> AsyncGenerator[AIProgressEvent, None]:
        queue = self._events.get(project_id)
        if queue is None:
            return
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

    def cancel(self, project_id: int) -> bool:
        task = self._active.get(project_id)
        if task and not task.done():
            task.cancel()
            return True
        return False


orchestrator = AIOrchestrator()
