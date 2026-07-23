"""Deterministic mod scoring that does not overfit to download counts."""
from __future__ import annotations
import math, random
from dataclasses import dataclass
from typing import overload
from app.schemas.mod import ModEntry
from app.services.requirements import Requirements, theme_matches
@dataclass(frozen=True)
class ScoredMod:
    mod: ModEntry; score: float; reasons: tuple[str,...]
def _download_score(downloads:int,minimum:int)->float:
    if downloads<minimum:return 0.0
    return min(1.0,math.log10(max(downloads,1))/8.0)
def score_mod(mod:ModEntry,requirements:Requirements,*,rng:random.Random|None=None)->ScoredMod:
    rng=rng or random.Random(0); text=' '.join((mod.name,mod.slug,mod.summary,*mod.categories)).casefold(); reasons=[]
    if not theme_matches(text,requirements): return ScoredMod(mod,-1.0,('forbidden theme signal',))
    match=sum(1 for feature in requirements.required_features if feature.casefold() in text); match_score=min(1.0,match/max(1,len(requirements.required_features)))
    compatibility=1.0 if mod.file_name and mod.download_url else 0.0; quality=1.0 if mod.hashes.sha1 or mod.hashes.sha512 else 0.5; downloads=_download_score(mod.downloads,requirements.minimum_downloads)
    performance=1.0 if any(term in text for term in ('optimization','performance','fps','sodium','modernfix','ferritecore')) else 0.5
    if requirements.target_fps is not None and requirements.target_fps >= 60 and any(term in text for term in ('heavy','shader','visual','high quality')): performance -= .25
    if requirements.performance_preference == 'performance': performance=min(1.0,performance+.25)
    if requirements.performance_preference == 'quality' and any(term in text for term in ('visual','shader','quality')): performance=min(1.0,performance+.15)
    novelty=1.0-downloads; jitter=rng.random()*.03
    score=.40*match_score+.20*compatibility+.15*quality+.10*downloads+.10*performance+.05*novelty+jitter
    if match: reasons.append(f'matches {match} requested feature(s)')
    if compatibility: reasons.append('has a compatible downloadable file')
    if requirements.target_fps is not None and performance >= .75: reasons.append(f'supports {requirements.target_fps} FPS preference')
    if novelty>.5: reasons.append('adds catalog diversity')
    return ScoredMod(mod,score,tuple(reasons))
def rank_mods(mods:list[ModEntry],requirements:Requirements,*,seed:int)->list[ScoredMod]:
    rng=random.Random(seed); return sorted([score_mod(mod,requirements,rng=rng) for mod in mods],key=lambda item:item.score,reverse=True)
def _select_scored(ranked:list[ScoredMod],count:int)->list[ScoredMod]:
    if count<=0:return []
    selected=[]; used=set(); categories=set()
    for item in ranked:
        key=f'{item.mod.source}:{item.mod.id}'
        if key in used:continue
        cats={c.casefold() for c in item.mod.categories}
        if cats-categories:selected.append(item); used.add(key); categories.update(cats)
        if len(selected)>=count:return selected
    for item in ranked:
        key=f'{item.mod.source}:{item.mod.id}'
        if key not in used:selected.append(item); used.add(key)
        if len(selected)>=count:break
    return selected
def _select_candidates(candidates:list[ModEntry],count:int)->list[ModEntry]:
    if count<=0:return []
    selected=[]; used=set(); categories=set()
    for item in candidates:
        key=f'{item.source}:{item.id}'
        if key in used:continue
        cats={c.casefold() for c in item.categories}
        if cats-categories:selected.append(item); used.add(key); categories.update(cats)
        if len(selected)>=count:return selected
    for item in candidates:
        key=f'{item.source}:{item.id}'
        if key not in used:selected.append(item); used.add(key)
        if len(selected)>=count:break
    return selected
@overload
def select_diverse(ranked:list[ScoredMod],count:int)->list[ScoredMod]:...
@overload
def select_diverse(ranked:list[ModEntry],count:int)->list[ModEntry]:...
def select_diverse(ranked:list[ScoredMod]|list[ModEntry],count:int)->list[ScoredMod]|list[ModEntry]:
    if not ranked:return []
    return _select_scored(ranked,count) if isinstance(ranked[0],ScoredMod) else _select_candidates(ranked,count)
