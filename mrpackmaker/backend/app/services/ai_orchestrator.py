"""Durable generation workflow with server-sent progress.

Two modes share one pipeline:

* **AI mode** uses the configured provider to analyse the request, plan
  categories and rank mods, and degrades gracefully to heuristics if any AI
  call fails.
* **Quick mode** (``use_ai=False``) skips every AI call and selects the most
  downloaded compatible mods.  It exists so a usable modpack is produced even
  when no AI provider is configured or reachable at all.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

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

# A performance-friendly baseline that exists for every common version/loader.
# Used to give even an empty/ízkeyword-free request a sensible starting point.
POPULAR_FALLBACK_QUERIES = ["performance", "utility", "storage"]


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

    @staticmethod
    def _fallback_queries(project: Project, prompt: str) -> list[str]:
        """Deterministic search queries from the theme and the prompt text.

        This is what step 2 uses when the AI is unavailable, and what quick
        mode uses directly.  It always yields at least one query.
        """
        queries: list[str] = list(THEME_CATEGORIES.get(ThemeType(project.theme), []))
        if project.theme_custom:
            queries.append(project.theme_custom)
        # Keep meaningful words from the prompt so a described request still
        # steers the search without any AI involvement.
        words = [word for word in prompt.split() if len(word) > 4]
        if words:
            queries.append(" ".join(words[:6]))
        queries.extend(POPULAR_FALLBACK_QUERIES)
        # De-duplicate while preserving order.
        return list(dict.fromkeys(q for q in queries if q.strip())) or POPULAR_FALLBACK_QUERIES

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

    async def _gather_candidates(
        self,
        registry: ModSourceRegistry,
        resolver: ModResolver,
        queries: list[str],
        mc_version: str,
        loader: LoaderType,
    ) -> list[ModEntry]:
        """Search every available source, always including a broad query.

        The trailing empty-string query returns the most relevant compatible
        mods for the version/loader even when the specific queries match
        nothing, which is what keeps output guaranteed.
        """
        candidates: dict[str, ModEntry] = {}
        search_terms = list(dict.fromkeys([*queries[:8], ""]))
        for query in search_terms:
            for source in registry.providers(available_only=True):
                try:
                    hits, _ = await source.search(query, mc_version, loader, limit=15)
                except Exception as exc:  # A single source failing must not abort.
                    logger.warning("Search failed on %s for '%s': %s", source.source_id, query, exc)
                    continue
                for hit in hits:
                    candidates.setdefault(resolver.mod_key(hit), hit)
        return list(candidates.values())[:120]

    async def generate(self, project_id: int, *, use_ai: bool = True) -> None:
        queue = self._events[project_id]
        provider = create_ai_provider() if use_ai else None
        registry = ModSourceRegistry(
            [
                ModrinthClient(config.apis.modrinth_key),
                CurseForgeClient(config.apis.curseforge_key),
            ]
        )
        resolver = ModResolver(registry=registry)
        mode_label = "ai" if use_ai else "quick"

        try:
            async with AsyncSessionLocal() as db:
                project = await db.get(Project, project_id)
                if not project:
                    return

                run = GenerationRun(
                    project_id=project_id,
                    provider=provider.provider_id if provider else "quick",
                )
                db.add(run)
                project.status = ProjectStatus.GENERATING.value
                await db.flush()
                # Persist the job before the first network request so a timeout
                # or restart can be audited instead of silently lost.
                await db.commit()

                loader = LoaderType(project.loader)
                mc_version = project.minecraft_version
                prompt = project.generation_prompt or project.description
                locked = self._locked_context(project)
                target_count = 40

                # --- Step 1 & 2: understand the request -------------------
                queries = self._fallback_queries(project, prompt)
                if use_ai and provider is not None:
                    await self._emit(project_id, AIProgressEvent(step=1, message="Analyzing gameplay requirements..."), run)
                    analysis: GameplayAnalysis | None = None
                    try:
                        analysis = await provider.chat_json(
                            system_prompt=(
                                f"You are a Minecraft modpack expert. {locked}\n"
                                "Return JSON with gameplay_goals, must_have_features, avoid arrays."
                            ),
                            user_prompt=f"Analyze this modpack request: {prompt}",
                            schema=GameplayAnalysis,
                        )
                    except AIProviderError:
                        logger.warning("AI analysis failed; continuing with heuristic queries")

                    await self._emit(project_id, AIProgressEvent(step=2, message="Determining mod categories..."), run)
                    try:
                        category_plan = await provider.chat_json(
                            system_prompt=(
                                f"You are a Minecraft modpack curator. {locked}\n"
                                "Return JSON with categories, search_queries, target_mod_count (30-50)."
                            ),
                            user_prompt=(
                                f"Plan mod categories for: {prompt}\n"
                                f"Suggested categories: {THEME_CATEGORIES.get(ThemeType(project.theme), [])}\n"
                                f"Analysis: {analysis.model_dump_json() if analysis else '{}'}"
                            ),
                            schema=CategoryPlan,
                        )
                        target_count = max(1, min(category_plan.target_mod_count, 80))
                        if category_plan.search_queries:
                            queries = list(dict.fromkeys([*category_plan.search_queries, *queries]))
                    except AIProviderError:
                        logger.warning("AI category planning failed; using heuristic queries")
                else:
                    await self._emit(project_id, AIProgressEvent(step=1, message="Preparing a quick pack (no AI)..."), run)
                    await self._emit(project_id, AIProgressEvent(step=2, message="Selecting mod categories from theme..."), run)

                # --- Step 3: search sources -------------------------------
                await self._emit(project_id, AIProgressEvent(step=3, message="Searching configured mod sources..."), run)
                candidate_list = await self._gather_candidates(registry, resolver, queries, mc_version, loader)
                if not candidate_list:
                    raise RuntimeError(
                        "No compatible mods were found for this Minecraft version and loader. "
                        "Check that the version/loader combination has mods on Modrinth."
                    )

                # --- Step 4: rank / select --------------------------------
                await self._emit(project_id, AIProgressEvent(step=4, message="Ranking mod candidates..."), run)
                selected_keys: list[str] = []
                if use_ai and provider is not None:
                    candidate_summary = [
                        {"key": resolver.mod_key(mod), "name": mod.name, "summary": mod.summary[:200]}
                        for mod in candidate_list
                    ]
                    try:
                        ranking = await provider.chat_json(
                            system_prompt=(
                                f"You are a Minecraft modpack curator. {locked}\n"
                                "Select only provided candidates. Return selected_ids as source:id keys, "
                                "rejected_ids and reasoning."
                            ),
                            user_prompt=(
                                f"Request: {prompt}\nTarget count: {target_count}\n"
                                f"Candidates: {json.dumps(candidate_summary)}"
                            ),
                            schema=ModRanking,
                        )
                        available_keys = {resolver.mod_key(mod) for mod in candidate_list}
                        selected_keys = [key for key in ranking.selected_ids if key in available_keys]
                    except AIProviderError:
                        logger.warning("AI ranking failed; selecting most downloaded compatible candidates")
                # Heuristic selection covers quick mode and every AI fallback.
                if not selected_keys:
                    selected_keys = [
                        resolver.mod_key(mod)
                        for mod in sorted(candidate_list, key=lambda item: item.downloads, reverse=True)[:target_count]
                    ]

                # --- Step 5: resolve files + dependencies -----------------
                await self._emit(project_id, AIProgressEvent(step=5, message="Resolving required dependencies..."), run)
                resolved_mods: list[ModEntry] = []
                resolved_keys: set[str] = set()
                pending_keys = list(dict.fromkeys(selected_keys))
                # Bounded traversal protects against a malformed circular graph.
                while pending_keys and len(resolved_mods) < 250:
                    key = pending_keys.pop(0)
                    if key in resolved_keys:
                        continue
                    try:
                        entry = await resolver.resolve_mod_by_key(key, mc_version, loader)
                    except UnknownModSourceError:
                        logger.warning("Skipping unknown catalog source in key '%s'", key)
                        continue
                    if not entry or not entry.file_name or not entry.download_url:
                        # A candidate without a compatible, downloadable file
                        # cannot ship; skip it rather than blocking the pack.
                        continue
                    resolved_mods.append(entry)
                    resolved_keys.add(resolver.mod_key(entry))
                    for dependency in entry.dependencies:
                        if dependency.dependency_type in {"required", "embedded"} and dependency.project_id:
                            dependency_key = f"{dependency.source or entry.source}:{dependency.project_id}"
                            if dependency_key not in resolved_keys:
                                pending_keys.append(dependency_key)

                resolved_mods = await resolver.inject_library_mods(resolved_mods, mc_version, loader)
                if not resolved_mods:
                    raise RuntimeError(
                        "Found candidate mods but none had a downloadable file for this "
                        "version/loader. Try a different Minecraft version or loader."
                    )

                # --- Step 6: balance (AI only) ----------------------------
                await self._emit(project_id, AIProgressEvent(step=6, message="Finalizing the mod list..."), run)
                summary = f"{'Generated' if use_ai else 'Quick pack:'} {len(resolved_mods)} compatible mods."
                if use_ai and provider is not None:
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
                        summary = final.summary or summary
                    except AIProviderError:
                        logger.warning("AI finalization failed; keeping the resolved mod list")

                loader_version = await resolver.resolve_loader_version(loader, mc_version)
                project.mods_json = json.dumps([mod.model_dump(mode="json") for mod in resolved_mods])
                project.resolved_loader_version = loader_version
                project.ai_summary = summary
                project.status = ProjectStatus.REVIEW.value
                run.status = "completed"
                run.summary = summary
                if provider is not None:
                    try:
                        run.model = (await provider.connection_status()).active_model
                    except Exception:  # Reporting the model must never fail a completed run.
                        run.model = None
                run.completed_at = datetime.now(timezone.utc)
                await self._emit(
                    project_id,
                    AIProgressEvent(
                        step=7,
                        message=f"{mode_label.capitalize()} generation complete: {len(resolved_mods)} mods selected.",
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
                AIProgressEvent(
                    step=0,
                    message=f"Generation failed: {exc}",
                    status="error",
                ),
            )
        finally:
            if provider is not None:
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

    def start_generation(self, project_id: int, *, use_ai: bool = True) -> None:
        if self.is_active(project_id):
            raise RuntimeError("Generation already in progress")
        self._events[project_id] = asyncio.Queue()
        self._active[project_id] = asyncio.create_task(self.generate(project_id, use_ai=use_ai))

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
