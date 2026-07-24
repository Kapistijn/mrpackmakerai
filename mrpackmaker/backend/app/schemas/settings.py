"""Public and unified settings API contracts."""
from __future__ import annotations
from pydantic import BaseModel,Field
class AISettingsPublic(BaseModel):
 provider:str;base_url:str;model:str;timeout_seconds:float;max_tokens:int;temperature:float;top_p:float=1.0;retry_attempts:int=3;context_size:int=4096;configured:bool;api_key_configured:bool=False
class VoiceSettingsPublic(BaseModel):
 whisper_url:str;tts_provider:str;tts_base_url:str;tts_model:str;tts_voice:str;tts_enabled:bool=False;tts_api_key_configured:bool=False
class MinecraftSettingsPublic(BaseModel):default_version:str;default_loader:str
class SourcesSettingsPublic(BaseModel):modrinth_enabled:bool;curseforge_enabled:bool
class SettingsOverview(BaseModel):
 ai:AISettingsPublic;voice:VoiceSettingsPublic;minecraft:MinecraftSettingsPublic;sources:SourcesSettingsPublic;mod_sources:dict[str,bool];modrinth_key_configured:bool=False;curseforge_key_configured:bool=False;modrinth_key_masked:str='not configured';curseforge_key_masked:str='not configured';admin_locked:bool=False;provider_presets:dict[str,str]=Field(default_factory=dict)
class AIModelSelection(BaseModel):model:str=''
class AISettingsUpdate(BaseModel):
 provider:str|None=None;base_url:str|None=None;model:str|None=None;timeout_seconds:float|None=Field(default=None,ge=1.0,le=300.0);max_tokens:int|None=Field(default=None,ge=128,le=32768);temperature:float|None=Field(default=None,ge=0.0,le=2.0);top_p:float|None=Field(default=None,ge=0.0,le=1.0);retry_attempts:int|None=Field(default=None,ge=1,le=5);context_size:int|None=Field(default=None,ge=512,le=131072);api_key:str|None=None
class VoiceSettingsUpdate(BaseModel):
 whisper_url:str|None=None;tts_provider:str|None=None;tts_base_url:str|None=None;tts_model:str|None=None;tts_voice:str|None=None;tts_api_key:str|None=None
class MinecraftSettingsUpdate(BaseModel):default_version:str|None=None;default_loader:str|None=None
class SourcesSettingsUpdate(BaseModel):modrinth_enabled:bool|None=None;curseforge_enabled:bool|None=None
class UnifiedSettingsUpdate(BaseModel):
 ai:AISettingsUpdate|None=None;voice:VoiceSettingsUpdate|None=None;minecraft:MinecraftSettingsUpdate|None=None;sources:SourcesSettingsUpdate|None=None;modrinth_key:str|None=None;curseforge_key:str|None=None
class TTSTestRequest(BaseModel):text:str=Field(default='MrPackMaker text to speech is working.',max_length=500)
class ApiTestResult(BaseModel):ok:bool;service:str;status_code:int|None=None;latency_ms:int|None=None;detail:str|None=None;info:dict[str,str]=Field(default_factory=dict)
class AdminSettingsUpdate(BaseModel):ai:AISettingsUpdate|None=None;modrinth_key:str|None=None;curseforge_key:str|None=None;admin_token:str|None=Field(default=None,min_length=16)
class AdminSettingsResponse(BaseModel):ai:AISettingsPublic;modrinth_key:str;curseforge_key:str;admin_token_configured:bool
