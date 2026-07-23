from __future__ import annotations
from pydantic import BaseModel,Field
class ChangePrompt(BaseModel):prompt:str=Field(min_length=1,max_length=4000)
class ApproveChange(BaseModel):request_id:int
class CrashRequest(BaseModel):text:str=Field(min_length=1,max_length=100000)
