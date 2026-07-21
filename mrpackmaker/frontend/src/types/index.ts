export enum LoaderType {
  FABRIC = 'fabric',
  FORGE = 'forge',
  NEOFORGE = 'neoforge',
}

export enum ThemeType {
  TECHNOLOGY = 'technology',
  ADVENTURE = 'adventure',
  MAGIC = 'magic',
  EXPLORATION = 'exploration',
  SURVIVAL = 'survival',
  CUSTOM = 'custom',
}

export enum DifficultyType {
  CASUAL = 'casual',
  NORMAL = 'normal',
  HARD = 'hard',
  EXPERT = 'expert',
}

export enum PerformancePreference {
  BALANCED = 'balanced',
  PERFORMANCE = 'performance',
  VISUALS = 'visuals',
}

export enum ProjectStatus {
  DRAFT = 'draft',
  GENERATING = 'generating',
  REVIEW = 'review',
  READY = 'ready',
  EXPORTED = 'exported',
}

export enum ModSource {
  MODRINTH = 'modrinth',
  CURSEFORGE = 'curseforge',
}

export interface ModDependency {
  project_id: string;
  dependency_type: string;
  source?: ModSource;
}

export interface ModHash {
  sha1?: string;
  sha512?: string;
}

export interface ModEntry {
  id: string;
  source: string;
  name: string;
  slug: string;
  icon_url?: string;
  summary: string;
  downloads: number;
  categories: string[];
  loaders: string[];
  dependencies: ModDependency[];
  project_url: string;
  selected_version?: string;
  version_id?: string;
  file_id?: number;
  file_name?: string;
  file_size?: number;
  download_url?: string;
  hashes: ModHash;
}

export interface ProjectSettings {
  minecraft_version: string;
  loader: LoaderType;
  name: string;
  description: string;
  theme: ThemeType;
  theme_custom?: string;
  difficulty: DifficultyType;
  performance_preference: PerformancePreference;
}

export interface Project extends ProjectSettings {
  id: number;
  generation_prompt: string;
  status: ProjectStatus;
  mods: ModEntry[];
  resolved_loader_version?: string;
  ai_summary?: string;
  mrpack_path?: string;
  settings_locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProjectListItem {
  id: number;
  name: string;
  minecraft_version: string;
  loader: LoaderType;
  status: ProjectStatus;
  created_at: string;
  updated_at: string;
}

export interface AIProgressEvent {
  step: number;
  total_steps: number;
  message: string;
  status: string;
  data?: any;
}

export enum CompatStatus {
  OK = 'OK',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

export interface CompatCheckItem {
  name: string;
  status: CompatStatus;
  message: string;
}

export interface CompatibilityReport {
  status: CompatStatus;
  mods: CompatCheckItem[];
  dependencies: CompatCheckItem[];
  conflicts: CompatCheckItem[];
  warnings: string[];
  missing_libraries: string[];
  export_ready: boolean;
  errors: string[];
}

export interface AISettingsPublic {
  provider: string;
  base_url: string;
  model: string;
  timeout_seconds: number;
  max_tokens: number;
  temperature: number;
  configured: boolean;
  api_key_configured: boolean;
}

export interface VoiceSettingsPublic {
  whisper_url: string;
  tts_provider: string;
  tts_base_url: string;
  tts_model: string;
  tts_voice: string;
  tts_enabled: boolean;
  tts_api_key_configured: boolean;
}

export interface SettingsOverview {
  ai: AISettingsPublic;
  voice: VoiceSettingsPublic;
  mod_sources: Record<string, boolean>;
  modrinth_key_configured: boolean;
  curseforge_key_configured: boolean;
  modrinth_key_masked: string;
  curseforge_key_masked: string;
  admin_locked: boolean;
}

export interface AISettingsUpdate {
  provider?: string;
  base_url?: string;
  model?: string;
  timeout_seconds?: number;
  max_tokens?: number;
  temperature?: number;
  api_key?: string;
}

export interface VoiceSettingsUpdate {
  whisper_url?: string;
  tts_provider?: string;
  tts_base_url?: string;
  tts_model?: string;
  tts_voice?: string;
  tts_api_key?: string;
}

export interface UnifiedSettingsUpdate {
  ai?: AISettingsUpdate;
  voice?: VoiceSettingsUpdate;
  modrinth_key?: string;
  curseforge_key?: string;
}

export type SecretName = 'modrinth' | 'curseforge' | 'ai' | 'tts';
