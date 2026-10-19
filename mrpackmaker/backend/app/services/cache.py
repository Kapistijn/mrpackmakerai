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
 def __init__(self,ttl:int=DEFAULT_TTL,max_entries:int=DEFAULT_MAX_ENTRIES)->None:
  if ttl < 0: raise ValueError('ttl must be non-negative')
  self._ttl=ttl;self._max_entries=max(1,max_entries);self._store:OrderedDict[str,tuple[float,T]]=OrderedDict()
 def _get_entry(self,key:str)->tuple[float,T]|None:
  entry=self._store.get(key)
  if entry is None:return None
  expires_at,value=entry
  if time.monotonic()>=expires_at:del self._store[key];return None
  self._store.move_to_end(key);return entry
 def get(self,key:str)->T|None:
  entry=self._get_entry(key)
  return None if entry is None else entry[1]
 def set(self,key:str,value:T)->None:
  now=time.monotonic()
  for old_key,(expires_at,_) in list(self._store.items()):
   if now>=expires_at:del self._store[old_key]
  self._store[key]=(now+self._ttl,value);self._store.move_to_end(key)
  while len(self._store)>self._max_entries:self._store.popitem(last=False)
 def clear(self)->None:self._store.clear()
class AsyncCoalescingCache(Generic[T]):
 """One shared result per key, safe for concurrent callers and test loops."""
 def __init__(self,ttl:int=DEFAULT_TTL,max_entries:int=DEFAULT_MAX_ENTRIES)->None:
  self._values=TTLCache[T](ttl,max_entries);self._inflight:dict[str,asyncio.Future[T]]={};self._lock:asyncio.Lock|None=None;self._loop:asyncio.AbstractEventLoop|None=None;self._generation=0
 def _ensure_loop(self)->None:
  loop=asyncio.get_running_loop()
  if self._loop is not loop:
   self._loop=loop;self._lock=asyncio.Lock();self._inflight={}
 async def get_or_fetch(self,key:str,fetch:Callable[[],Awaitable[T]])->T:
  self._ensure_loop();entry=self._values._get_entry(key)
  if entry is not None:return entry[1]
  assert self._lock is not None
  async with self._lock:
   entry=self._values._get_entry(key)
   if entry is not None:return entry[1]
   future=self._inflight.get(key)
   if future is None:
    future=asyncio.get_running_loop().create_future();future.add_done_callback(lambda done: None if done.cancelled() else done.exception())
    self._inflight[key]=future;owner=True;generation=self._generation
   else:owner=False;generation=self._generation
  if not owner:return await future
  try:
   value=await fetch()
   if generation == self._generation:self._values.set(key,value)
   async with self._lock:
    if not future.done():future.set_result(value)
    self._inflight.pop(key,None)
   return value
  except BaseException as exc:
   async with self._lock:
    if not future.done():
     if isinstance(exc, asyncio.CancelledError):future.cancel()
     else:future.set_exception(exc)
    self._inflight.pop(key,None)
   raise
 def clear(self)->None:
  self._generation += 1
  self._values.clear()
search_cache:TTLCache[Any]=TTLCache()
detail_cache:TTLCache[Any]=TTLCache()
shared_catalog_cache:AsyncCoalescingCache[Any]=AsyncCoalescingCache()
