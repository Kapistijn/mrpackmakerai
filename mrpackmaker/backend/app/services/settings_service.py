from __future__ import annotations
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from app.config import PROVIDER_PRESETS,AIConfig,MinecraftConfig,SourcesConfig,VoiceConfig,config
from app.schemas.settings import AISettingsPublic,AdminSettingsResponse,AdminSettingsUpdate,MinecraftSettingsPublic,SettingsOverview,SourcesSettingsPublic,UnifiedSettingsUpdate,VoiceSettingsPublic
from app.services.secret_store import SecretStore
from app.services.source_registry import create_default_registry
SECRET_KEYS={'modrinth':'modrinth_key','curseforge':'curseforge_key','ai':'ai_api_key','tts':'tts_api_key'}
def _mask(value:str)->str:
 if not value:return 'not configured'
 if len(value)<=4:return '*'*len(value)
 return f'{value[:2]}{"*"*max(8,len(value)-4)}{value[-2:]}'
def _public_ai()->AISettingsPublic:return AISettingsPublic(provider=config.ai.provider,base_url=config.ai.base_url,model=config.ai.model,timeout_seconds=config.ai.timeout_seconds,max_tokens=config.ai.max_tokens,temperature=config.ai.temperature,top_p=config.ai.top_p,retry_attempts=config.ai.retry_attempts,context_size=config.ai.context_size,configured=True,api_key_configured=bool(config.ai.api_key))
def _public_voice()->VoiceSettingsPublic:return VoiceSettingsPublic(whisper_url=config.voice.whisper_url,tts_provider=config.voice.tts_provider,tts_base_url=config.voice.tts_base_url,tts_model=config.voice.tts_model,tts_voice=config.voice.tts_voice,tts_enabled=config.voice.tts_enabled,tts_api_key_configured=bool(config.voice.tts_api_key))
def _public_minecraft()->MinecraftSettingsPublic:return MinecraftSettingsPublic(default_version=config.minecraft.default_version,default_loader=config.minecraft.default_loader)
def _public_sources()->SourcesSettingsPublic:return SourcesSettingsPublic(modrinth_enabled=config.sources.modrinth_enabled,curseforge_enabled=config.sources.curseforge_enabled)
class SettingsService:
 async def overview(self)->SettingsOverview:
  registry=create_default_registry()
  try:sources={source_id:registry.is_available(source_id) for source_id in registry.ids()}
  finally:await registry.close()
  return SettingsOverview(ai=_public_ai(),voice=_public_voice(),minecraft=_public_minecraft(),sources=_public_sources(),mod_sources=sources,modrinth_key_configured=bool(config.apis.modrinth_key),curseforge_key_configured=bool(config.apis.curseforge_key),modrinth_key_masked=_mask(config.apis.modrinth_key),curseforge_key_masked=_mask(config.apis.curseforge_key),admin_locked=bool(config.security.admin_token),provider_presets=dict(PROVIDER_PRESETS))
 def set_model(self,model:str)->AISettingsPublic:
  public=self._read_public_config();ai=self._ai_data(public);ai['model']=model.strip();new=AIConfig(**ai);public['ai']=new.model_dump(exclude={'api_key'});self._write_public_config(public);config.ai=new;return _public_ai()
 async def update_settings(self,update:UnifiedSettingsUpdate)->SettingsOverview:
  public=self._read_public_config();ai=self._ai_data(public);voice=self._voice_data(public);mc=dict(public.get('minecraft',{}));sources=dict(public.get('sources',{}));secret_set={};secret_clear=[]
  if update.ai is not None:
   for name in ('provider','base_url','model','timeout_seconds','max_tokens','temperature','top_p','retry_attempts','context_size'):
    value=getattr(update.ai,name)
    if value is not None:ai[name]=value
   if update.ai.api_key is not None:
    key=update.ai.api_key.strip();ai['api_key']=key
    if key:secret_set['ai_api_key']=key
    else:secret_clear.append('ai_api_key')
  if update.voice is not None:
   for name in ('whisper_url','tts_provider','tts_base_url','tts_model','tts_voice'):
    value=getattr(update.voice,name)
    if value is not None:voice[name]=value
   if update.voice.tts_api_key is not None:
    key=update.voice.tts_api_key.strip();voice['tts_api_key']=key
    if key:secret_set['tts_api_key']=key
    else:secret_clear.append('tts_api_key')
  if update.minecraft is not None:
   for name in ('default_version','default_loader'):
    value=getattr(update.minecraft,name)
    if value is not None:mc[name]=value
  if update.sources is not None:
   for name in ('modrinth_enabled','curseforge_enabled'):
    value=getattr(update.sources,name)
    if value is not None:sources[name]=value
  for field,key_name in (('modrinth_key','modrinth_key'),('curseforge_key','curseforge_key')):
   value=getattr(update,field)
   if value is not None:
    value=value.strip()
    if value:secret_set[key_name]=value
    else:secret_clear.append(key_name)
  new_ai=AIConfig(**ai);new_voice=VoiceConfig(**voice);new_mc=MinecraftConfig(**mc);new_sources=SourcesConfig(**sources)
  store=SecretStore(config.data_dir)
  if secret_set:store.update(secret_set)
  if secret_clear:store.remove(secret_clear)
  public['ai']=new_ai.model_dump(exclude={'api_key'});public['voice']=new_voice.model_dump(exclude={'tts_api_key'});public['minecraft']=new_mc.model_dump();public['sources']=new_sources.model_dump();public.setdefault('apis',{}).pop('modrinth_key',None);public.setdefault('apis',{}).pop('curseforge_key',None);self._write_public_config(public)
  config.ai=new_ai;config.voice=new_voice;config.minecraft=new_mc;config.sources=new_sources
  if 'modrinth_key' in secret_set:config.apis.modrinth_key=secret_set['modrinth_key']
  elif 'modrinth_key' in secret_clear:config.apis.modrinth_key=''
  if 'curseforge_key' in secret_set:config.apis.curseforge_key=secret_set['curseforge_key']
  elif 'curseforge_key' in secret_clear:config.apis.curseforge_key=''
  return await self.overview()
 async def delete_secret(self,name:str)->SettingsOverview:
  key=SECRET_KEYS.get(name.strip().lower())
  if not key:raise KeyError(name)
  SecretStore(config.data_dir).remove([key])
  if key=='modrinth_key':config.apis.modrinth_key=''
  elif key=='curseforge_key':config.apis.curseforge_key=''
  elif key=='ai_api_key':config.ai.api_key=''
  elif key=='tts_api_key':config.voice.tts_api_key=''
  return await self.overview()
 def admin_view(self)->AdminSettingsResponse:return AdminSettingsResponse(ai=_public_ai(),modrinth_key=_mask(config.apis.modrinth_key),curseforge_key=_mask(config.apis.curseforge_key),admin_token_configured=bool(config.security.admin_token))
 def update(self,update:AdminSettingsUpdate)->AdminSettingsResponse:
  public=self._read_public_config();ai=self._ai_data(public);secret_updates={}
  if update.ai is not None:
   for name in ('provider','base_url','model','timeout_seconds','max_tokens','temperature','top_p','retry_attempts','context_size'):
    value=getattr(update.ai,name)
    if value is not None:ai[name]=value
   if update.ai.api_key is not None:
    ai['api_key']=update.ai.api_key;secret_updates['ai_api_key']=update.ai.api_key
  if update.modrinth_key is not None:secret_updates['modrinth_key']=update.modrinth_key;config.apis.modrinth_key=update.modrinth_key
  if update.curseforge_key is not None:secret_updates['curseforge_key']=update.curseforge_key;config.apis.curseforge_key=update.curseforge_key
  if update.admin_token is not None:secret_updates['admin_token']=update.admin_token;config.security.admin_token=update.admin_token
  new_ai=AIConfig(**ai);SecretStore(config.data_dir).update(secret_updates);public['ai']=new_ai.model_dump(exclude={'api_key'});public.setdefault('apis',{}).pop('modrinth_key',None);public['apis'].pop('curseforge_key',None);public.setdefault('security',{}).pop('admin_token',None);self._write_public_config(public);config.ai=new_ai;return self.admin_view()
 @staticmethod
 def _ai_data(public:dict)->dict:
  ai=dict(public.get('ai',{}))
  if 'base_url' not in ai and 'url' in ai:ai['base_url']=ai.pop('url')
  ai['api_key']=config.ai.api_key;return ai
 @staticmethod
 def _voice_data(public:dict)->dict:
  voice=dict(public.get('voice',{}));voice['tts_api_key']=config.voice.tts_api_key;return voice
 @staticmethod
 def _read_public_config()->dict:
  path=config.repo_root/'config.json';return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
 @staticmethod
 def _write_public_config(contents:dict)->None:
  path=config.repo_root/'config.json';path.parent.mkdir(parents=True,exist_ok=True)
  with NamedTemporaryFile('w',encoding='utf-8',delete=False,dir=path.parent) as temp:json.dump(contents,temp,indent=2);temp.write('\n');tmp=Path(temp.name)
  tmp.replace(path)
settings_service=SettingsService()
