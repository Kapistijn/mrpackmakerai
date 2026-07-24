"""Unified mod DTOs."""
from __future__ import annotations
from pydantic import BaseModel,Field
class ModDependency(BaseModel):
 project_id:str
 dependency_type:str='required'
 source:str|None=None
 version_range:str|None=None
 minecraft_versions:list[str]=Field(default_factory=list)
 loaders:list[str]=Field(default_factory=list)
class ModHash(BaseModel):
 sha1:str|None=None
 sha512:str|None=None
class ModEntry(BaseModel):
 id:str
 source:str
 name:str
 slug:str=''
 icon_url:str|None=None
 summary:str=''
 downloads:int=0
 categories:list[str]=Field(default_factory=list)
 loaders:list[str]=Field(default_factory=list)
 minecraft_versions:list[str]=Field(default_factory=list)
 selected_version:str|None=None
 version_id:str|None=None
 file_id:int|None=None
 file_name:str|None=None
 file_size:int|None=None
 download_url:str|None=None
 hashes:ModHash=Field(default_factory=ModHash)
 dependencies:list[ModDependency]=Field(default_factory=list)
 project_url:str=''
 install_path:str|None=None
