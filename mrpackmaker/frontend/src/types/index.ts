export enum LoaderType { FABRIC='fabric', FORGE='forge', NEOFORGE='neoforge' }
export enum ThemeType { TECHNOLOGY='technology', ADVENTURE='adventure', MAGIC='magic', EXPLORATION='exploration', SURVIVAL='survival', CUSTOM='custom' }
export enum DifficultyType { CASUAL='casual', NORMAL='normal', HARD='hard', EXPERT='expert' }
export enum PerformancePreference { BALANCED='balanced', PERFORMANCE='performance', VISUALS='visuals' }
export enum ShaderSupport { OFF='off', OPTIONAL='optional', ENABLED='enabled' }
export enum ProjectStatus { DRAFT='draft', GENERATING='generating', REVIEW='review', READY='ready', EXPORTED='exported' }
export enum ModSource { MODRINTH='modrinth', CURSEFORGE='curseforge' }
export interface ModDependency { project_id:string; dependency_type:string; source?:ModSource }
export interface ModHash { sha1?:string; sha512?:string }
export interface ModEntry { id:string; source:string; name:string; slug:string; icon_url?:string; summary:string; downloads:number; categories:string[]; loaders:string[]; dependencies:ModDependency[]; project_url:string; selected_version?:string; version_id?:string; file_id?:number; file_name?:string; file_size?:number; download_url?:string; hashes:ModHash; install_path?:string }
export interface ProjectSettings { minecraft_version:string; loader:LoaderType; loader_version?:string; name:string; description:string; theme:ThemeType; theme_custom?:string; difficulty?:DifficultyType; performance_preference?:PerformancePreference; minimum_mods?:number; maximum_mods?:number; minimum_downloads?:number; target_ram_gb?:number; target_fps?:number; shader_support?:ShaderSupport; shader_quality?:string; resourcepack_support?:boolean; required_mods?:string[]; forbidden_mods?:string[]; ai_creativity?:string; ai_strictness?:string; discovery_depth?:string; gameplay_style?:string[]; qol_level?:string; hardware_profile?:string; multiplayer_mode?:string; world_style?:string; progression?:string }
export interface Project extends ProjectSettings { id:number; generation_prompt:string; status:ProjectStatus; mods:ModEntry[]; resolved_loader_version?:string; ai_summary?:string; mrpack_path?:string; settings_locked:boolean; created_at:string; updated_at:string }
export interface ProjectListItem { id:number; name:string; minecraft_version:string; loader:LoaderType; status:ProjectStatus; created_at:string; updated_at:string }
export interface AIProgressEvent { step:number; total_steps:number; message:string; status:string; data?:any }
export enum CompatStatus { OK='OK', WARN='WARN', ERROR='ERROR' }
export interface CompatCheckItem { name:string; status:CompatStatus; message:string }
export interface CompatibilityMetrics { minecraft_version:string; loader:string; loader_version?:string; dependency_count:number; duplicate_count:number; missing_mod_count:number; missing_library_count:number; incompatible_count:number; client_only_count:number; server_only_count:number; deprecated_count:number; abandoned_count:number; outdated_count:number; security_issue_count:number; performance_score?:number; estimated_ram_mb?:number; estimated_vram_mb?:number; estimated_cpu_load_percent?:number; estimated_startup_seconds?:number; download_size_bytes:number; installed_size_bytes:number }
export interface CompatibilityReport { status:CompatStatus; mods:CompatCheckItem[]; dependencies:CompatCheckItem[]; conflicts:CompatCheckItem[]; configuration?:CompatCheckItem[]; warnings:string[]; missing_libraries:string[]; export_ready:boolean; errors:string[]; metrics?:CompatibilityMetrics }
export interface AISettingsPublic { provider:string; base_url:string; model:string; timeout_seconds:number; max_tokens:number; temperature:number; top_p:number; retry_attempts:number; context_size:number; configured:boolean; api_key_configured:boolean }
export interface VoiceSettingsPublic { whisper_url:string; tts_provider:string; tts_base_url:string; tts_model:string; tts_voice:string; tts_enabled:boolean; tts_api_key_configured:boolean }
export interface MinecraftSettingsPublic { default_version:string; default_loader:string }
export interface SourcesSettingsPublic { modrinth_enabled:boolean; curseforge_enabled:boolean }
export interface SettingsOverview { ai:AISettingsPublic; voice:VoiceSettingsPublic; minecraft:MinecraftSettingsPublic; sources:SourcesSettingsPublic; mod_sources:Record<string,boolean>; modrinth_key_configured:boolean; modrinth_key_masked:string; curseforge_key_configured:boolean; curseforge_key_masked:string; admin_locked:boolean }
export interface AISettingsUpdate { provider?:string; base_url?:string; model?:string; timeout_seconds?:number; max_tokens?:number; temperature?:number; top_p?:number; retry_attempts?:number; context_size?:number; api_key?:string }
export interface VoiceSettingsUpdate { whisper_url?:string; tts_provider?:string; tts_base_url?:string; tts_model?:string; tts_voice?:string; tts_api_key?:string }
export interface MinecraftSettingsUpdate { default_version?:string; default_loader?:string }
export interface SourcesSettingsUpdate { modrinth_enabled?:boolean; curseforge_enabled?:boolean }
export interface UnifiedSettingsUpdate { ai?:AISettingsUpdate; voice?:VoiceSettingsUpdate; minecraft?:MinecraftSettingsUpdate; sources?:SourcesSettingsUpdate; modrinth_key?:string; curseforge_key?:string }
export interface ApiTestResult { ok:boolean; service:string; status_code?:number; latency_ms?:number; detail?:string; info:Record<string,string> }
export type SecretName='modrinth'|'curseforge'|'ai'|'tts'
