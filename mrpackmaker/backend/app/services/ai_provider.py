from __future__ import annotations
import asyncio,json,logging
from dataclasses import dataclass
from typing import Any,Protocol,TypeVar
from openai import AsyncOpenAI
from pydantic import BaseModel,ValidationError
from app.config import AIConfig,config
logger=logging.getLogger(__name__);T=TypeVar('T',bound=BaseModel)
class AIProviderError(RuntimeError):pass
def _is_response_format_error(exc:Exception)->bool:
 text=str(exc).lower();return 'response_format' in text or 'response format' in text or 'json_object' in text or getattr(exc,'status_code',None)==400
def _is_retryable(exc:Exception)->bool:
 status=getattr(exc,'status_code',None);return status in {408,409,425,429,500,502,503,504} or isinstance(exc,(TimeoutError,asyncio.TimeoutError,ConnectionError))
@dataclass(frozen=True)
class ProviderConnection:provider:str;reachable:bool;active_model:str|None=None;detail:str|None=None
class AIProvider(Protocol):
 provider_id:str
 async def list_models(self)->list[str]:...
 async def connection_status(self)->ProviderConnection:...
 async def chat_json(self,system_prompt:str,user_prompt:str,schema:type[T])->T:...
 async def close(self)->None:...
class OpenAICompatibleProvider:
 def __init__(self,settings:AIConfig)->None:
  self.provider_id=settings.provider;self._settings=settings;self._client=AsyncOpenAI(api_key=settings.api_key or 'local-provider',base_url=settings.base_url,timeout=settings.timeout_seconds,max_retries=0);self._model=settings.model or None;self._supports_json_mode=True
 async def close(self)->None:await self._client.close()
 async def _with_retry(self,operation,*,label:str)->Any:
  last=None
  for attempt in range(self._settings.retry_attempts):
   try:return await operation()
   except Exception as exc:
    last=exc
    if not _is_retryable(exc) or attempt==self._settings.retry_attempts-1:raise
    delay=0.25*(2**attempt);logger.warning('%s failed for %s, retrying in %.2fs',label,self.provider_id,delay);await asyncio.sleep(delay)
  raise last or AIProviderError(f'{label} failed')
 async def list_models(self)->list[str]:
  try:models=await self._with_retry(self._client.models.list,label='model discovery')
  except Exception as exc:raise AIProviderError(f'Could not list models from {self.provider_id}: {exc}') from exc
  ids={model.id.strip() for model in (getattr(models,'data',None) or []) if getattr(model,'id',None)};return sorted(ids,key=lambda value:('instruct' not in value.lower(),value.casefold()))
 async def get_model(self)->str:
  if self._model:return self._model
  models=await self.list_models()
  if not models:raise AIProviderError(f'{self.provider_id} did not expose a loaded model')
  self._model=models[0];logger.info("Auto-selected model '%s' from %s",self._model,self.provider_id);return self._model
 async def connection_status(self)->ProviderConnection:
  try:
   models=await self.list_models();model=self._model if self._model in models else (models[0] if models else None)
   if not model:raise AIProviderError(f'{self.provider_id} did not expose a loaded model')
   self._model=model;return ProviderConnection(self.provider_id,True,model)
  except AIProviderError as exc:return ProviderConnection(self.provider_id,False,detail=str(exc))
 async def _create_completion(self,model:str,messages:list[dict[str,str]])->Any:
  kwargs={'model':model,'messages':messages,'temperature':self._settings.temperature,'top_p':self._settings.top_p,'max_tokens':self._settings.max_tokens}
  if self._supports_json_mode:kwargs['response_format']={'type':'json_object'}
  try:return await self._with_retry(lambda:self._client.chat.completions.create(**kwargs),label='chat completion')
  except Exception as exc:
   if self._supports_json_mode and _is_response_format_error(exc):
    self._supports_json_mode=False;kwargs.pop('response_format',None);return await self._with_retry(lambda:self._client.chat.completions.create(**kwargs),label='chat completion without JSON mode')
   raise
 async def chat_json(self,system_prompt:str,user_prompt:str,schema:type[T])->T:
  model=await self.get_model();messages=[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}]
  for attempt in range(2):
   try:
    response=await self._create_completion(model,messages);content=response.choices[0].message.content or '{}';return schema.model_validate(json.loads(content))
   except (json.JSONDecodeError,ValidationError) as exc:
    if attempt:raise AIProviderError(f'{self.provider_id} returned invalid {schema.__name__} JSON') from exc
    messages.append({'role':'user','content':f'Return only valid JSON matching the {schema.__name__} schema.'})
   except AIProviderError:raise
   except Exception as exc:raise AIProviderError(f'{self.provider_id} failed while generating {schema.__name__}: {exc}') from exc
  raise AssertionError('JSON retry loop should either return or raise')
def create_ai_provider(settings:AIConfig|None=None)->OpenAICompatibleProvider:return OpenAICompatibleProvider(settings or config.ai)
