from __future__ import annotations
from dataclasses import dataclass
from app.schemas.mod import ModEntry
@dataclass(frozen=True)
class ModChangePlan:
 action:str
 reason:str
 add_queries:tuple[str,...]=()
 remove_names:tuple[str,...]=()
 replace_names:tuple[str,...]=()
 requires_approval:bool=True
 def to_dict(self): return {'action':self.action,'reason':self.reason,'add_queries':list(self.add_queries),'remove_names':list(self.remove_names),'replace_names':list(self.replace_names),'requires_approval':self.requires_approval}
def plan_change(prompt:str,current:list[ModEntry])->ModChangePlan:
 text=(prompt or '').casefold(); names=tuple(m.name for m in current)
 if any(x in text for x in ('remove','verwijder')) and any(x in text for x in ('magic','magie')):
  return ModChangePlan('remove','Remove magic mods while preserving unrelated user choices',remove_names=tuple(m.name for m in current if any(x in ' '.join((m.name,m.slug,*m.categories)).casefold() for x in ('magic','spell','arcane'))))
 if any(x in text for x in ('farming','farm','landbouw')): return ModChangePlan('add','Add farming content compatible with the current pack',add_queries=('farming','agriculture','crops'))
 if any(x in text for x in ('animal','dieren','wildlife')): return ModChangePlan('add','Add realistic animal content',add_queries=('animals','wildlife','mobs'))
 if any(x in text for x in ('real life','realistic','realistischer')): return ModChangePlan('add','Increase realism without removing current choices',add_queries=('weather','seasons','temperature','farming','animals','physics'))
 return ModChangePlan('analyze','No safe deterministic change understood; ask AI for a structured proposal',add_queries=())
