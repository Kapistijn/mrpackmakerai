"""Async Modrinth API client with bounded 429-aware requests."""
from __future__ import annotations
import asyncio, json, logging
from typing import Any
import httpx
from app.models.enums import LoaderType, ModSource
from app.schemas.mod import ModDependency, ModEntry, ModHash
from app.services.cache import detail_cache, search_cache
from app.services.rate_limit import modrinth_limiter
logger=logging.getLogger(__name__)
BASE_URL='https://api.modrinth.com/v2'; USER_AGENT='mrpackmaker/1.0.0 (local-app)'
_VERSION_TYPE_RANK={'release':0,'beta':1,'alpha':2}
def _invert_iso(value:str)->tuple[int,...]: return tuple(-ord(c) for c in value)
class ModrinthClient:
 source_id='modrinth'
 def __init__(self,api_key:str='')->None:
  headers={'User-Agent':USER_AGENT}
  if api_key: headers['Authorization']=api_key
  self._client=httpx.AsyncClient(base_url=BASE_URL,headers=headers,timeout=30.0);self._inflight:dict[str,Any]={}
 async def close(self)->None: await self._client.aclose()
 @property
 def available(self)->bool:return True
 async def _get(self,path:str,**kwargs:Any)->httpx.Response:return await modrinth_limiter.run(lambda:self._client.get(path,**kwargs))
 async def _coalesced(self,key:str,loader:Any)->Any:
  cached=detail_cache.get(key)
  if cached is not None:return cached
  task=self._inflight.get(key)
  if task is None: task=asyncio.create_task(loader());self._inflight[key]=task
  try:return await task
  finally:
   if self._inflight.get(key) is task:self._inflight.pop(key,None)
 async def search(self,query:str,mc_version:str,loader:LoaderType,category:str|None=None,limit:int=20,offset:int=0)->tuple[list[ModEntry],int]:
  key=f'modrinth:search:{query}:{mc_version}:{loader}:{category}:{limit}:{offset}';cached=search_cache.get(key)
  if cached is not None:return cached
  groups=[['project_type:mod'],[f'versions:{mc_version}'],[f'categories:{loader.value}']]
  if category:groups.append([f'categories:{category}'])
  try:
   r=await self._get('/search',params={'query':query,'facets':json.dumps(groups),'limit':limit,'offset':offset,'index':'relevance'});r.raise_for_status();data=r.json()
  except httpx.HTTPError as exc:
   logger.warning('Modrinth search unavailable: %s',exc);return [],0
  hits=[ModEntry(id=h.get('project_id',h.get('slug','')),source=ModSource.MODRINTH,name=h.get('title',''),slug=h.get('slug',''),icon_url=h.get('icon_url'),summary=h.get('description',''),downloads=h.get('downloads',0),categories=h.get('categories',[]),loaders=h.get('loaders',[]),project_url=f"https://modrinth.com/mod/{h.get('slug','')}") for h in data.get('hits',[])]
  result=(hits,data.get('total_hits',len(hits)));search_cache.set(key,result);return result
 async def get_project(self,project_id:str)->dict[str,Any]|None:
  key=f'modrinth:project:{project_id}'
  async def load():
   try:r=await self._get(f'/project/{project_id}');r.raise_for_status();data=r.json();detail_cache.set(key,data);return data
   except httpx.HTTPError as exc:logger.warning('Modrinth project %s unavailable after retries: %s',project_id,exc);return None
  return await self._coalesced(key,load)
 async def get_versions(self,project_id:str,mc_version:str,loader:LoaderType)->list[dict[str,Any]]:
  key=f'modrinth:versions:{project_id}:{mc_version}:{loader}'
  async def load():
   try:r=await self._get(f'/project/{project_id}/version',params={'loaders':json.dumps([loader.value]),'game_versions':json.dumps([mc_version])});r.raise_for_status();data=r.json();detail_cache.set(key,data);return data
   except httpx.HTTPError as exc:logger.warning('Modrinth versions for %s unavailable after retries: %s',project_id,exc);return []
  return await self._coalesced(key,load)
 async def get_version(self,version_id:str)->dict[str,Any]|None:
  key=f'modrinth:version:{version_id}'
  async def load():
   try:r=await self._get(f'/version/{version_id}');r.raise_for_status();data=r.json();detail_cache.set(key,data);return data
   except httpx.HTTPError as exc:logger.warning('Modrinth version unavailable: %s',exc);return None
  return await self._coalesced(key,load)
 async def get_mod_detail(self,project_id:str,mc_version:str,loader:LoaderType)->ModEntry|None:
  project=await self.get_project(project_id)
  if not project:return None
  version=self.select_best_version(await self.get_versions(project_id,mc_version,loader))
  if not version:return None
  files=version.get('files',[]);f=next((x for x in files if x.get('primary')),files[0] if files else {});hashes=f.get('hashes',{})
  deps=[ModDependency(project_id=d.get('project_id') or d.get('version_id',''),dependency_type=d.get('dependency_type','required'),source=ModSource.MODRINTH) for d in version.get('dependencies',[])]
  return ModEntry(id=project.get('id',project_id),source=ModSource.MODRINTH,name=project.get('title',''),slug=project.get('slug',''),icon_url=project.get('icon_url'),summary=project.get('description',''),downloads=project.get('downloads',0),categories=project.get('categories',[]),loaders=version.get('loaders',[]),dependencies=deps,project_url=f"https://modrinth.com/mod/{project.get('slug','')}",selected_version=version.get('version_number'),version_id=version.get('id',''),file_name=f.get('filename'),file_size=f.get('size'),download_url=f.get('url'),hashes=ModHash(sha1=hashes.get('sha1'),sha512=hashes.get('sha512')))
 @staticmethod
 def select_best_version(versions:list[dict[str,Any]])->dict[str,Any]|None:
  if not versions:return None
  return min(versions,key=lambda v:(_VERSION_TYPE_RANK.get(v.get('version_type','release'),3),_invert_iso(v.get('date_published',''))))
 async def search_loader_version(self,loader:LoaderType,mc_version:str)->str|None:
  project={'fabric':'fabric-loader','forge':'forge','neoforge':'neoforge'}.get(loader.value)
  if not project:return None
  best=self.select_best_version(await self.get_versions(project,mc_version,loader));return best.get('version_number') if best else None
