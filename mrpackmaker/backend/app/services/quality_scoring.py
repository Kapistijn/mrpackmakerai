"""Explainable taxonomy-backed mod quality scoring."""
from __future__ import annotations
import math
from dataclasses import dataclass
from app.schemas.mod import ModEntry
from app.services.intent_analysis import IntentAnalysis
from app.services.intent_taxonomy import TAXONOMY_SYNONYMS,matches_category
from app.services.pack_profile import PackProfile
_CATEGORY_SYNONYMS={k.value:v for k,v in TAXONOMY_SYNONYMS.items()}
@dataclass(frozen=True)
class ModQualityScore:
    mod:ModEntry; intent_match:float; realism_score:float; popularity:float; maintenance_score:float; compatibility_score:float; performance_cost:float; dependency_quality:float; is_performance_mod:bool; reasons:tuple[str,...]
    @property
    def total(self)->float: return round(.35*self.intent_match+.20*self.realism_score+.15*self.compatibility_score+.10*self.maintenance_score+.10*self.popularity+.10*(1-self.performance_cost)+.05*self.dependency_quality,5)
def _text(mod): return ' '.join((mod.name,mod.slug,mod.summary,*mod.categories)).casefold()
def _popularity(downloads): return min(1.0,math.log10(max(downloads,1))/8.0)
def _category_match(text,intent): return .5 if not intent.categories else min(1.0,sum(matches_category(text,c) for c in intent.categories)/len(intent.categories)*2)
def score_mod_quality(mod:ModEntry,intent:IntentAnalysis,profile:PackProfile,*,minimum_downloads:int=0)->ModQualityScore:
    text=_text(mod);is_perf=any(x in text for x in ('sodium','lithium','modernfix','ferritecore','embeddium','optimization','performance','fps','memory'));heavy=any(x in text for x in ('shader','iris','oculus','volumetric','worldgen','world generation','dimension','high quality'));intent_match=_category_match(text,intent);realism=min(1.0,sum(x in text for x in ('realistic','realism','weather','season','temperature','farm','animal','physics','ambient','sound','light','survival','terrain','biome'))/4);popularity=_popularity(mod.downloads) if mod.downloads>=minimum_downloads else 0;compat=1.0 if mod.file_name and mod.download_url and (mod.hashes.sha1 or mod.hashes.sha512) else 0;maintenance=1.0 if mod.file_name and mod.download_url else .3;dependency=max(.4,1-.1*len(mod.dependencies));cost=0 if is_perf else .8 if heavy else .1
    reasons=[]
    if intent_match>=.5: reasons.append(f'matches intent ({intent.goal})')
    if is_perf: reasons.append('performance mod')
    if heavy: reasons.append('heavy visual/worldgen mod')
    return ModQualityScore(mod,intent_match,realism,popularity,maintenance,compat,cost,dependency,is_perf,tuple(reasons))
def rank_by_quality(mods,intent,profile,*,minimum_downloads=0): return sorted((score_mod_quality(m,intent,profile,minimum_downloads=minimum_downloads) for m in mods),key=lambda x:x.total,reverse=True)
def is_blocked(score,profile): return score.is_performance_mod and not profile.needs_performance_mods or score.performance_cost>=.8 and (profile.performance_floor>=.7 or not profile.allow_heavy_mods)
def select_quality(ranked,count,profile):
    selected=[];used=set();categories=set()
    for score in ranked:
        if is_blocked(score,profile): continue
        key=f'{score.mod.source}:{score.mod.id}'
        if key in used: continue
        cats={str(x).casefold() for x in score.mod.categories}
        if not selected or cats-categories: selected.append(score.mod);used.add(key);categories.update(cats)
        if len(selected)>=count:return selected
    for score in ranked:
        if is_blocked(score,profile):continue
        key=f'{score.mod.source}:{score.mod.id}'
        if key not in used:selected.append(score.mod);used.add(key)
        if len(selected)>=count:break
    return selected
