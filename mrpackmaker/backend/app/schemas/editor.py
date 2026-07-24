from __future__ import annotations
from pydantic import BaseModel,Field
class ChangePrompt(BaseModel):prompt:str=Field(min_length=1,max_length=4000)
class ApproveChange(BaseModel):request_id:int
class CrashRequest(BaseModel):text:str=Field(min_length=1,max_length=100000)
class AIChangePlan(BaseModel):
 action:str='analyze';reason:str='';summary:str='';risk:str='unknown';impact:str='';benefits:list[str]=Field(default_factory=list);drawbacks:list[str]=Field(default_factory=list);alternatives:list[str]=Field(default_factory=list);dependencies_affected:list[str]=Field(default_factory=list);performance_impact:str='unknown';compatibility_impact:str='unknown';realism_impact:str='unknown';add_queries:list[str]=Field(default_factory=list);remove_names:list[str]=Field(default_factory=list);replace_names:list[str]=Field(default_factory=list);requires_approval:bool=True
