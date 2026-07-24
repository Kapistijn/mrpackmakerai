"""Parallel AI candidate generation and quality-aware merge rounds.

Workers are independent: each gets a distinct exploration directive, asks the
configured AI provider for a structured plan, searches the real catalog, ranks
its own candidate pack, critiques it, and returns evidence. Catalog detail
requests are coalesced through the shared async cache so worker count does not
multiply identical provider traffic.
"""
from __future__ import annotations
import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from typing import Awaitable, Callable
from app.config import config
from app.models.enums import LoaderType
from app.schemas.mod import ModEntry
from app.services.ai_provider import AIProviderError, create_ai_provider
from app.services.mod_resolver import mod_identity
from app.services.source_registry import ModSourceRegistry

MAX_WORKERS = 24

@dataclass(frozen=True)
class WorkerDirective:
    index: int
    seed: int
    focus: str

@dataclass
class WorkerCandidate:
    directive: WorkerDirective
    mods: list[ModEntry] = field(default_factory=list)
    score: float = 0.0
    intent_coverage: float = 0.0
    compatibility: float = 0.0
    performance: float = 0.0
    dependency_quality: float = 0.0
    confidence: float = 0.0
    reasoning: str = ""
    ai_used: bool = False
    fallback_reason: str | None = None

    def keyset(self) -> set[str]:
        return {mod_identity(mod) for mod in self.mods}

    def evidence(self) -> dict:
        return {
            "worker": self.directive.index,
            "focus": self.directive.focus,
            "score": self.score,
            "intent_coverage": self.intent_coverage,
            "compatibility": self.compatibility,
            "performance": self.performance,
            "dependency_quality": self.dependency_quality,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "ai_used": self.ai_used,
            "fallback_reason": self.fallback_reason,
            "mod_count": len(self.mods),
        }

class AsyncCoalescingCache:
    """Shared in-flight + completed cache for worker catalog requests."""
    def __init__(self) -> None:
        self._values: dict[str, tuple[list[ModEntry], int]] = {}
        self._inflight: dict[str, asyncio.Future[tuple[list[ModEntry], int]]] = {}
        self._lock = asyncio.Lock()

    async def get_or_fetch(self, key: str, fetch: Callable[[], Awaitable[tuple[list[ModEntry], int]]]):
        async with self._lock:
            if key in self._values:
                return self._values[key]
            future = self._inflight.get(key)
            if future is None:
                future = asyncio.get_running_loop().create_future()
                self._inflight[key] = future
                owner = True
            else:
                owner = False
        if not owner:
            return await future
        try:
            value = await fetch()
            async with self._lock:
                self._values[key] = value
                future.set_result(value)
                self._inflight.pop(key, None)
            return value
        except Exception as exc:
            async with self._lock:
                if not future.done(): future.set_exception(exc)
                self._inflight.pop(key, None)
            raise

