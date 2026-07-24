"""Bounded response caches and shared async request coalescing."""
from __future__ import annotations
import asyncio
import time
from collections import OrderedDict
from typing import Any,Awaitable,Callable,Generic,TypeVar
T=TypeVar('T')
DEFAULT_TTL=300
DEFAULT_MAX_ENTRIES=512
class TTLCache(Generic[T]):
 def __init__(self,ttl:int=DEFAULT_TTL,max_entries:int=DEFAULT_MAX_ENTRIES)->None:self._ttl=ttl;self._max_entries=max(1,max_entries);self._store:OrderedDict[str,tuple[float,T]]=OrderedDict()
 def get(self,key:str)->T|None:
  entry=self._store.get(key)
  if entry is None:return None
  expires_at,value=entry
  if time.monotonic()>expires_at:del self._store[key];return None
  self._store.move_to_end(key);return value
 def set(self,key:str,value:T)->None:
  now=time.monotonic()
  for old_key,(expires_at,_) in list(self._store.items()):
   if now>expires_at:del self._store[old_key]
  self._store[key]=(now+self._ttl,value);self._store.move_to_end(key)
  while len(self._store)>self._max_entries:self._store.popitem(last=False)
 def clear(self)->None:self._store.clear()
class AsyncCoalescingCache(Generic[T]):
 """One shared result per key, including concurrent callers."""
 def __init__(self,ttl:int=DEFAULT_TTL,max_entries:int=DEFAULT_MAX_ENTRIES)->None:self._values=TTLCache[T](ttl,max_entries);self._inflight:dict[str,asyncio.Future[T]]={};self._lock=asyncio.Lock()
 async def get_or_fetch(self,key:str,fetch:Callable[[],Awaitable[T]])->T:
  cached=self._values.get(key)
  if cached is not None:return cached
  async with self._lock:
   cached=self._values.get(key)
   if cached is not None:return cached
   future=self._inflight.get(key)
   if future is None:future=asyncio.get_running_loop().create_future();self._inflight[key]=future;owner=True
   else:owner=False
  if not owner:return await future
  try:
   value=await fetch();self._values.set(key,value)
   async with self._lock:
    if not future.done():future.set_result(value)
    self._inflight.pop(key,None)
   return value
  except Exception as exc:
   async with self._lock:
    if not future.done():future.set_exception(exc)
    self._inflight.pop(key,None)
   raise
 def clear(self)->None:self._values.clear()
search_cache:TTLCache[Any]=TTLCache()
detail_cache:TTLCache[Any]=TTLCache()
shared_catalog_cache:AsyncCoalescingCache[Any]=AsyncCoalescingCache()
