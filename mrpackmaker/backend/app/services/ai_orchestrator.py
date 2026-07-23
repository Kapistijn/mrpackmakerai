"""Durable, requirement-driven generation workflow with SSE progress."""

from __future__ import annotations

import asyncio
import json
import logging
import random
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
from app.services.mod_resolver import ModResolver, mod_identity
from app.services.mod_scoring import rank_mods
from app.services.prompt_pipeline import optimize_prompt
from app.services.requirements import parse_requirements, theme_matches
from app.services.modrinth import ModrinthClient
from app.services.source_registry import ModSourceRegistry, UnknownModSourceError

logger = logging.getLogger(__name__)
TERMINAL_STATUSES = {"complete", "error", "cancelled"}
THEME_CATEGORIES = {ThemeType.TECHNOLOGY: ["technology", "storage", "utility"], ThemeType.ADVENTURE: ["adventure", "worldgen", "mobs"], ThemeType.MAGIC: ["magic", "adventure"], ThemeType.EXPLORATION: ["worldgen", "adventure", "utility"], ThemeType.SURVIVAL: ["food", "utility", "storage"], ThemeType.CUSTOM: []}
POPULAR_FALLBACK_QUERIES = ["performance", "utility", "storage"]


class AIOrchestrator:
    def __init__(self) -> None:
        self._active: dict[int, asyncio.Task[None]] = {}
        self._events: dict[int, asyncio.Queue[AIProgressEvent | None]] = {}
        self._final: dict[int, AIProgressEvent] = {}

    def _locked_context(self, project: Project) -> str:
        theme = f"{project.theme} ({project.theme_custom})" if project.theme_custom else project.theme
        return ("IMMUTABLE USER SETTINGS (DO NOT CHANGE):\n" f"- Minecraft Version: {project.minecraft_version}\n" f"- Loader: {project.loader}\n" f"- Loader Version: {project.loader_version or 'latest stable'}\n" f"- Modpack Name: {project.name}\n" f"- Description: {project.description}\n" f"- Theme: {theme}\n" f"- Difficulty: {project.difficulty}\n" f"- Performance preference: {project.performance_preference}\n")

    @staticmethod
    def _fallback_queries(project: Project, prompt: str) -> list[str]:
        queries = list(THEME_CATEGORIES.get(ThemeType(project.theme), []))
        if project.theme_custom: queries.append(project.theme_custom)
        words = [word for word in prompt.split() if len(word) > 4]
        if words: queries.append(" ".join(words[:6]))
        queries.extend(POPULAR_FALLBACK_QUERIES)
        return list(dict.fromkeys(q for q in queries if q.strip())) or POPULAR_FALLBACK_QUERIES

    async def _emit(self, project_id: int, event: AIProgressEvent, run: GenerationRun | None = None) -> None:
        queue = self._events.get(project_id)
        if queue: await queue.put(event)
        if event.status in TERMINAL_STATUSES: self._final[project_id] = event
        if run is not None:
            history = json.loads(run.event_log_json or "[]")
            history.append(event.model_dump(mode="json"))
            run.event_log_json = json.dumps(history)

    async def _gather_candidates(self, registry, resolver, queries, mc_version, loader, requirements, *, seed: int) -> list[ModEntry]:
        candidates: dict[str, ModEntry] = {}
        search_terms = list(dict.fromkeys([*queries[:12], ""]))
        for query in search_terms:
            for source in registry.providers(available_only=True):
                try:
                    hits, _ = await source.search(query, mc_version, loader, limit=50)
                except Exception as exc:
                    logger.warning("Search failed on %s for '%s': %s", source.source_id, query, exc)
                    continue
                for hit in hits:
                    text = " ".join((hit.name, hit.slug, hit.summary, *hit.categories))
                    if hit.downloads < requirements.minimum_downloads or not theme_matches(text, requirements):
                        continue
                    candidates.setdefault(mod_identity(hit), hit)
        return [item.mod for item in rank_mods(list(candidates.values()), requirements, seed=seed) if item.score >= 0]

    async def generate(self, project_id: int, *, use_ai: bool = True) -> None:
        queue = self._events[project_id]
        provider = create_ai_provider() if use_ai else None
        registry = ModSourceRegistry([ModrinthClient(config.apis.modrinth_key), CurseForgeClient(config.apis.curseforge_key)])
        resolver = ModResolver(registry=registry)
        mode_label = "ai" if use_ai else "quick"
        try:
            async with AsyncSessionLocal() as db:
                project = await db.get(Project, project_id)
                if not project: return
                run = GenerationRun(project_id=project_id, provider=provider.provider_id if provider else "quick")
                db.add(run); project.status = ProjectStatus.GENERATING.value; await db.flush(); await db.commit()
                loader, mc_version = LoaderType(project.loader), project.minecraft_version
                prompt = project.generation_prompt or project.description
                requirements = parse_requirements(prompt, theme=project.theme)
                seed = project.id ^ int(datetime.now(timezone.utc).timestamp())
                brief = optimize_prompt(prompt, minecraft_version=mc_version, loader=loader.value, theme=project.theme, difficulty=project.difficulty, performance_preference=project.performance_preference)
                target_count = max(requirements.minimum_mods or 40, min(requirements.maximum_mods or 250, requirements.target_count))
                queries = self._fallback_queries(project, prompt) + list(requirements.required_features)
                if use_ai and provider is not None:
                    await self._emit(project_id, AIProgressEvent(step=1, message="Analyzing requirements..."), run)
                    try:
                        analysis = await provider.chat_json(system_prompt=brief.system_prompt, user_prompt=brief.as_user_prompt(), schema=GameplayAnalysis)
                        await self._emit(project_id, AIProgressEvent(step=2, message="Personalizing categories...", data={"themes": requirements.themes, "features": requirements.required_features}), run)
                        plan = await provider.chat_json(system_prompt=brief.system_prompt, user_prompt=f"{brief.as_user_prompt()}\nAnalysis: {analysis.model_dump_json()}", schema=CategoryPlan)
                        if plan.search_queries: queries = list(dict.fromkeys([*plan.search_queries, *queries]))
                    except AIProviderError as exc:
                        logger.warning("AI planning failed; using deterministic requirements: %s", exc)
                else:
                    await self._emit(project_id, AIProgressEvent(step=1, message="Analyzing requirements..."), run)
                    await self._emit(project_id, AIProgressEvent(step=2, message="Personalizing categories...", data={"themes": requirements.themes, "features": requirements.required_features}), run)
                await self._emit(project_id, AIProgressEvent(step=3, message="Finding requirement-matched mods..."), run)
                candidates = await self._gather_candidates(registry, resolver, queries, mc_version, loader, requirements, seed=seed)
                if len(candidates) < min(target_count, 10): raise RuntimeError(f"Only {len(candidates)} compatible mods matched your requirements; refusing to silently create a smaller pack (target {target_count}).")
                await self._emit(project_id, AIProgressEvent(step=4, message="Scoring personalized candidates..."), run)
                selected = candidates[:target_count]
                if len(selected) < requirements.minimum_mods if requirements.minimum_mods else False:
                    raise RuntimeError(f"Could not satisfy minimum mod count {requirements.minimum_mods}; found {len(selected)} compatible matches.")
                await self._emit(project_id, AIProgressEvent(step=5, message="Resolving dependencies and compatibility..."), run)
                resolved_mods: list[ModEntry] = []; resolved_keys: set[str] = set(); pending = [resolver.mod_key(item) for item in selected]
                while pending and len(resolved_mods) < max(250, target_count * 2):
                    key = pending.pop(0)
                    if key in resolved_keys: continue
                    try: entry = await resolver.resolve_mod_by_key(key, mc_version, loader)
                    except UnknownModSourceError: continue
                    if not entry or not entry.file_name or not entry.download_url: continue
                    identity = mod_identity(entry)
                    if identity in {mod_identity(item) for item in resolved_mods}: continue
                    resolved_mods.append(entry); resolved_keys.add(key)
                    for dependency in entry.dependencies:
                        if dependency.dependency_type in {"required", "embedded"} and dependency.project_id:
                            dep_key = f"{dependency.source or entry.source}:{dependency.project_id}"
                            if dep_key not in resolved_keys: pending.append(dep_key)
                resolved_mods = resolver.deduplicate(resolved_mods)
                if requirements.minimum_mods and len(resolved_mods) < requirements.minimum_mods:
                    raise RuntimeError(f"Dependencies and compatibility reduced the result to {len(resolved_mods)} mods, below your requested minimum of {requirements.minimum_mods}.")
                if not resolved_mods: raise RuntimeError("No compatible mods matched the selected theme and requirements.")
                await self._emit(project_id, AIProgressEvent(step=6, message="Running final quality checks and removing duplicates...", data={"mod_count": len(resolved_mods)}), run)
                loader_version = project.loader_version or await resolver.resolve_loader_version(loader, mc_version)
                if not loader_version: raise RuntimeError(f"No compatible {loader.value} loader version found for Minecraft {mc_version}.")
                project.mods_json = json.dumps([mod.model_dump(mode="json") for mod in resolved_mods]); project.resolved_loader_version = loader_version; project.ai_summary = f"Personalized {project.theme} pack: {len(resolved_mods)} requirement-matched mods."; project.status = ProjectStatus.REVIEW.value
                run.status = "completed"; run.summary = project.ai_summary; run.completed_at = datetime.now(timezone.utc)
                await self._emit(project_id, AIProgressEvent(step=7, message=f"{mode_label.capitalize()} generation complete: {len(resolved_mods)} personalized mods.", status="complete", data={"mod_count": len(resolved_mods), "target_count": target_count, "seed": seed}), run)
                await db.commit()
        except asyncio.CancelledError:
            await self._mark_cancelled(project_id); await self._emit(project_id, AIProgressEvent(step=0, message="Generation cancelled.", status="cancelled")); raise
        except Exception as exc:
            logger.exception("Generation failed for project %d", project_id); await self._mark_failed(project_id, str(exc)); await self._emit(project_id, AIProgressEvent(step=0, message=f"Generation failed: {exc}", status="error"))
        finally:
            if provider is not None: await provider.close()
            await registry.close(); await queue.put(None); self._active.pop(project_id, None); self._events.pop(project_id, None)

    async def _mark_failed(self, project_id: int, message: str) -> None:
        async with AsyncSessionLocal() as db:
            project = await db.get(Project, project_id)
            if project: project.status = ProjectStatus.DRAFT.value
            from sqlalchemy import select
            run = (await db.execute(select(GenerationRun).where(GenerationRun.project_id == project_id, GenerationRun.status == "running").order_by(GenerationRun.started_at.desc()))).scalars().first()
            if run: run.status = "failed"; run.error = message[:4000]; run.completed_at = datetime.now(timezone.utc)
            await db.commit()

    async def _mark_cancelled(self, project_id: int) -> None: await self._mark_failed(project_id, "Cancelled by user")
    def start_generation(self, project_id: int, *, use_ai: bool = True) -> None:
        if self.is_active(project_id): raise RuntimeError("Generation already in progress")
        self._final.pop(project_id, None); self._events[project_id] = asyncio.Queue(); self._active[project_id] = asyncio.create_task(self.generate(project_id, use_ai=use_ai))
    def is_active(self, project_id: int) -> bool: return bool(self._active.get(project_id) and not self._active[project_id].done())
    async def stream_events(self, project_id: int) -> AsyncGenerator[AIProgressEvent, None]:
        queue = self._events.get(project_id)
        if queue is None:
            final = self._final.pop(project_id, None)
            if final is not None: yield final
            return
        while True:
            event = await queue.get()
            if event is None: break
            yield event
    def cancel(self, project_id: int) -> bool:
        task = self._active.get(project_id)
        if task and not task.done(): task.cancel(); return True
        return False


orchestrator = AIOrchestrator()
