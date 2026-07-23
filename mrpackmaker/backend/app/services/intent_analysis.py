"""Machine-readable intent analysis for modpack generation."""
from __future__ import annotations
import re
from dataclasses import dataclass,field
REALISM_CATEGORIES=('weather','seasons','temperature','food','farming','animals','physics','sound','lighting','survival','world_generation','immersion')
REALISM_AVOID=('magic','anime','fantasy','space','sci-fi')
THEME_CATEGORIES={'horror':('horror','atmosphere','sound','lighting','mobs','survival','world_generation','immersion'),'technology':('technology','automation','storage','energy','progression','utility'),'magic':('magic','spells','rituals','progression','adventure'),'adventure':('adventure','exploration','structures','bosses','world_generation','quests'),'exploration':('exploration','world_generation','structures','biomes','adventure'),'survival':('survival','food','farming','utility','storage','world_generation')}
_REALISM_PATTERNS=(r'real ?life',r'realistic',r'realism',r'lifelike',r'zo dicht mogelijk bij .*(?:echt|real)',r'echt(?:e)? leven',r'levensecht')
_CATEGORY_SIGNALS={'horror':('horror','scary','creepy','psychological','apocalypse','apocalyptic'),'weather':('weather','storm','rain','weer'),'seasons':('season','seizoen','seasons'),'temperature':('temperature','thirst','cold','heat','temperatuur','dorst'),'food':('food','hunger','cooking','eten','honger'),'farming':('farm','farming','agriculture','landbouw','boer'),'animals':('animal','wildlife','creature','dier'),'physics':('physics','gravity','realistic movement','natuurkunde','zwaartekracht'),'sound':('sound','audio','ambience','geluid'),'lighting':('lighting','shadow','light','verlichting'),'survival':('survival','hardcore','overleven'),'world_generation':('worldgen','world generation','terrain','biome','wereldgeneratie'),'immersion':('immers','atmosphere','immersie','sfeer'),'technology':('tech','technology','machine','automation'),'magic':('magic','spell','arcane','magie'),'adventure':('adventure','dungeon','quest','avontuur')}
@dataclass(frozen=True)
class IntentAnalysis:
    goal:str;categories:tuple[str,...]=field(default_factory=tuple);avoid:tuple[str,...]=field(default_factory=tuple);realism_focus:bool=False
    def to_dict(self):return {'goal':self.goal,'categories':list(self.categories),'avoid':list(self.avoid),'realism_focus':self.realism_focus}
def _dedupe(values):return tuple(dict.fromkeys(v for v in values if v))
def analyze_intent(prompt:str,*,theme:str|None=None,forbidden:tuple[str,...]=())->IntentAnalysis:
    text=(prompt or '').casefold();realism=any(re.search(p,text) for p in _REALISM_PATTERNS);categories=[category for category,signals in _CATEGORY_SIGNALS.items() if any(signal in text for signal in signals)];avoid=list(forbidden)
    if re.search(r'no magic|geen magie|zonder magie',text):avoid.append('magic')
    if re.search(r'no tech|geen technologie',text):avoid.append('technology')
    if realism:goal='realism survival';categories=list(REALISM_CATEGORIES)+categories;avoid=list(REALISM_AVOID)+avoid
    else:
        selected_theme=(theme or '').casefold();categories=list(THEME_CATEGORIES.get(selected_theme,()))+categories;goal=f'{selected_theme or "custom"} experience'
    avoid_set=set(avoid);return IntentAnalysis(goal=goal,categories=_dedupe(c for c in categories if c not in avoid_set),avoid=_dedupe(avoid),realism_focus=realism)
def merge_ai_intent(base:IntentAnalysis,*,goal:str|None,categories,avoid,realism_focus:bool|None)->IntentAnalysis:
    merged_categories=_dedupe([*base.categories,*(categories or [])]);merged_avoid=_dedupe([*base.avoid,*(avoid or [])]);avoid_set=set(merged_avoid);return IntentAnalysis(goal=(goal or base.goal).strip() or base.goal,categories=tuple(c for c in merged_categories if c not in avoid_set),avoid=merged_avoid,realism_focus=base.realism_focus or bool(realism_focus))
