"""Deterministic planning helpers for expert-style modpack generation.

These helpers do not invent catalog entries. They turn validated user intent
into an inspectable design plan, query expansion, category quotas, and review
signals before provider search begins.
"""
from __future__ import annotations
from dataclasses import dataclass
from app.services.requirements import Requirements, category_quotas

@dataclass(frozen=True)
class PackDesign:
    vision: str
    gameplay_loop: tuple[str, ...]
    required_experiences: tuple[str, ...]
    forbidden_experiences: tuple[str, ...]
    pacing: str
    atmosphere: tuple[str, ...]
    categories: dict[str, int]
    search_queries: tuple[str, ...]

@dataclass(frozen=True)
class PackQuality:
    gameplay: float
    performance: float
    creativity: float
    compatibility: float
    progression: float
    balance: float
    atmosphere: float
    replayability: float
    immersion: float
    stability: float
    @property
    def overall(self) -> float:
        values = (self.gameplay, self.performance, self.creativity, self.compatibility, self.progression, self.balance, self.atmosphere, self.replayability, self.immersion, self.stability)
        return round(sum(values) / len(values), 3)

def _theme_queries(theme: str | None) -> tuple[str, ...]:
    return {
        'horror': ('horror','psychological horror','ambient horror','stalker','creepy','survival horror','dark atmosphere','immersive','night','sound','fog','monster','entity','weather','lighting'),
        'technology': ('technology','automation','machines','factory','energy','storage','progression','engineering'),
        'magic': ('magic','spell','ritual','wizard','arcane','fantasy','dimensions','progression'),
        'adventure': ('adventure','exploration','structures','dungeons','bosses','worldgen','quests','dimensions'),
    }.get((theme or '').casefold(), ('content','exploration','progression','worldgen','performance','qol'))

def build_pack_design(requirements: Requirements, *, target_count: int | None = None) -> PackDesign:
    theme = requirements.themes[0] if requirements.themes else 'custom'
    feature_text = ' '.join(requirements.required_features).casefold()
    if theme == 'horror':
        loop = ('explore at night','manage limited resources','survive rare encounters','progress through escalating threats')
        experiences = ('tension','darkness','ambient audio','fog and weather','meaningful exploration','rare encounters')
        atmosphere = ('sound','lighting','fog','weather','structures','caves')
        pacing = 'slow-burn escalation with rare high-intensity encounters'
    elif 'automation' in feature_text or theme == 'technology':
        loop = ('gather resources','build a production chain','unlock progression','optimize the base')
        experiences = ('clear progression','automation milestones','resource trade-offs')
        atmosphere = ('worldgen','structures','progression')
        pacing = 'steady progression with increasingly complex milestones'
    else:
        loop = ('explore','gather resources','progress through compatible content','master the world')
        experiences = ('varied exploration','clear progression','meaningful combat')
        atmosphere = ('worldgen','structures','mobs')
        pacing = 'measured progression with varied activities'
    queries = tuple(dict.fromkeys((*_theme_queries(theme), *requirements.required_features, *atmosphere)))
    return PackDesign(f'{theme} pack focused on {pacing}', loop, experiences, requirements.forbidden_features, pacing, atmosphere, category_quotas(requirements, target_count), queries)

def review_pack(mods, requirements: Requirements) -> PackQuality:
    if not mods: return PackQuality(0,0,0,0,0,0,0,0,0,0)
    texts = [' '.join((m.name,m.slug,m.summary,*m.categories)).casefold() for m in mods]
    joined = ' '.join(texts)
    required_hits = sum(feature.casefold() in joined for feature in requirements.required_features)
    performance = sum(any(term in text for term in ('performance','optimization','fps','sodium','modernfix')) for text in texts)
    category_count = len({category for m in mods for category in m.categories})
    duplicate_ids = len(mods) - len({f'{m.source}:{m.id}' for m in mods})
    compatibility = sum(bool(m.file_name and m.download_url and (m.hashes.sha1 or m.hashes.sha512)) for m in mods) / len(mods)
    return PackQuality(min(1, required_hits / max(1,len(requirements.required_features))), min(1, performance / max(1, len(mods) * .1)), min(1, category_count / 10), compatibility, min(1, category_count / 8), min(1, 1 - duplicate_ids / len(mods)), min(1, ('sound' in joined) * .5 + ('lighting' in joined) * .5), min(1, category_count / 8), min(1, ('immers' in joined) * .5 + ('atmos' in joined) * .5), compatibility)
