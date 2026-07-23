"""Deterministic catalog scope controls for AI creativity and discovery depth."""
from __future__ import annotations
from dataclasses import dataclass
@dataclass(frozen=True)
class DiscoveryPlan:
    limit:int; offsets:tuple[int,...]; index:str; include_queries:bool
def build_discovery_plan(creativity:int|str=50,depth:str='medium')->DiscoveryPlan:
    try: creativity=max(0,min(100,int(creativity)))
    except (TypeError,ValueError): creativity=50
    level=str(depth or 'medium').casefold()
    if level in {'low','shallow'}: return DiscoveryPlan(20,(0,),'downloads',False)
    if level in {'high','deep'}: return DiscoveryPlan(100,(0,100,200,300),'relevance',True)
    return DiscoveryPlan(50 if creativity>=50 else 30,(0,50),'relevance',True)