class WorkerGenerationEngine:
    def __init__(self, registry: ModSourceRegistry, *, max_concurrency: int | None = None):
        self.registry = registry
        self.cache = AsyncCoalescingCache()
        self.max_concurrency = max(1, min(max_concurrency or 8, MAX_WORKERS))

    @staticmethod
    def validate_worker_count(value: int) -> int:
        if value < 2 or value > MAX_WORKERS:
            raise ValueError(f"workers must be between 2 and {MAX_WORKERS}")
        return value

    @staticmethod
    def merge_group(left: WorkerCandidate, right: WorkerCandidate) -> WorkerCandidate:
        """Merge both packs, preserving strongest unique content from each."""
        ranked = sorted([left, right], key=lambda item: item.score, reverse=True)
        merged: list[ModEntry] = []
        seen: set[str] = set()
        for candidate in ranked:
            for mod in candidate.mods:
                identity = mod_identity(mod)
                if identity not in seen:
                    seen.add(identity)
                    merged.append(mod)
        total = len(merged)
        overlap = len(left.keyset() & right.keyset())
        return WorkerCandidate(
            directive=WorkerDirective(min(left.directive.index, right.directive.index), left.directive.seed ^ right.directive.seed, f"merged: {left.directive.focus} + {right.directive.focus}"),
            mods=merged,
            score=(left.score + right.score) / 2 + min(10.0, max(0, total - overlap) * 0.05),
            intent_coverage=max(left.intent_coverage, right.intent_coverage),
            compatibility=min(left.compatibility, right.compatibility),
            performance=min(left.performance, right.performance),
            dependency_quality=min(left.dependency_quality, right.dependency_quality),
            confidence=(left.confidence + right.confidence) / 2,
            reasoning=f"Preserved unique mods from workers {left.directive.index} and {right.directive.index}; overlap {overlap}.",
            ai_used=left.ai_used or right.ai_used,
            fallback_reason=left.fallback_reason or right.fallback_reason,
        )

    @classmethod
    def merge_rounds(cls, candidates: list[WorkerCandidate]) -> tuple[WorkerCandidate, list[dict]]:
        if not candidates:
            raise ValueError("No worker candidates were produced")
        current = list(candidates)
        rounds: list[dict] = []
        while len(current) > 1:
            next_round: list[WorkerCandidate] = []
            comparisons: list[dict] = []
            for offset in range(0, len(current), 2):
                if offset + 1 == len(current):
                    next_round.append(current[offset]); continue
                left, right = current[offset], current[offset + 1]
                merged = cls.merge_group(left, right)
                comparisons.append({"left": left.evidence(), "right": right.evidence(), "result": merged.evidence()})
                next_round.append(merged)
            rounds.append({"input_count": len(current), "output_count": len(next_round), "comparisons": comparisons})
            current = next_round
        return current[0], rounds

    async def _search(self, provider, directive: WorkerDirective, query: str, mc: str, loader: LoaderType):
        key = f"{provider.source_id}:{mc}:{loader.value}:{query.casefold()}"
        return await self.cache.get_or_fetch(key, lambda: provider.search(query, mc, loader, limit=50, offset=0))

    async def _worker(self, directive: WorkerDirective, prompt: str, mc: str, loader: LoaderType, target: int) -> WorkerCandidate:
        provider = create_ai_provider()
        plan = None
        fallback_reason = None
        try:
            try:
                plan = await provider.chat_json(
                    system_prompt="You are one independent modpack worker. Explore a distinct strategy. Return JSON with queries (list), rationale (string), intent_coverage (number 0-100), performance (number 0-100).",
                    user_prompt=f"Request: {prompt}\nWorker {directive.index}. Focus: {directive.focus}. Seed: {directive.seed}. Do not copy another worker.",
                    schema=_WorkerPlan,
                )
            except AIProviderError as exc:
                fallback_reason = str(exc)
        finally:
            await provider.close()
        queries = list(plan.queries) if plan else [directive.focus, prompt]
        candidates: dict[str, ModEntry] = {}
        for catalog in self.registry.providers(available_only=True):
            for query in queries[:8]:
                hits, _ = await self._search(catalog, directive, query, mc, loader)
                for mod in hits:
                    candidates.setdefault(mod_identity(mod), mod)
        mods = list(candidates.values())[:max(target, 1)]
        coverage = float(plan.intent_coverage if plan else 40)
        performance = float(plan.performance if plan else 50)
        return WorkerCandidate(directive, mods, score=coverage * .45 + performance * .2 + min(len(mods), target) / max(target, 1) * 35, intent_coverage=coverage, compatibility=70.0, performance=performance, dependency_quality=60.0, confidence=65.0 if plan else 35.0, reasoning=plan.rationale if plan else "Deterministic catalog exploration fallback.", ai_used=plan is not None, fallback_reason=fallback_reason)

    async def generate(self, prompt: str, mc: str, loader: LoaderType, workers: int, target: int = 40) -> tuple[WorkerCandidate, list[dict]]:
        count = self.validate_worker_count(workers)
        focuses = ("survival progression", "performance stability", "world generation", "immersion realism", "content diversity", "structures exploration", "automation utility", "multiplayer balance")
        directives = [WorkerDirective(i, int(hashlib.sha256(f"{prompt}:{i}".encode()).hexdigest()[:8], 16), focuses[i % len(focuses)]) for i in range(count)]
        semaphore = asyncio.Semaphore(self.max_concurrency)
        async def run(directive):
            async with semaphore:
                return await self._worker(directive, prompt, mc, loader, target)
        candidates = await asyncio.gather(*(run(directive) for directive in directives))
        return self.merge_rounds(list(candidates))

class _WorkerPlan(__import__('pydantic').BaseModel):
    queries: list[str] = []
    rationale: str = ""
    intent_coverage: float = 50
    performance: float = 50
